#!/usr/bin/env python3
"""
Resolve every place to a Google Place ID, so a link can name it exactly.

Why this exists: you navigate from a *saved list* in Google Maps, and building
one is manual - there is no API for saved lists and no import path. The tedious
half is not the tapping, it is confirming that the thing Google found is the
thing you meant. That is the same failure this toolchain already knows well:
the geocoder put Chateau Frontenac in the Dordogne and Hautes-Gorges 8 km from
the sector you drive to, and both answers looked confident.

A Place ID removes the judgement. Google Maps URLs take `query_place_id`, which
resolves to one exact Place rather than a search, so the link lands on the right
place with nothing to eyeball:

    https://www.google.com/maps/search/?api=1&query=<lat>,<lon>&query_place_id=<ID>

The documented api=1 Search action accepts only `query` and `query_place_id` -
there is no location-bias, viewport or centre parameter - so a Place ID is the
only supported way to make such a link unambiguous.

  python3 tools/placeid.py                  look everything up, report deltas
  python3 tools/placeid.py --write          same, and store the accepted IDs
  python3 tools/placeid.py --only Cannon    retry one place

Add --dest SLUG to target a specific destination.

Why storing these is allowed, when Google route geometry is not: Place IDs are
*explicitly exempt* from the caching restriction in Maps Platform Terms section
3.2.3(b) - they may be stored indefinitely, and refreshed at no charge. That is
the whole reason this fits a repo whose entire premise is committing its inputs
so CI never re-fetches. tools/routes.py explains why Directions data gets no
such licence.

So this script deliberately stores as little as it can: the ID, the date, and
the distance it measured. Google's displayName and location are printed for
review and then discarded, because those *are* Content under the 30-day rule.
Nothing Google-derived is ever drawn on the Esri basemap, which keeps clear of
the non-Google-map clause that rules out Directions here.

Anything further than --max-delta from the verified coordinate is REPORTED,
never stored, and an administrative result - a town rather than a place inside
it - is held to the much tighter --max-admin. This script never touches lat/lon;
that is asserted before it writes, not merely intended.

> Editing FIELDS does not invalidate the cache. `_http.py` keys on the URL and
> the request body, and the field mask is a *header*, so a cached response comes
> back in the old shape and the new field is silently absent. Delete
> maps/.placeid-cache.json after changing it.

Needs a key for the Places API (New). Free: the tier this uses allows thousands
of calls a month and one destination needs well under a hundred. Looked for in
three places, first hit wins: --key, then $GOOGLE_MAPS_API_KEY, then the macOS
keychain under that same service name. The keychain is the one worth using -
it keeps the key out of your shell history and out of this repo, which is
published to GitHub Pages:

    security add-generic-password -U -a "$USER" -s GOOGLE_MAPS_API_KEY -w

Enable "Places API (New)" on the Cloud project the key belongs to. CI never
needs a key, because places.json is committed.

Usage:  python3 tools/placeid.py [--dest SLUG] [--write] [--only SUBSTR]
"""
import argparse, io, json, os, sys, time

import _dest, _http
from _proj import metres
from routes import keychain          # same hardened, silent-on-failure lookup

UA = "travel-guide-toolchain/1.0 (personal itinerary; contact via github.com/a87pal)"

ENDPOINT = "https://places.googleapis.com/v1/places:searchText"
KEY_NAME = "GOOGLE_MAPS_API_KEY"

# Ask for the least that still allows a sanity check. `location` is what lets us
# measure the disagreement, `displayName` is what makes the report readable, and
# `types` is what distinguishes a town from a place inside it. None is stored -
# see the module docstring.
FIELDS = "places.id,places.displayName,places.location,places.types"

