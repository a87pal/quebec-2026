#!/usr/bin/env python3
"""
Give every extras.json entry a coordinate, from OSM and Wikidata only.

Why this exists: extras.json holds the places that belong on the driving list
but are not map markers - the restaurant inside a town whose pin is the town.
Each has a Place ID, so a Google Maps link opens it exactly; none has a
coordinate, so tools/tripmap.py cannot put it in the KML, which needs a point
per placemark. This script fills that gap.

  python3 tools/extracoords.py                 look everything up, report
  python3 tools/extracoords.py --write         same, and store what passed
  python3 tools/extracoords.py --only Ashton   retry one entry
  python3 tools/extracoords.py --refresh       redo entries that already have one

Add --dest SLUG to target a specific destination.

## Why not read the coordinate off the Place ID

Every entry here already has a Google Place ID, and one Places API call would
hand back `location`. That is the obvious shortcut and it is not available:

- Maps Platform Terms 3.2.3(b) caps caching of Content at 30 consecutive days.
  extras.json is committed permanently, which is the entire point of it.
- 4.2 / 19.2 forbid using Google Maps Content with a non-Google map. These maps
  are Esri tiles.

Place IDs are the one field *exempt* from the caching cap, which is exactly why
placeid.py stores the ID and throws the location away. Coordinates come from the
same two open-licensed sources as every marker on these maps: OSM Nominatim
first, Wikidata P625 as the fallback. The lookup functions are imported from
resolve.py rather than re-written, so there is one implementation of each.

## The check, which is the point

An extra names a `near` place in places.json, and that place has a verified
coordinate. The anchor is used twice: to judge the answer, and to measure it.
Anything further from the anchor than the entry's own `max_m` - or --max-delta
where it has none - is REPORTED, NEVER APPLIED. A confidently wrong geocode is
worse than no coordinate at all: this project has had a chateau resolve to the
Dordogne and a park resolve 8 km from the sector you drive to, and both answers
looked entirely plausible on their own.

An OSM *relation* is held tighter still (--max-relation). A relation for a town
or a park is an administrative or boundary polygon whose centroid is a field
somewhere, not the door you walk through. resolve.py caps them for the same
reason. Sharpening the `query` with a street address usually turns a relation
hit into a node, which is the real fix; raising the cap for one entry with
--only is the escape hatch when the polygon genuinely is the target.

An entry that cannot be resolved keeps no coordinate and simply stays out of the
KML. That is a fine outcome. Inventing one is not: never hand-write a lat/lon
here any more than in places.json - sharpen the query and run this again.

This script never touches places.json. That is asserted before it writes, not
merely intended.
"""
import argparse, hashlib, io, json, os, sys, time

import _dest, _http
import resolve                      # for nominatim(), wikidata() and the UA
from _proj import metres


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def limit_for(src, maxd, max_relation):
    """The distance a candidate is allowed to sit from its anchor."""
    if src.startswith("osm:relation"):
        return min(maxd, max_relation)
    return maxd


def lookup(query):
    """OSM first, Wikidata second - resolve.py's own functions, its own order.

    Nominatim answers in one request. Wikidata needs a search call plus a claims
    call per candidate and throttles hard, so it is the fallback and not the
    first choice.
    """
    coord, src, label = resolve.nominatim(query)
    if not coord:
        coord, src, label = resolve.wikidata(query)
    return coord, src, label


