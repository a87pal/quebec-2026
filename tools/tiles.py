#!/usr/bin/env python3
"""Download Esri World Topo basemap tiles for each map's bounding box.

Reads the bounding boxes and zooms from destinations/<slug>/maps/maps.json and
writes tiles to <slug>/images/tiles/<map>/<x>_<y>.jpg.

Also writes tilemeta.json, the contract between this script and overlay.py: for
each map it records zoom z, the tile range, the composite size W/H, and the
pixel origin ox/oy of the top-left tile. A marker's SVG position is the
web-mercator pixel at zoom z minus (ox, oy). Both scripts implement that
projection and THEY MUST AGREE - if markers are uniformly offset, look here
first. tilemeta.json must land where overlay.py reads it, which is why it is
written next to maps.json rather than anywhere else.

Esri's tile URL is /tile/{z}/{y}/{x} - row before column. Getting this
backwards yields a plausible-looking map of somewhere else entirely.

Existing tiles are skipped, so re-running is cheap and offline.

Usage:  python3 tools/tiles.py [--dest SLUG]
"""
import json, math, os, time, urllib.request

import _dest

H = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36'}
TPL = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"


def px(lat, lon, z):
    n = 2 ** z
    x = (lon + 180.0) / 360.0 * n * 256
    lr = math.radians(lat)
    y = (1.0 - math.log(math.tan(lr) + 1 / math.cos(lr)) / math.pi) / 2.0 * n * 256
    return x, y


def main():
    dest, _ = _dest.from_args('Download basemap tiles for a destination.')
    MAPS = dest.load('maps.json')
    DEST = dest.tiles
    os.makedirs(DEST, exist_ok=True)

    meta = {}
    for name, cfg in MAPS.items():
        z = cfg['z']
        x0, y1 = px(cfg['lat'][0], cfg['lon'][0], z)   # SW -> min x, max y
        x1, y0 = px(cfg['lat'][1], cfg['lon'][1], z)   # NE -> max x, min y
        tx0, tx1 = int(x0 // 256), int(x1 // 256)
        ty0, ty1 = int(y0 // 256), int(y1 // 256)
        nw, nh = tx1 - tx0 + 1, ty1 - ty0 + 1
        meta[name] = dict(z=z, tx0=tx0, tx1=tx1, ty0=ty0, ty1=ty1, W=nw * 256, H=nh * 256,
                          ox=tx0 * 256, oy=ty0 * 256)
        print(name, 'z', z, 'tiles', nw, 'x', nh, '=', nw * nh, '  px', nw * 256, 'x', nh * 256)

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
