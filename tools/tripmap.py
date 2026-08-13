#!/usr/bin/env python3
"""Build a Google My Maps layer of the whole trip, for use on the phone while driving.

This is the companion to the offline guide, not a replacement for it. The guide
is a self-contained HTML file with local tiles that works on a plane and prints;
this is a live Google map that navigates. Different jobs.

  python3 tools/tripmap.py            -> maps/tripmap.kml

Import it at https://www.google.com/mymaps (Create a new map -> Import), then
open it on the phone in Google Maps under Saved -> Maps. Tapping a pin gives
you the usual Directions button.

One layer per map region, one placemark per stop carrying its sublabel and
whichever practical detail the guide holds, plus the driving legs as lines with
their real distance and duration from routes.json.

Note on what this is not: My Maps will not navigate *along* a drawn line. The
lines are there to show the shape of each day; you tap a pin and hand off to
normal navigation. Google caps an imported layer at 2,000 features and 5 MB,
which this is nowhere near.

Why the pins come from places.json and not from Google's own geocoder: the same
coordinates drive the offline maps in the guide, which are Esri tiles, and Maps
Platform terms 6.2 forbid using Geocoding API output with a non-Google map. One
verified coordinate per place, usable in both places, keeps that clean.

Usage:  python3 tools/tripmap.py [--dest SLUG]
"""
import io, os, sys

import _dest
from kml import esc

# Marker kinds -> a colour that survives Google's import, and a label.
KIND = {
    'base': ('ff2d8f4c', 'Where you sleep'),
    'hi':   ('ff3023a3', 'Marquee sight'),
    'ev':   ('ff26a3d0', 'Evening'),
    'stop': ('ffb8791d', 'Stop'),
    'home': ('ff404040', 'Home'),
}
ICON = 'http://maps.google.com/mapfiles/kml/paddle/%s-blank.png'
PADDLE = {'base': 'grn', 'hi': 'red', 'ev': 'blu', 'stop': 'ylw', 'home': 'wht'}


def hm(sec):
    h, m = int(sec // 3600), int(round((sec % 3600) / 60.0))
    if m == 60:
        h, m = h + 1, 0
    return ('%d h %02d' % (h, m)) if h else ('%d min' % m)


def collect(dest):
    """Ask overlay.py what this trip actually draws, so nothing drifts."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import overlay
    m = overlay.Maps(dest)
    m.collect_only = True
    overlay.load_markers(dest).build(m)
    return m


def main():
    dest, _ = _dest.from_args('Build a Google My Maps layer for driving.')
    m = collect(dest)
    places = dest.load('places.json', default={})
    routes = dest.load('routes.json', default={})
    legs = dest.load('legs.json', default={})
    meta = dest.meta()
    order = list(dest.load('maps.json').keys())

    o = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<kml xmlns="http://www.opengis.net/kml/2.2"><Document>',
         '<name>%s</name>' % esc(meta.get('title', dest.slug)),
         '<description>%s  %s</description>'
         % (esc(meta.get('dates', '')), esc(meta.get('blurb', '')))]
    for kind, (colour, _) in KIND.items():
        o.append('<Style id="%s"><IconStyle><color>%s</color><scale>1.1</scale>'
                 '<Icon><href>%s</href></Icon></IconStyle>'
                 '<LabelStyle><color>%s</color></LabelStyle></Style>'
                 % (kind, colour, ICON % PADDLE[kind], colour))
    o.append('<Style id="leg"><LineStyle><color>ff2d8f4c</color><width>4</width></LineStyle></Style>')

    # ---- one folder per region, markers in the order the guide draws them ----
    seen, n = set(), 0
    for region in sorted(m._specs, key=lambda r: order.index(r) if r in order else 99):
        specs = m._specs[region]
        if not specs:
            continue
        o.append('<Folder><name>%s</name>' % esc(region))
        for s in specs:
            key = s['label'].strip()
            if (region, key) in seen:
                continue
            seen.add((region, key))
            p = places.get(key, {})
            bits = []
            if s['sub']:
                bits.append(esc(s['sub']))
            if s['day'] is not None:
                bits.append('Day %s' % esc(s['daytext'] or s['day']))
            src = str(p.get('source', ''))
            if src.startswith('manual:') or src.startswith('gmaps:'):
                bits.append('<i>%s</i>' % esc(src.split(':', 1)[1].strip()[:120]))
            o.append('<Placemark><name>%s</name><styleUrl>#%s</styleUrl>'
                     '<description>%s</description>'
                     '<Point><coordinates>%.6f,%.6f,0</coordinates></Point></Placemark>'
                     % (esc(key), s['kind'] if s['kind'] in KIND else 'stop',
                        '<br/>'.join(bits), s['lon'], s['lat']))
            n += 1
        o.append('</Folder>')

    # ---- the drives, with their measured numbers in the description ----
    if routes:
        o.append('<Folder><name>Drives</name>')
        for rid in sorted(routes):
            r = routes[rid]
            via = ' → '.join(legs.get(rid, {}).get('via', r.get('via', [])))
            coords = ' '.join('%.5f,%.5f,0' % (lon, lat) for lat, lon in r['geometry'])
            o.append('<Placemark><name>%s</name><styleUrl>#leg</styleUrl>'
                     '<description>%s<br/>%.0f km · %s</description>'
                     '<LineString><tessellate>1</tessellate><coordinates>%s</coordinates>'
                     '</LineString></Placemark>'
                     % (esc(rid), esc(via), r['distance_m'] / 1000.0, hm(r['duration_s']), coords))
        o.append('</Folder>')

    o.append('</Document></kml>')
    path = os.path.join(dest.mapdir, 'tripmap.kml')
    io.open(path, 'w', encoding='utf-8').write('\n'.join(o))
    kb = os.path.getsize(path) // 1024
    print('wrote %d places and %d drives -> %s  (%d KB)' % (n, len(routes), path, kb))
    print('\nImport at https://www.google.com/mymaps → Create a new map → Import.')
    print('Then on the phone: Google Maps → Saved → Maps.')
    if kb > 4500:
        print('!! over 4.5 MB - Google caps an imported layer at 5 MB.')


if __name__ == '__main__':
    main()
