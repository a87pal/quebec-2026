#!/usr/bin/env python3
"""Round-trip places.json through Google My Maps so a human can verify every pin.

resolve.py is the automated pass: it asks Nominatim and Wikidata and accepts
anything that has not moved far. It is good, and it is not enough. It put
Chateau Frontenac in the Dordogne and Hautes-Gorges 8 km from the sector you
actually drive to, because a geocoder cannot tell you that the coordinate it
found is not the place you meant. tools/README.md is blunt about what caught
every real error we have had: looking at the map.

This makes looking cheap.

  python3 tools/kml.py --export           write maps/places.kml
  ... import that into a Google My Maps layer, drag anything wrong, export KML
  python3 tools/kml.py --import FILE      report what moved
  python3 tools/kml.py --import FILE --write     apply it

Pins are coloured by confidence on export, so the review targets the entries
that need it rather than all of them: red for typed-by-hand, amber for manual
overrides, green for a resolved geocoder hit.

A pin that comes back from this round trip outranks anything resolve.py finds
later - both --seed and the resolver skip "gmaps:" sources. The prior source is
kept in "was", so a manual override's reasoning is never destroyed.

Add --dest SLUG to target a specific destination.
"""
import argparse, io, json, os, sys, time, xml.etree.ElementTree as ET, zipfile

import _dest
from _proj import metres

# KML colours are aabbggrr - alpha, then BLUE, GREEN, RED. Writing them as
# familiar rrggbb yields confidently wrong colours, which is the same class of
# trap as Esri's /tile/{z}/{y}/{x} axis order.
STYLES = [
    ('unverified', 'ff3643f0', 'red',  'typed by hand - not verified anywhere'),
    ('manual',     'ff20a5ff', 'ylw',  'deliberate override - read the reason before moving it'),
    ('resolved',   'ff4caf67', 'grn',  'geocoder hit, not yet eyeballed'),
    ('confirmed',  'ff8f6b3b', 'blu',  'already confirmed on Google basemap'),
]
ICON = 'http://maps.google.com/mapfiles/kml/paddle/%s-blank.png'

# A drag this small is a mis-click, not a correction.
DRAG_M = 10.0


def confidence(src):
    if src.startswith('gmaps:'):
        return 'confirmed'
    if src.startswith('manual:'):
        return 'manual'
    if src.startswith(('osm:', 'wikidata:')):
        return 'resolved'
    return 'unverified'


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;'))


# --------------------------------------------------------------------- export
def export(dest, path):
    places = dest.load('places.json')
    cfg = dest.load('maps.json')
    routes = dest.load('routes.json', default={})
    title = dest.meta().get('title', dest.slug)

    o = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
         '<name>%s - pin review</name>' % esc(title),
         '<description>Drag any pin that is in the wrong place, then export KML '
         'and run: python3 tools/kml.py --import FILE --write</description>']
    for sid, colour, icon, _ in STYLES:
        o.append('<Style id="%s"><IconStyle><color>%s</color><scale>1.1</scale>'
                 '<Icon><href>%s</href></Icon></IconStyle>'
                 '<LabelStyle><color>%s</color></LabelStyle></Style>'
                 % (sid, colour, ICON % icon, colour))

    # Region order follows maps.json so the layers arrive in the guide's order.
    order = list(cfg.keys())
    regions = sorted({p.get('region') or '_' for p in places.values()},
                     key=lambda r: (order.index(r) if r in order else 99, r))

    counts = {}
    for region in regions:
        rows = sorted((k, v) for k, v in places.items() if (v.get('region') or '_') == region)
        if not rows:
            continue
        o.append('<Folder><name>%s</name>' % esc(region))
        for key, p in rows:
            c = confidence(p.get('source', ''))
            counts[c] = counts.get(c, 0) + 1
            desc = ['<b>%s</b>' % esc(dict((s[0], s[3]) for s in STYLES)[c]),
                    'query: %s' % esc(p.get('query', '')),
                    'source: %s' % esc(p.get('source', '')),
                    'verified: %s' % esc(p.get('verified') or 'never')]
            if p.get('was'):
                desc.append('was: %s' % esc(p['was']))
            if p.get('matched'):
                desc.append('matched: %s' % esc(p['matched']))
            o.append('<Placemark><name>%s</name><styleUrl>#%s</styleUrl>'
                     '<description>%s</description>'
                     '<Point><coordinates>%.6f,%.6f,0</coordinates></Point></Placemark>'
                     % (esc(key), c, '<br/>'.join(desc), p['lon'], p['lat']))
        o.append('</Folder>')

    # Route geometry, for context only. Import ignores LineStrings: routes come
    # from OSRM, so a line dragged here would be overwritten on the next fetch.
    if routes:
        o.append('<Folder><name>routes (context only)</name>')
        for rid, r in sorted(routes.items()):
            coords = ' '.join('%.6f,%.6f,0' % (lon, lat) for lat, lon in r['geometry'])
            o.append('<Placemark><name>%s</name><LineString><tessellate>1</tessellate>'
                     '<coordinates>%s</coordinates></LineString></Placemark>' % (esc(rid), coords))
        o.append('</Folder>')

    o.append('</Document></kml>')
    io.open(path, 'w', encoding='utf-8').write('\n'.join(o))

    print('wrote %d places -> %s' % (len(places), path))
    for sid, _, _, label in STYLES:
        if counts.get(sid):
            print('  %-11s %3d  %s' % (sid, counts[sid], label))
    print('\nNext: import that file as a layer at https://www.google.com/mymaps,')
    print('check the red and amber pins first, drag anything wrong, then')
    print('Export to KML and run:  python3 tools/kml.py --import <file> --write')