# A town's Place ID resolves to its administrative centre, which is a road
# junction somewhere near the middle - not the wharf, the dining street or the
# rental you actually drive to. These maps deliberately pin the site rather than
# the town (see the "town centres replaced by the sites we drive to" pass), so a
# locality hit 900 m away is the wrong answer even though 900 m looks tolerable.
# resolve.py caps OSM *relations* at 250 m for exactly this reason.
ADMIN = {'locality', 'sublocality', 'neighborhood', 'political', 'postal_code',
         'country', 'administrative_area_level_1', 'administrative_area_level_2',
         'administrative_area_level_3', 'administrative_area_level_4'}
# ...unless it is also a real establishment, which is a named thing at a point.
NOT_ADMIN = {'establishment', 'point_of_interest', 'premise', 'street_address'}


def is_admin(types):
    t = set(types or ())
    return bool(t & ADMIN) and not (t & NOT_ADMIN)


# Some pins *are* the town: a route-overview label, a border crossing, a place
# you pass through. Setting "place_scope": "town" on the entry says the locality
# centroid is the intended target. It is set by hand, never inferred - the whole
# point of the admin cap is that a script cannot tell "the town" from "a place in
# the town", and only a person knows which was meant.
#
# Such an entry gets --max-town rather than --max-delta, because the pin is
# deliberately a site inside the town and the centroid is legitimately kilometres
# away. The check is not abandoned, only scaled: it still catches the failure
# that matters, which is a same-named town in the wrong region entirely.


def api_key(explicit):
    """Resolve the key. Returns (key, where_it_came_from)."""
    if explicit:
        return explicit, '--key'
    if os.environ.get(KEY_NAME):
        return os.environ[KEY_NAME], '$' + KEY_NAME
    got = keychain(KEY_NAME)
    if got:
        return got, 'macOS keychain (%s)' % KEY_NAME
    return None, None


KEY_HELP = ("error: this needs a Google Maps API key with the Places API (New)\n"
            "enabled. Create one at https://console.cloud.google.com/ , then store\n"
            "it in the macOS keychain, which keeps it out of your shell history and\n"
            "out of this repo:\n\n"
            "  security add-generic-password -U -a \"$USER\" -s %s -w\n\n"
            "(-w with no value prompts for it, hidden, and confirms it twice.)\n"
            "Or set $%s for one command, or pass --key." % (KEY_NAME, KEY_NAME))


def search(http, key, query, lat, lon, radius):
    """Text Search biased to where we already know the place is.

    Returns a list of (place_id, name, (lat, lon)) in Google's ranking order.
    The bias is what stops "Notre-Dame" resolving to Paris; the caller still
    checks the distance, because a bias is a preference and not a fence.
    """
    body = {
        "textQuery": query,
        "pageSize": 5,
        "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lon},
                                    "radius": float(radius)}},
    }
    r = http.post_json(ENDPOINT, body,
                       {"X-Goog-Api-Key": key, "X-Goog-FieldMask": FIELDS})
    out = []
    for p in r.get("places", []):
        loc = p.get("location") or {}
        if "latitude" not in loc or "longitude" not in loc:
            continue
        out.append((p.get("id"), (p.get("displayName") or {}).get("text", ""),
                    (loc["latitude"], loc["longitude"]), p.get("types") or []))
    return out


def limit_for(types, max_delta, max_admin, max_town, scope):
    if scope == 'town':
        return max_town
    return min(max_delta, max_admin) if is_admin(types) else max_delta


def pick(cands, here, max_delta, max_admin=250, max_town=6000, scope=None):
    """Choose a candidate. Returns (index, id, name, distance, limit) or None.

    Google's top hit first: it is ranked on more than proximity and is usually
    right. Only when that one is implausibly far do we look down the list, and
    the caller prints the rank when it is not 1 so a human sees that it happened.

    Each candidate is judged against its own limit, because a town gets a much
    tighter one than a named establishment.
    """
    scored = [(i, pid, name, metres(here, loc),
               limit_for(types, max_delta, max_admin, max_town, scope))
              for i, (pid, name, loc, types) in enumerate(cands)]
    if not scored:
        return None
    for row in scored:
        if row[3] <= row[4]:
            return row
    return scored[0]                  # too far: returned so it can be reported


