# -*- coding: utf-8 -*-
"""Project lat/lon onto the downloaded tiles and draw routes, markers and labels.

This file is the engine and knows nothing about any particular trip. The
markers, routes, legends and captions for a destination live in
destinations/<slug>/maps/markers.py, which defines build(m) and returns
{map_name: html_fragment}.

Usage:  python3 tools/overlay.py [--dest SLUG]
"""
import math, html, importlib.util, os, sys

import _dest


class Maps(object):
    """Drawing context for one destination.

    Geometry is in tile-composite pixels; `k` rescales stroke widths and font
    sizes so a map rendered at 720 px reads the same as one at 1100 px.
    """

    def __init__(self, dest):
        self.dest = dest
        self.meta = dest.load('tilemeta.json')
        self.cfg = dest.load('maps.json')
        # Coordinates come from places.json, not from the literals at the call
        # sites in markers.py. Those are fallbacks only. Never fix a marker's
        # position by editing the literal - fix the query in places.json and
        # re-run resolve.py, or pin it as "manual:".
        self.places = dest.load('places.json', default={})
        self.unsourced = []
        self.k = 1.0

    def dispw(self, name):
        return self.cfg.get(name, {}).get('dispw', 1100)

    def mk(self, name):
        if name not in self.meta:
            sys.exit('error: no tile metadata for map "%s" - run tiles.py' % name)
        m = self.meta[name]
        z, ox, oy = m['z'], m['ox'], m['oy']
        self.k = m['W'] / self.dispw(name)

        def P(lat, lon):
            n = 2 ** z
            x = (lon + 180.0) / 360.0 * n * 256 - ox
            lr = math.radians(lat)
            y = (1.0 - math.log(math.tan(lr) + 1 / math.cos(lr)) / math.pi) / 2.0 * n * 256 - oy
            return round(x, 1), round(y, 1)

        return P, m

    def path(self, P, pts):
        return " ".join(("M" if i == 0 else "L") + "%s,%s" % P(a, b) for i, (a, b) in enumerate(pts))

    def dash(self, cls, P, pts, w):
        return '<path class="%s" d="%s" stroke-width="%.1f"/>' % (cls, self.path(P, pts), w * self.k)

    def route(self, P, pts, cls="rt", w=7):
        k = self.k
        d = self.path(P, pts)
        return ('<path class="cas" d="%s" stroke-width="%.1f"/><path class="%s" d="%s" stroke-width="%.1f"/>'
                % (d, (w + 5) * k, cls, d, w * k))

    def marker(self, P, lat, lon, label, sub="", kind="stop", n=None, anchor="start",
               dx=None, dy=0, r=None, day=None, daytext=None, lead=False):
        k = self.k
        pl = self.places.get(label.strip())
        if pl:
            lat, lon = pl['lat'], pl['lon']
        else:
            self.unsourced.append(label.strip())
        x, y = P(lat, lon)
        rr = (r if r else (11 if kind in ('base', 'hi') else 8)) * k
        dx = (dx * k) if dx is not None else (rr + 8 * k if anchor == "start" else -(rr + 8 * k))
        dy = dy * k
        fs = 16 * k; fs2 = 13 * k; sw = 5 * k; sw2 = 4.2 * k; cs = 3.2 * k
        o = '<g class="mk %s">' % kind
        if lead:
            ex = x + dx - (5 * k if anchor == 'start' else -5 * k)
            ey = y + dy + 5 * k - fs * 0.35
            o += '<path class="ldr" d="M%.1f,%.1f L%.1f,%.1f" stroke-width="%.1f"/>' % (x, y, ex, ey, 1.7 * k)
        o += '<circle cx="%.1f" cy="%.1f" r="%.1f" stroke-width="%.1f"/>' % (x, y, rr, cs)
        if n:
            o += '<text class="mn" x="%.1f" y="%.1f" text-anchor="middle" font-size="%.1f">%s</text>' % (x, y + 4 * k, fs2, n)
        o += '<text class="ml" x="%.1f" y="%.1f" text-anchor="%s" font-size="%.1f" stroke-width="%.1f">%s</text>' % (x + dx, y + dy + 5 * k, anchor, fs, sw, html.escape(label))
        if sub:
            o += '<text class="ms" x="%.1f" y="%.1f" text-anchor="%s" font-size="%.1f" stroke-width="%.1f">%s</text>' % (x + dx, y + dy + 5 * k + fs * 1.15, anchor, fs2, sw2, html.escape(sub))
        if daytext:
            bw = (len(daytext) * 8.4 + 15) * k; bh = 21 * k
            bx = (x - rr - 7 * k - bw) if anchor == "start" else (x + rr + 7 * k)
            o += ('<g class="dayb"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f"/>'
                  '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="%.1f">%s</text></g>'
                  % (bx, y - bh / 2, bw, bh, bh / 2, bx + bw / 2, y + 4.8 * k, 12.5 * k, html.escape(daytext)))
        o += '</g>'
        if day is not None:
            o = '<a class="mklink" href="#day-%s" aria-label="%s — go to day %s">%s</a>' % (day, html.escape(label), day, o)
        return o

    def wrap(self, name, body, legend, cap, gmaps):
        m = self.meta[name]
        tiles = []
        W, H = m['W'], m['H']
        for tx in range(m['tx0'], m['tx1'] + 1):
            for ty in range(m['ty0'], m['ty1'] + 1):
                l = (tx * 256 - m['ox']) / W * 100
                t = (ty * 256 - m['oy']) / H * 100
                tiles.append('<img src="images/tiles/%s/%d_%d.jpg" alt="" loading="lazy" style="left:%.4f%%;top:%.4f%%;width:%.4f%%"/>'
                             % (name, tx, ty, l, t, 256 / W * 100))
        return ('<div class="gmapwrap">\n<div class="gmap" style="aspect-ratio:%d/%d">\n<div class="tiles">%s</div>\n'
                '<svg class="ovl" viewBox="0 0 %d %d" preserveAspectRatio="none" role="img" aria-label="%s">%s</svg>\n</div>\n'
                '<div class="mapside"><button class="mapzoom" type="button" aria-expanded="false">'
                '<span>Expand map</span> <i>⤢</i></button>\n'
                '<div class="cap">%s <span class="attrib">Basemap: Esri World Topo — Esri, HERE, Garmin, USGS, NGA, OpenStreetMap contributors.</span></div></div>\n'
                '<div class="gmapfoot"><div class="maplegend">%s</div>'
                '<a class="gbtn" target="_blank" rel="noopener" href="%s">Open this route in Google Maps ↗</a></div>\n</div>'
                % (W, H, ''.join(tiles), W, H, html.escape(cap[:110]), body, cap, legend, gmaps))


