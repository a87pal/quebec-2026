#!/usr/bin/env python3
"""
Resolve every map marker's coordinates against an authoritative source.

Why this exists: the first version of these maps had coordinates typed from
memory. Three markers were 300-420 m out, which is invisible on the z8 route
map and glaring at z13-15. Nothing in the Esri basemap can be queried -- the
tiles are raster JPEGs and the place names on them are painted pixels -- so the
coordinates have to come from somewhere else. They come from here.

  python3 tools/resolve.py --seed     build places.json from markers.py
  python3 tools/resolve.py            look everything up, report drift
  python3 tools/resolve.py --write    same, and accept moves under --max-accept

Add --dest SLUG to target a specific destination.

Sources, in order: OSM Nominatim, then Wikidata (P625). Both keyless and free.
Nominatim goes first because it answers in one request; Wikidata needs a search
call plus a claims call per candidate, and throttles hard enough that 55 places
can take half an hour.

Anything that moves further than --max-accept is REPORTED, never auto-applied:
a bad search hit is worse than a coordinate that is 200 m off.

This is the automated first pass. tools/kml.py is the human one: it exports
places.json to KML for review on Google's basemap and merges the corrections
back. A pin you dragged there outranks anything this script found.
"""
import argparse, io, json, os, re, sys, time, urllib.parse

import _dest, _http
from _proj import metres

UA = "travel-guide-toolchain/1.0 (personal itinerary; contact via github.com/a87pal)"

# Set by main() once --dest is resolved.
PLACES = MARKERS = None
http = None


def _bind(dest):
    """Point the module at one destination's map data."""
    global PLACES, MARKERS, http
    PLACES = os.path.join(dest.mapdir, "places.json")
    MARKERS = os.path.join(dest.mapdir, "markers.py")
    http = _http.Http(os.path.join(dest.mapdir, ".resolve-cache.json"), UA)


def get(url):
    return http.get_json(url)


# --------------------------------------------------------------- sources
def wikidata(query):
    u = ("https://www.wikidata.org/w/api.php?action=wbsearchentities&format=json"
         "&language=en&limit=5&search=" + urllib.parse.quote(query))
    for hit in get(u).get("search", []):
        c = get("https://www.wikidata.org/w/api.php?action=wbgetclaims&format=json"
                "&property=P625&entity=" + hit["id"])
        for cl in c.get("claims", {}).get("P625", []):
            v = cl.get("mainsnak", {}).get("datavalue", {}).get("value")
            if v:
                return (v["latitude"], v["longitude"]), "wikidata:" + hit["id"], hit.get("label", "")
    return None, None, None


def nominatim(query):
    u = ("https://nominatim.openstreetmap.org/search?format=json&limit=1&q="
         + urllib.parse.quote(query))
    r = get(u)
    if r:
        return ((float(r[0]["lat"]), float(r[0]["lon"])),
                "osm:%s/%s" % (r[0].get("osm_type", "?"), r[0].get("osm_id", "?")),
                r[0].get("display_name", "")[:60])
    return None, None, None


# --------------------------------------------------------------- seeding
MARKER = re.compile(r'\bmarker\(P,\s*(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)\s*,\s*"([^"]+)"')
# Map names may contain hyphens - maps.py has always accepted [a-z0-9_-]+ for a
# tile directory. This used to be \w+, which matches neither "home-nh" nor any
# part of it, so `region` silently kept the previous map's value and every
# marker on a hyphenated map was seeded with the wrong context string. Silent is
# the problem: the queries looked fine and pointed at the wrong province.
REGION = re.compile(r"\bmk\('([\w-]+)'\)")