def main():
    ap = argparse.ArgumentParser(description="Resolve places to Google Place IDs.")
    _dest.add_arg(ap)
    ap.add_argument("--write", action="store_true", help="store IDs within --max-delta")
    ap.add_argument("--refresh", action="store_true",
                    help="re-resolve places that already have an ID (Google suggests "
                         "refreshing IDs over 12 months old; delete the cache file to "
                         "force a real refetch)")
    ap.add_argument("--max-delta", type=float, default=1000,
                    help="metres; further than this is reported, never stored")
    ap.add_argument("--max-admin", type=float, default=250,
                    help="metres; the tighter cap for a town or other administrative "
                         "result, whose coordinate is a centroid rather than a place")
    ap.add_argument("--max-town", type=float, default=6000,
                    help="metres; the looser cap for an entry marked "
                         '"place_scope": "town", where the centroid is what is wanted')
    ap.add_argument("--max-extra", type=float, default=5000,
                    help="metres; allowance for an extras.json entry, which is measured "
                         "against a town anchor rather than against itself")
    ap.add_argument("--radius", type=float, default=800,
                    help="metres; location-bias radius around the verified coordinate")
    ap.add_argument("--only", default="", help="substring filter, for retrying one place")
    ap.add_argument("--key", default="", help="API key (prefer the keychain)")
    a = ap.parse_args()
    dest = _dest.resolve(a.dest)

    key, where = api_key(a.key)
    if not key:
        sys.exit(KEY_HELP)
    print("key from %s" % where)      # never the key itself

    path = os.path.join(dest.mapdir, "places.json")
    if not os.path.exists(path):
        sys.exit("no places.json - run tools/resolve.py first")
    places = json.load(io.open(path, encoding="utf-8"))
    http = _http.Http(os.path.join(dest.mapdir, ".placeid-cache.json"), UA)
    today = time.strftime("%Y-%m-%d")

    # The hard rule is that nothing but resolve.py and kml.py may move a pin.
    # Snapshot the coordinates and assert on them before writing, so a future
    # edit to this file cannot quietly start doing it.
    before = {k: (v.get("lat"), v.get("lon")) for k, v in places.items()}

    # extras.json holds places that belong on the driving list but are not map
    # markers - the attraction inside a town whose pin is the town. They have no
    # coordinate of their own, so each names a `near` place to bias the search
    # and to measure against.
    extras = dest.load('extras.json', default={})

    work = []
    for name in sorted(places):
        p = places[name]
        if p.get("lat") is None or p.get("lon") is None:
            work.append((name, None, None, p, a.max_delta,
                         "no coordinate to bias the search with"))
            continue
        work.append((name, p.get("query") or name, (p["lat"], p["lon"]), p, a.max_delta, None))
    for name in sorted(extras):
        e = extras[name]
        anchor = places.get(e.get("near") or "")
        # An extra is measured against its anchor, which is somewhere in the same
        # town rather than the place itself, so it gets a much wider allowance -
        # per-entry "max_m" where a place sits further out still. The check is
        # not decorative even at this width: it is what catches a same-named
        # restaurant in another city, which is the failure that actually happens.
        maxd = float(e.get("max_m") or a.max_extra)
        if not anchor or anchor.get("lat") is None:
            work.append((name, None, None, e, maxd,
                         'extras: "near" does not name a place with a coordinate'))
            continue
        work.append((name, e.get("query") or name, (anchor["lat"], anchor["lon"]), e, maxd, None))

    found, flagged, missed, skipped = [], [], [], 0
    for name, query, here, p, maxd, problem in work:
        if a.only and a.only.lower() not in name.lower():
            continue
        if p.get("place_id") and not a.refresh:
            skipped += 1
            continue
        if problem:
            missed.append((name, problem))
            continue
        try:
            cands = search(http, key, query, here[0], here[1],
                           max(a.radius, min(maxd, 5000)))
        except Exception as e:
            print("  ! %-30s lookup failed: %s" % (name[:30], e))
            continue
        got = pick(cands, here, maxd, a.max_admin, a.max_town, p.get('place_scope'))
        if not got:
            missed.append((name, 'no result for "%s"' % query))
            continue
        rank, pid, gname, d, lim = got
        row = (name, d, pid, gname, rank, lim)
        if d <= lim:
            found.append(row)
            if a.write:
                p["place_id"] = pid
                p["place_verified"] = today
                p["place_delta_m"] = round(d)
        else:
            flagged.append(row)

    def show(rows):
        for n, d, pid, gname, rank, lim in sorted(rows, key=lambda r: -r[1]):
            mark = "" if rank == 0 else "  [hit #%d]" % (rank + 1)
            if lim < a.max_delta:
                mark += "  [town: %dm limit]" % lim
            elif lim > a.max_delta:
                mark += "  [%dm limit]" % lim
            print("  %6.0f m  %-30s %-28s %s%s"
                  % (d, n[:30], pid[:28], gname[:34], mark))

    print("\n--- within limit (safe to accept) ---")
    show(found)
    if flagged:
        print("\n--- over limit: REVIEW BY HAND, not stored ---")
        show(flagged)
        print("  A Place ID this far from a verified pin is the wrong place, or the")
        print("  pin is wrong. Sharpen \"query\" in places.json and retry with --only.")
        print("  \"[town]\" means Google returned the locality, not the site you pinned;")
        print("  those keep the coordinate link, which still opens the right spot.")
    if missed:
        print("\n--- no usable result ---")
        for n, why in missed:
            print("  %-30s %s" % (n[:30], why))
    if skipped:
        print("\n%d place(s) already had an ID (--refresh to redo them)" % skipped)

    # Two entries on one Place ID means one of them lost. "Main Deli" resolved to
    # Schwartz's - the right answer for a *different* row - and a distance check
    # cannot see that, because the wrong place was 444 m away and entirely
    # plausible. Only the collision gives it away.
    seen = {}
    for src in (places, extras):
        for k, v in src.items():
            if v.get("place_id"):
                seen.setdefault(v["place_id"], []).append(k)
    # Include what this run *would* store, so a dry run reports the collision
    # rather than only revealing it after --write.
    for n, d_, pid, gname, rank, lim in found:
        seen.setdefault(pid, [])
        if n not in seen[pid]:
            seen[pid].append(n)
    clash = {pid: names for pid, names in seen.items() if len(names) > 1}
    if clash:
        print("\n--- SAME Place ID on more than one entry ---")
        for pid, names in sorted(clash.items(), key=lambda kv: -len(kv[1])):
            print("  %-28s %s" % (pid[:28], ' | '.join(sorted(names))))
        print("  Deliberate for an alias (a base that doubles as its town's pin).")
        print("  Otherwise one of them is wrong: sharpen its query and retry with --only.")

    http.save()

    if not a.write:
        print("\n(dry run - pass --write to store the accepted IDs)")
        return

    after = {k: (v.get("lat"), v.get("lon")) for k, v in places.items()}
    if after != before:
        sys.exit("error: this script moved a coordinate, which it must never do. "
                 "Nothing written.")
    # Count per file. `found` spans both, so reporting its length against
    # places.json overstates what actually landed there.
    json.dump(places, io.open(path, "w", encoding="utf-8"),
              indent=1, ensure_ascii=False, sort_keys=True)
    n_places = sum(1 for n, *_ in found if n in places)
    print("\nstored %d Place ID(s) -> %s" % (n_places, path))
    if extras:
        xpath = os.path.join(dest.mapdir, "extras.json")
        json.dump(extras, io.open(xpath, "w", encoding="utf-8"),
                  indent=1, ensure_ascii=False, sort_keys=True)
        print("  stored %d, %d with an ID -> %s"
              % (len(found) - n_places,
                 sum(1 for v in extras.values() if v.get("place_id")), xpath))


if __name__ == "__main__":
    main()
