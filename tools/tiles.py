#!/usr/bin/env python3
"""Download Esri World Topo basemap tiles for each map's bounding box.

Reads the bounding boxes and zooms from destinations/<slug>/maps/maps.json and
writes tiles to <slug>/images/tiles/<map>/<x>_<y>.jpg.

Also writes tilemeta.json, the contract between this script and overlay.py: for
each map it records zoom z, the tile range, the composite size W/H, and the
pixel origin ox/oy of the top-left tile. A marker's SVG position is the
web-mercator pixel at zoom z minus (ox, oy). Both scripts get that projection
from tools/_proj.py so they cannot disagree. tilemeta.json must still land
where overlay.py reads it, which is why it is written next to maps.json rather
than anywhere else.

Esri's tile URL is /tile/{z}/{y}/{x} - row before column. Getting this
backwards yields a plausible-looking map of somewhere else entirely.

Existing tiles are skipped, so re-running is cheap and offline.

Usage:  python3 tools/tiles.py [--dest SLUG]
"""
import json, os, time, urllib.request

import _dest, _proj

H = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36'}
TPL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"


def main():
    dest, _ = _dest.from_args('Download basemap tiles for a destination.')
    MAPS = dest.load('maps.json')
    DEST = dest.tiles
    os.makedirs(DEST, exist_ok=True)

    meta = {}
    for name, cfg in MAPS.items():
        m = _proj.tilemeta(cfg['z'], cfg['lat'], cfg['lon'])
        meta[name] = m
        nw, nh = m['tx1'] - m['tx0'] + 1, m['ty1'] - m['ty0'] + 1
        print(name, 'z', m['z'], 'tiles', nw, 'x', nh, '=', nw * nh, '  px', m['W'], 'x', m['H'])

    metapath = os.path.join(dest.mapdir, 'tilemeta.json')
    os.makedirs(dest.mapdir, exist_ok=True)
    json.dump(meta, open(metapath, 'w'))
    total = sum((m['tx1'] - m['tx0'] + 1) * (m['ty1'] - m['ty0'] + 1) for m in meta.values())
    print('TOTAL TILES', total, '->', metapath)

    got = 0; fail = 0
    for name, m in meta.items():
        d = os.path.join(DEST, name); os.makedirs(d, exist_ok=True)
        for tx in range(m['tx0'], m['tx1'] + 1):
            for ty in range(m['ty0'], m['ty1'] + 1):
                f = os.path.join(d, '%d_%d.jpg' % (tx, ty))
                if os.path.exists(f) and os.path.getsize(f) > 1500:
                    got += 1; continue
                u = TPL.format(z=m['z'], x=tx, y=ty)
                ok = False
                for a in range(3):
                    try:
                        b = urllib.request.urlopen(urllib.request.Request(u, headers=H), timeout=30).read()
                        open(f, 'wb').write(b); ok = True; got += 1; break
                    except Exception:
                        time.sleep(2 + a * 3)
                if not ok:
                    fail += 1; print('FAIL', name, tx, ty)
                time.sleep(0.12)
        print('done', name)
    print('tiles ok', got, 'failed', fail)


if __name__ == '__main__':
    main()