def main():
    ap = argparse.ArgumentParser(
        description="Resolve extras.json entries to coordinates from OSM/Wikidata.")
    _dest.add_arg(ap)
    ap.add_argument("--write", action="store_true",
                    help="store coordinates that pass the distance check")
    ap.add_argument("--refresh", action="store_true",
                    help="re-resolve entries that already have a coordinate")
    ap.add_argument("--max-delta", type=float, default=5000,
                    help="metres from the anchor; further is reported, never stored. "
                         'An entry\'s own "max_m" wins where it has one.')
    ap.add_argument("--max-relation", type=float, default=2000,
                    help="metres; the tighter cap for an OSM relation, whose centroid "
                         "is a polygon's middle rather than a place")
    ap.add_argument("--only", default="", help="substring filter, for retrying one entry")
    a = ap.parse_args()
    dest = _dest.resolve(a.dest)

    ppath = os.path.join(dest.mapdir, "places.json")
    xpath = os.path.join(dest.mapdir, "extras.json")
    if not os.path.exists(ppath):
        sys.exit("no places.json - run tools/resolve.py first")
    if not os.path.exists(xpath):
        sys.exit("no extras.json for %s" % dest.slug)
    places = json.load(io.open(ppath, encoding="utf-8"))
    extras = json.load(io.open(xpath, encoding="utf-8"))

    # Nothing but resolve.py and kml.py may move a pin in places.json. Snapshot
    # the coordinates *and* the file itself, and assert on both before writing,
    # so a future edit to this file cannot quietly start doing it. (placeid.py
    # carries the same guard, for the same reason.)
    before = {k: (v.get("lat"), v.get("lon")) for k, v in places.items()}
    before_sha = sha(ppath)

    # resolve.py keeps its client in a module global, bound by _bind() to the
    # destination it is working on. Bind it here to our own cache file, so the
    # two scripts share the lookup code without sharing a cache: a query
    # sharpened for an extra should not silently answer for a marker.
    resolve.http = _http.Http(os.path.join(dest.mapdir, ".extracoords-cache.json"),
                              resolve.UA)
    today = time.strftime("%Y-%m-%d")

    found, flagged, missed, skipped = [], [], [], 0
    for name in sorted(extras):
        e = extras[name]
        if a.only and a.only.lower() not in name.lower():
            continue
        if e.get("lat") is not None and e.get("lon") is not None and not a.refresh:
            skipped += 1
            continue
        anchor = places.get(e.get("near") or "")
        if not anchor or anchor.get("lat") is None or anchor.get("lon") is None:
            missed.append((name, '"near" does not name a place with a coordinate'))
            continue
        here = (anchor["lat"], anchor["lon"])
        maxd = float(e.get("max_m") or a.max_delta)
        query = e.get("query") or name
        try:
            coord, src, label = lookup(query)
        except Exception as exc:
            print("  ! %-30s lookup failed: %s" % (name[:30], exc))
            continue
        if not coord:
            missed.append((name, 'no OSM or Wikidata result for "%s"' % query))
            continue
        d = metres(here, coord)
        lim = limit_for(src, maxd, a.max_relation)
        row = (name, d, coord, src, label, lim, e.get("place_delta_m"))
        if d <= lim:
            found.append(row)
            if a.write:
                e["lat"], e["lon"] = round(coord[0], 5), round(coord[1], 5)
                e["source"], e["verified"] = src, today
        else:
            flagged.append(row)

    def show(rows):
        for name, d, coord, src, label, lim, gdelta in sorted(rows, key=lambda r: -r[1]):
            mark = ""
            if src.startswith("osm:relation"):
                mark += "  [relation: %dm limit]" % lim
            # place_delta_m is what placeid.py measured from the same anchor to
            # Google's answer. It is a scalar already committed here, not a
            # coordinate and nothing that reaches a map - but a wild disagreement
            # between the two distances is a cheap hint that one of them found a
            # different place. Advisory only; it gates nothing.
            if gdelta is not None and abs(d - gdelta) > max(500, 0.5 * gdelta):
                mark += "  [google measured %dm]" % gdelta
            print("  %6.0f m  %-30s %-20s %-32s%s"
                  % (d, name[:30], src[:20], label[:32], mark))

    print("\n--- within limit (safe to accept) ---")
    show(found)
    if flagged:
        print("\n--- over limit: REVIEW BY HAND, not stored ---")
        show(flagged)
        for name, d, coord, src, label, lim, gdelta in sorted(flagged, key=lambda r: -r[1]):
            anchor = places[extras[name]["near"]]
            print("     %-28s anchor %.5f,%.5f  source says %.5f,%.5f"
                  % (name[:28], anchor["lat"], anchor["lon"], coord[0], coord[1]))
        print("  A coordinate this far from its anchor is the wrong place. Sharpen")
        print('  "query" in extras.json - a street and a town usually fix it - and')
        print("  retry with --only. Leaving it unresolved is the right answer if it")
        print("  cannot be made to land; it just stays out of the KML.")
    if missed:
        print("\n--- no usable result ---")
        for name, why in missed:
            print("  %-30s %s" % (name[:30], why))
    if skipped:
        print("\n%d entr(ies) already had a coordinate (--refresh to redo them)" % skipped)

    # Two entries on one coordinate means one of them probably lost - the same
    # failure placeid.py catches with duplicate Place IDs, where "Main Deli"
    # resolved to Schwartz's and looked entirely plausible at 444 m.
    seen = {}
    for k, v in extras.items():
        if v.get("lat") is not None:
            seen.setdefault((round(v["lat"], 4), round(v["lon"], 4)), []).append(k)
    for name, d, coord, src, label, lim, gdelta in found:
        key = (round(coord[0], 4), round(coord[1], 4))
        seen.setdefault(key, [])
        if name not in seen[key]:
            seen[key].append(name)
    clash = {c: names for c, names in seen.items() if len(names) > 1}
    if clash:
        print("\n--- SAME coordinate on more than one entry (within ~10 m) ---")
        for c, names in sorted(clash.items(), key=lambda kv: -len(kv[1])):
            print("  %.4f,%.4f  %s" % (c[0], c[1], " | ".join(sorted(names))))
        print("  Deliberate where two entries share a building. Otherwise one of")
        print("  them is wrong: sharpen its query and retry with --only.")

    resolve.http.save()
    print("\n%d resolved, %d flagged, %d unresolved; %d of %d entries now have a "
          "coordinate" % (len(found), len(flagged), len(missed),
                          sum(1 for v in extras.values() if v.get("lat") is not None),
                          len(extras)))

    if not a.write:
        print("\n(dry run - pass --write to store the accepted coordinates)")
        return

    after = {k: (v.get("lat"), v.get("lon")) for k, v in places.items()}
    if after != before or sha(ppath) != before_sha:
        sys.exit("error: places.json changed under this script, which must never "
                 "happen. Nothing written.")
    json.dump(extras, io.open(xpath, "w", encoding="utf-8"),
              indent=1, ensure_ascii=False, sort_keys=True)
    print("wrote %d coordinate(s) -> %s" % (len(found), xpath))


if __name__ == "__main__":
    main()