def load_markers(dest):
    """Import destinations/<slug>/maps/markers.py as a module."""
    p = os.path.join(dest.mapdir, 'markers.py')
    if not os.path.exists(p):
        sys.exit('error: %s missing' % p)
    spec = importlib.util.spec_from_file_location('markers_%s' % dest.slug.replace('-', '_'), p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not hasattr(mod, 'build'):
        sys.exit('error: %s must define build(m)' % p)
    return mod


def main():
    dest, _ = _dest.from_args('Draw map overlays for a destination.')
    m = Maps(dest)
    frag = load_markers(dest).build(m)

    missing = [k for k in m.cfg if k not in frag]
    if missing:
        print('!! maps.json declares %s but markers.py produced no fragment' % ', '.join(missing))

    for name, v in frag.items():
        with open(dest.fragment(name), 'w', encoding='utf-8') as f:
            f.write(v)
        print('wrote', name, len(v), 'bytes')

    if m.unsourced:
        print('\n!! %d markers have no places.json entry (using the literal in markers.py):' % len(m.unsourced))
        for u in sorted(set(m.unsourced)):
            print('   ', u)
        print('   run: python3 tools/resolve.py --dest %s --seed && '
              'python3 tools/resolve.py --dest %s --write' % (dest.slug, dest.slug))


if __name__ == '__main__':
    main()