# --------------------------------------------------------------------- import
def tag(el):
    """Local tag name, ignoring whichever KML namespace Google used today."""
    return el.tag.rsplit('}', 1)[-1]


def read_kml(path):
    """Parse KML or KMZ into [(folder, name, lat, lon)] for every Point."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower().endswith('.kml')]
            if not names:
                sys.exit('error: %s is a zip with no .kml inside' % path)
            data = z.read(names[0])
    else:
        data = io.open(path, 'rb').read()
    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        sys.exit('error: %s is not parseable XML: %s' % (path, e))

    out, lines = [], []

    def walk(el, folder):
        for ch in el:
            t = tag(ch)
            if t in ('Folder', 'Document'):
                nm = next(((g.text or '').strip() for g in ch if tag(g) == 'name'), '')
                walk(ch, nm or folder)
            elif t == 'Placemark':
                name = coords = None
                geom = None
                for g in ch.iter():
                    gt = tag(g)
                    if gt == 'name' and name is None:
                        name = (g.text or '').strip()
                    elif gt == 'coordinates':
                        coords = (g.text or '').strip()
                    elif gt in ('LineString', 'Polygon'):
                        geom = gt
                if geom or not coords:
                    lines.append(name or '(unnamed)')
                    continue
                # KML is lon,lat[,alt] - the opposite order to everything else here.
                first = coords.split()[0].split(',')
                out.append((folder, name or '', float(first[1]), float(first[0])))
            else:
                walk(ch, folder)

    walk(root, None)
    return out, lines


def merge(dest, path, write, add_new, max_move):
    places = dest.load('places.json')
    pins, lines = read_kml(path)
    if not pins:
        sys.exit('error: no Point placemarks found in %s' % path)
    today = time.strftime('%Y-%m-%d')

    moved, same, new, far = [], [], [], []
    seen = set()
    for folder, name, lat, lon in pins:
        key = name.strip()
        if key not in places:
            new.append((folder, key, lat, lon))
            continue
        seen.add(key)
        p = places[key]
        d = metres((p['lat'], p['lon']), (lat, lon))
        if d > max_move:
            far.append((key, d, lat, lon))
        elif d >= DRAG_M:
            moved.append((key, d, lat, lon))
        else:
            same.append((key, d, lat, lon))

    print('read %d pins from %s' % (len(pins), os.path.basename(path)))
    if lines:
        print('  (ignored %d line/shape placemarks: %s)'
              % (len(lines), ', '.join(lines[:4]) + ('...' if len(lines) > 4 else '')))

    if moved:
        print('\n--- moved (a real correction) ---')
        for key, d, lat, lon in sorted(moved, key=lambda r: -r[1]):
            print('  %7.0f m  %-34s %.5f,%.5f  was %s'
                  % (d, key[:34], lat, lon, places[key].get('source', '')[:28]))
    if same:
        print('\n--- confirmed in place (%d) ---' % len(same))
        for key, d, lat, lon in sorted(same):
            print('  %7.1f m  %-34s %s' % (d, key[:34], places[key].get('source', '')[:34]))

    # Loud about everything it will not apply. A correction dropped in silence
    # is worse than one refused out loud.
    problems = 0
    if far:
        print('\n--- OVER --max-move (%.0f m): NOT applied ---' % max_move)
        for key, d, lat, lon in sorted(far, key=lambda r: -r[1]):
            print('  %7.0f m  %-34s stored %.5f,%.5f  kml %.5f,%.5f'
                  % (d, key[:34], places[key]['lat'], places[key]['lon'], lat, lon))
        print('  A move this large is usually the wrong file or a renamed pin.')
        print('  Raise --max-move if it really did move that far.')
        problems += len(far)
    if new:
        print('\n--- in the KML but not in places.json ---')
        for folder, key, lat, lon in sorted(new, key=lambda r: r[1]):
            print('  %-34s %.5f,%.5f  (layer: %s)' % (key[:34], lat, lon, folder or '?'))
        if add_new:
            print('  --add-new given: these will be added.')
        else:
            print('  A pin here means it was renamed or newly dropped. The name must')
            print('  match the label in markers.py exactly. Pass --add-new to add them.')
            problems += len(new)
    missing = sorted(set(places) - seen)
    if missing:
        print('\n--- in places.json but not in the KML (left untouched) ---')
        for key in missing:
            print('  %s' % key)

    if not write:
        print('\n(dry run - pass --write to apply)')
        return 1 if problems else 0

    n = 0
    for key, d, lat, lon in moved:
        p = places[key]
        prior = p.get('source', '')
        if prior and not prior.startswith('gmaps:'):
            p['was'] = prior
        p['lat'], p['lon'] = round(lat, 5), round(lon, 5)
        p['source'] = 'gmaps: dragged %.0f m on Google basemap' % d
        p['verified'] = today
        n += 1
    for key, d, lat, lon in same:
        p = places[key]
        prior = p.get('source', '')
        if prior and not prior.startswith('gmaps:'):
            p['was'] = prior
        p['source'] = 'gmaps: confirmed'
        p['verified'] = today
        n += 1
    if add_new:
        for folder, key, lat, lon in new:
            places[key] = {'lat': round(lat, 5), 'lon': round(lon, 5), 'query': key,
                           'region': folder, 'source': 'gmaps: added by hand',
                           'verified': today}
            n += 1

    json.dump(places, io.open(os.path.join(dest.mapdir, 'places.json'), 'w'),
              indent=1, ensure_ascii=False, sort_keys=True)
    print('\nwrote %d verified pins to places.json' % n)
    left = sorted(k for k, v in places.items()
                  if confidence(v.get('source', '')) == 'unverified')
    if left:
        print('still unverified (%d): %s' % (len(left), ', '.join(left[:6])
                                             + ('...' if len(left) > 6 else '')))
    else:
        print('every place now has a verified coordinate.')
    return 1 if problems else 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Verify places.json against Google My Maps.')
    _dest.add_arg(ap)
    ap.add_argument('--export', action='store_true', help='write maps/places.kml for review')
    ap.add_argument('--import', dest='imp', metavar='FILE',
                    help='merge a KML/KMZ exported back out of Google My Maps')
    ap.add_argument('--write', action='store_true', help='apply the merge (default is a dry run)')
    ap.add_argument('--add-new', action='store_true',
                    help='also add placemarks that are not yet in places.json')
    ap.add_argument('--max-move', type=float, default=25000,
                    help='metres; a pin further than this is reported, never applied')
    a = ap.parse_args()
    d = _dest.resolve(a.dest)
    if a.export == bool(a.imp):
        sys.exit('error: pass exactly one of --export or --import FILE')
    if a.export:
        export(d, os.path.join(d.mapdir, 'places.kml'))
    else:
        if not os.path.exists(a.imp):
            sys.exit('error: no such file: %s' % a.imp)
        sys.exit(merge(d, a.imp, a.write, a.add_new, a.max_move))