def seed(dest):
    """Pull the current marker coordinates out of markers.py as a starting point."""
    src = io.open(MARKERS, encoding="utf-8").read()
    # which map each marker belongs to, so we can add regional context to queries
    region, out = None, {}
    ctx = {k: v.get("context", "") for k, v in dest.load("maps.json").items()}
    for line in src.split("\n"):
        m = REGION.search(line)
        if m:
            region = m.group(1)
        for lat, lon, name in MARKER.findall(line):
            key = name.strip()
            if key in out:
                continue
            out[key] = {"lat": float(lat), "lon": float(lon), "region": region,
                        "query": (key + " " + ctx.get(region, "")).strip(),
                        "source": "typed-by-hand", "verified": None}
    existing = json.load(io.open(PLACES)) if os.path.exists(PLACES) else {}
    resolved = queries = 0
    for k, v in existing.items():
        if k not in out:
            continue
        if v.get("source", "").startswith(("wikidata:", "osm:", "manual:", "gmaps:")):
            out[k] = v                                  # resolved: keep the whole entry
            resolved += 1
        elif v.get("query"):
            # Unresolved, but the query may have been sharpened by hand - and an
            # unresolved place is precisely one whose auto-generated query failed.
            # Regenerating it here would throw away the fix the README asks for.
            out[k]["query"] = v["query"]
            queries += 1
    json.dump(out, io.open(PLACES, "w"), indent=1, ensure_ascii=False, sort_keys=True)
    print("seeded %d places -> %s" % (len(out), PLACES))
    print("  kept %d resolved entries, %d hand-written queries, %d new"
          % (resolved, queries, len(out) - resolved - queries))


# --------------------------------------------------------------- resolving
def resolve(write, max_accept, only):
    places = json.load(io.open(PLACES))
    today = time.strftime("%Y-%m-%d")
    moved, flagged, missed = [], [], []
    for name in sorted(places):
        p = places[name]
        if only and only not in name:
            continue
        # Both are deliberate human overrides: "manual:" was reasoned about and
        # written down, "gmaps:" was dragged into place on Google's basemap.
        # A geocoder hit does not get to overrule either.
        if p.get("source", "").startswith(("manual:", "gmaps:")):
            continue
        q = p.get("query") or name
        try:
            # Nominatim first: one request per place. Wikidata needs a search
            # call plus a claims call per candidate (up to 6 requests), and it
            # throttles hard enough that 55 places can take half an hour.
            coord, src, label = nominatim(q)
            if not coord:
                coord, src, label = wikidata(q)
        except Exception as e:
            print("  ! %-30s lookup failed: %s" % (name[:30], e)); continue
        if not coord:
            missed.append(name); continue
        d = metres((p["lat"], p["lon"]), coord)
        row = (name, d, coord, src, label)
        # An OSM *relation* for a town or a park is an administrative polygon;
        # its centroid is a field somewhere, not the village square or the
        # trailhead you drive to. Only trust those when they barely move.
        limit = max_accept if not src.startswith("osm:relation") else min(max_accept, 250)
        if d <= limit:
            moved.append(row)
            if write:
                p["lat"], p["lon"] = round(coord[0], 5), round(coord[1], 5)
                p["source"], p["verified"], p["matched"] = src, today, label
        else:
            flagged.append(row)

    print("\n--- within %d m (safe to accept) ---" % max_accept)
    for n, d, c, s, l in sorted(moved, key=lambda r: -r[1]):
        print("  %6.0f m  %-30s %-22s %s" % (d, n[:30], s, l[:40]))
    print("\n--- over %d m: REVIEW BY HAND, not applied ---" % max_accept)
    for n, d, c, s, l in sorted(flagged, key=lambda r: -r[1]):
        print("  %6.0f m  %-30s %-22s %s" % (d, n[:30], s, l[:40]))
        print("            stored %.5f,%.5f  source says %.5f,%.5f"
              % (places[n]["lat"], places[n]["lon"], c[0], c[1]))
    if missed:
        print("\n--- no coordinate found (stays as typed) ---")
        for n in missed:
            print("  %s" % n)
    http.save()
    if write:
        json.dump(places, io.open(PLACES, "w"), indent=1, ensure_ascii=False, sort_keys=True)
        print("\nwrote %d accepted coordinates to places.json" % len(moved))
    else:
        print("\n(dry run — pass --write to apply the accepted ones)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Resolve marker coordinates from Wikidata/OSM.")
    _dest.add_arg(ap)
    ap.add_argument("--seed", action="store_true", help="rebuild places.json from markers.py")
    ap.add_argument("--write", action="store_true", help="apply coordinates under --max-accept")
    ap.add_argument("--max-accept", type=float, default=2000,
                    help="metres; further than this is flagged, never auto-applied")
    ap.add_argument("--only", default="", help="substring filter, for retrying one place")
    a = ap.parse_args()
    dest = _dest.resolve(a.dest)
    _bind(dest)
    if a.seed:
        seed(dest)
    else:
        if not os.path.exists(PLACES):
            sys.exit("no places.json — run with --seed first")
        resolve(a.write, a.max_accept, a.only)
