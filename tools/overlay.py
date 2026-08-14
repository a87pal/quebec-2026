# -*- coding: utf-8 -*-
"""Project lat/lon onto the downloaded tiles and draw routes, markers and labels.

This file is the engine and knows nothing about any particular trip. The
markers, routes, legends and captions for a destination live in
destinations/<slug>/maps/markers.py, which defines build(m) and returns
{map_name: html_fragment}.

Label placement is automatic. marker() does not emit anything when it is
called: it records what it was asked to draw and returns a placeholder, and
wrap() runs a placement pass over the whole map once every dot, route and label
is known. Each label tries a series of candidate positions - beside the dot,
above, below, then further out on a leader line - and takes the first that
collides with nothing. Before this, every marker carried hand-tuned dx/dy/lead
values that had to be re-nudged against boxes.py after any coordinate change;
tools/README.md called it the weakest part of the toolchain.

anchor / dx / dy at a call site still win. They are overrides for the cases
where the automatic answer is merely legal rather than right.

Usage:  python3 tools/overlay.py [--dest SLUG]
"""
import html, importlib.util, json, os, sys

import _dest, _metrics, _proj

# Draw order for placement: the labels that matter most get first pick of the
# space around them, and everything else places around what is already down.
PRIORITY = ('base', 'hi', 'ev', 'stop', 'home')

GAP = 8.0           # unscaled px between a dot's edge and its label
SLACK = 4.0         # composite px of overlap tolerated before it counts
PAD = 4.0           # keep labels this far inside the map edge

# Candidate rows beside the dot, in unscaled px, best first.
ROWS = (0.0, -13.0, 13.0, -26.0, 26.0, -39.0, 39.0)
# Leader-line radii, tried only once the tidy positions are all taken.
LEAD_R = (34.0, 52.0, 72.0, 96.0)
LEAD_DIRS = ((1, 0), (-1, 0), (1, -1), (-1, -1), (1, 1), (-1, 1), (0, -1), (0, 1))


class Maps(object):
    """Drawing context for one destination.

    Geometry is in tile-composite pixels; each map's `k` rescales stroke widths
    and font sizes so a map rendered at 720 px reads the same as one at 1100 px.
    k is looked up per map rather than held as mutable state, so drawing two
    maps in an interleaved order cannot silently pick up the wrong scale.
    """

    def __init__(self, dest):
        self.dest = dest
        self.meta = dest.load('tilemeta.json')
        self.cfg = dest.load('maps.json')
        # Coordinates come from places.json, not from the literals at the call
        # sites in markers.py. Those are fallbacks only. Never fix a marker's
        # position by editing the literal - correct the pin in Google My Maps
        # and re-run kml.py, fix the query and re-run resolve.py, or pin it as
        # "manual:".
        self.places = dest.load('places.json', default={})
        self.routes = dest.load('routes.json', default={})
        self.legs = dest.load('legs.json', default={})
        # Optional: the Google My Maps id from meta.json. When set, each map gets
        # a button that swaps the Esri tiles for the live map centred on the same
        # ground. Absent, nothing is emitted and the guide is unchanged - which
        # is the case for any destination that has not been imported to My Maps.
        self.mymaps = (dest.meta().get('mymaps') or '').strip()
        self.unsourced = []
        self.outside = []
        self.schematic = []
        self.crowded = []
        self.routed = {}                # map -> {provider} actually drawn, for attribution
        self.collect_only = False       # metrics.py harvests labels without placing
        self._cur = None
        self._specs = {}                # map -> [marker spec]
        self._paths = {}                # map -> [sampled route points]
        self._k = {}                    # map -> scale factor
        self.placed = {}                # map -> [placed boxes], for boxes.py

    # ------------------------------------------------------------- geometry
    def dispw(self, name):
        return self.cfg.get(name, {}).get('dispw', 1100)

    def mk(self, name):
        if name not in self.meta:
            sys.exit('error: no tile metadata for map "%s" - run tiles.py' % name)
        m = self.meta[name]
        self._cur = name
        self._k[name] = m['W'] / self.dispw(name)
        self._specs.setdefault(name, [])
        self._paths.setdefault(name, [])
        return _proj.projector(m), m

    @property
    def k(self):
        return self._k[self._cur]

    def _sample(self, pts):
        """Remember a drawn line so labels can be scored against crossing it."""
        step = 7.0
        out = []
        for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
            d = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            n = max(1, int(d / step))
            for i in range(n):
                t = i / float(n)
                out.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
        if pts:
            out.append(pts[-1])
        self._paths[self._cur].extend(out)

    # ------------------------------------------------------------- lines
    def path(self, P, pts):
        xy = [P(a, b) for a, b in pts]
        self._sample(xy)
        return " ".join(("M" if i == 0 else "L") + "%s,%s" % p for i, p in enumerate(xy))

    def dash(self, cls, P, pts, w):
        return '<path class="%s" d="%s" stroke-width="%.1f"/>' % (cls, self.path(P, pts), w * self.k)

    def route(self, P, pts, cls="rt", w=7):
        k = self.k
        d = self.path(P, pts)
        return ('<path class="cas" d="%s" stroke-width="%.1f"/><path class="%s" d="%s" stroke-width="%.1f"/>'
                % (d, (w + 5) * k, cls, d, w * k))

    def leg(self, P, rid, fallback=None):
        """Draw a declared leg using the road geometry fetched by routes.py.

        Falls back to the schematic vertex list at the call site when the leg
        has not been fetched yet, so a guide still builds - and says so - before
        anyone has run routes.py. TRAVEL-PREFERENCES section 8 asks that a line
        which is not real geometry be labelled schematic; self.schematic is what
        the caption generator uses to do that.
        """
        spec = self.legs.get(rid)
        if spec is None:
            sys.exit('error: leg "%s" is not declared in legs.json' % rid)
        r = self.routes.get(rid)
        cls = spec.get('cls', 'rt')
        w = spec.get('w', 7 if spec.get('style', 'route') == 'route' else 5)
        if r:
            pts = [(a, b) for a, b in r['geometry']]
            # Thin to what this map can actually show. OSRM returns a vertex
            # every few metres; at z8 that is thousands of points inside one
            # pixel, and it all ends up inline in the guide.
            xy = [P(a, b) for a, b in pts]
            xy = _proj.simplify(xy, 0.6)
            d = " ".join(("M" if i == 0 else "L") + "%s,%s" % p for i, p in enumerate(xy))
            self._sample(xy)
            self.routed.setdefault(self._cur, set()).add(r.get('source', 'osrm'))
        else:
            if not fallback:
                sys.exit('error: leg "%s" has no geometry and no fallback' % rid)
            self.schematic.append(rid)
            d = self.path(P, fallback)
        k = self.k
        if spec.get('style', 'route') == 'dash':
            return '<path class="%s" d="%s" stroke-width="%.1f"/>' % (cls, d, w * k)
        return ('<path class="cas" d="%s" stroke-width="%.1f"/><path class="%s" d="%s" stroke-width="%.1f"/>'
                % (d, (w + 5) * k, cls, d, w * k))

    # ------------------------------------------------------------- markers
    def marker(self, P, lat, lon, label, sub="", kind="stop", n=None, anchor=None,
               dx=None, dy=None, r=None, day=None, daytext=None, lead=None,
               allow_unsourced=False):
        """Record a marker. The SVG is emitted later, by wrap()."""
        name = self._cur
        k = self._k[name]
        key = label.strip()
        pl = self.places.get(key)
        if pl:
            lat, lon = pl['lat'], pl['lon']
        elif not allow_unsourced:
            self.unsourced.append(key)
        else:
            self.schematic.append(key)

        cfg = self.cfg.get(name, {})
        if pl and 'lat' in cfg and 'lon' in cfg:
            # A coordinate outside the map it is drawn on is not a placement
            # problem, it is a wrong coordinate: this is the check that catches
            # a geocoder answering with the right name in the wrong country.
            if not (cfg['lat'][0] <= lat <= cfg['lat'][1] and cfg['lon'][0] <= lon <= cfg['lon'][1]):
                self.outside.append((name, key, lat, lon))

        x, y = P(lat, lon)
        rr = (r if r else (11 if kind in ('base', 'hi') else 8)) * k
        spec = dict(x=x, y=y, rr=rr, lat=lat, lon=lon, label=label, sub=sub, kind=kind,
                    n=n, day=day, daytext=daytext, k=k, map=name,
                    anchor=anchor, dx=dx, dy=dy, lead=lead)
        if daytext:
            bw = (len(daytext) * 8.4 + 15) * k
            bh = 21 * k
            spec['pill'] = (bw, bh)
        self._specs[name].append(spec)
        return '\x00mk%d\x00' % (len(self._specs[name]) - 1)

    def all_specs(self):
        for name in self._specs:
            for s in self._specs[name]:
                yield s

    # ------------------------------------------------------------- placement
    def _box(self, s, cand):
        anchor, dx, dy, lead = cand
        k = s['k']
        fs, fs2 = 16 * k, 13 * k
        lx = s['x'] + dx
        ly = s['y'] + dy + 5 * k
        w = _metrics.width(s['label'], fs, 800)
        if s['sub']:
            w = max(w, _metrics.width(s['sub'], fs2, 600))
        if anchor == 'start':
            x0 = lx
        elif anchor == 'end':
            x0 = lx - w
        else:
            x0 = lx - w / 2.0
        sy = ly + fs * 1.15 if s['sub'] else None
        return dict(x0=x0, x1=x0 + w, y0=ly - fs * 0.8, y1=(sy if sy else ly) + fs * 0.4,
                    lx=lx, ly=ly, sy=sy, anchor=anchor, dx=dx, dy=dy, lead=lead,
                    w=w, label=s['label'])

    def _candidates(self, s):
        k = s['k']
        rr = s['rr']
        off = rr + GAP * k
        # A call site that pins all three gets exactly what it asked for.
        if s['anchor'] and s['dx'] is not None and s['dy'] is not None:
            yield (s['anchor'], s['dx'] * k, s['dy'] * k, bool(s['lead']))
            return
        anchors = [s['anchor']] if s['anchor'] else ['start', 'end']
        fixed_dx = s['dx'] * k if s['dx'] is not None else None
        fixed_dy = s['dy'] * k if s['dy'] is not None else None
        # A pinned dy fixes the row but still leaves both sides of the dot open.
        rows = [fixed_dy] if fixed_dy is not None else [r * k for r in ROWS]
        for dy in rows:
            for a in anchors:
                dx = fixed_dx if fixed_dx is not None else (off if a == 'start' else -off)
                yield (a, dx, dy, False)
        if s['dx'] is None and s['dy'] is None:
            for dy in (-(rr + 16 * k), rr + 26 * k):
                yield ('middle', 0.0, dy, False)
            for R in LEAD_R:
                for ux, uy in LEAD_DIRS:
                    a = 'start' if ux > 0 else ('end' if ux < 0 else 'middle')
                    yield (a, ux * R * k, uy * R * k, True)

    def _place(self, name):
        specs = self._specs.get(name, [])
        if not specs:
            return
        m = self.meta[name]
        W, H = m['W'], m['H']
        dots = [(s['x'], s['y'], s['rr']) for s in specs]
        samples = self._paths.get(name, [])
        taken = []

        def inside(b):
            return b['x0'] >= PAD and b['y0'] >= PAD and b['x1'] <= W - PAD and b['y1'] <= H - PAD

        def hits_box(b, o):
            dx = min(b['x1'], o['x1']) - max(b['x0'], o['x0'])
            dy = min(b['y1'], o['y1']) - max(b['y0'], o['y0'])
            return dx > SLACK and dy > SLACK

        def hits_dot(b, i):
            for j, (cx, cy, rad) in enumerate(dots):
                if j == i:
                    continue
                # Nearest point on the box to the dot's centre: a real
                # circle-rectangle test, so clipping the edge of a 21 px dot
                # counts, which a centre-point test misses.
                nx = min(max(cx, b['x0']), b['x1'])
                ny = min(max(cy, b['y0']), b['y1'])
                if (cx - nx) ** 2 + (cy - ny) ** 2 < rad * rad:
                    return True
            return False

        def crossings(b):
            return sum(1 for px_, py_ in samples if b['x0'] < px_ < b['x1'] and b['y0'] < py_ < b['y1'])

        order = sorted(range(len(specs)),
                       key=lambda i: (PRIORITY.index(specs[i]['kind'])
                                      if specs[i]['kind'] in PRIORITY else len(PRIORITY),
                                      round(specs[i]['y'], 1), round(specs[i]['x'], 1),
                                      specs[i]['label']))
        out = [None] * len(specs)
        for i in order:
            s = specs[i]
            best = fallback = None
            for rank, cand in enumerate(self._candidates(s)):
                b = self._box(s, cand)
                legal = inside(b) and not hits_dot(b, i) and not any(hits_box(b, o) for o in taken)
                # A label lying along a route is legible - they are drawn with a
                # white halo under the text - so crossing is a tie-breaker, not
                # a veto. Being off the map or on top of another label is not.
                score = rank + crossings(b) * 0.35 + (2.0 if cand[3] else 0.0)
                if legal:
                    if best is None or score < best[0]:
                        best = (score, b)
                    if score <= rank:
                        break
                elif fallback is None or score < fallback[0]:
                    fallback = (score, b)
            if best is None:
                # Nothing fits. Take the least-bad and say so rather than
                # emitting a clean-looking map with two labels on top of
                # each other.
                best = fallback
                self.crowded.append((name, s['label']))
            out[i] = best[1]
            taken.append(best[1])
            if s.get('pill'):
                # The day badge is drawn on the far side of the dot from the
                # label, so where it lands is only known once the anchor is.
                bw, bh = s['pill']
                bx = (s['x'] - s['rr'] - 7 * s['k'] - bw) if best[1]['anchor'] == 'start' \
                    else (s['x'] + s['rr'] + 7 * s['k'])
                taken.append(dict(x0=bx, x1=bx + bw, y0=s['y'] - bh / 2, y1=s['y'] + bh / 2,
                                  label=s['label'] + ' (day badge)'))
        self.placed[name] = out

    # ------------------------------------------------------------- emitting
    def _svg(self, s, b):
        k = s['k']
        x, y, rr = s['x'], s['y'], s['rr']
        fs, fs2 = 16 * k, 13 * k
        o = '<g class="mk %s">' % s['kind']
        if b['lead']:
            ex = b['lx'] - (5 * k if b['anchor'] == 'start' else (-5 * k if b['anchor'] == 'end' else 0))
            ey = b['ly'] - fs * 0.35
            o += '<path class="ldr" d="M%.1f,%.1f L%.1f,%.1f" stroke-width="%.1f"/>' % (x, y, ex, ey, 1.7 * k)
        o += '<circle cx="%.1f" cy="%.1f" r="%.1f" stroke-width="%.1f"/>' % (x, y, rr, 3.2 * k)
        if s['n']:
            o += ('<text class="mn" x="%.1f" y="%.1f" text-anchor="middle" font-size="%.1f">%s</text>'
                  % (x, y + 4 * k, fs2, s['n']))
        o += ('<text class="ml" x="%.1f" y="%.1f" text-anchor="%s" font-size="%.1f" stroke-width="%.1f">%s</text>'
              % (b['lx'], b['ly'], b['anchor'], fs, 5 * k, html.escape(s['label'])))
        if s['sub']:
            o += ('<text class="ms" x="%.1f" y="%.1f" text-anchor="%s" font-size="%.1f" stroke-width="%.1f">%s</text>'
                  % (b['lx'], b['sy'], b['anchor'], fs2, 4.2 * k, html.escape(s['sub'])))
        if s['daytext']:
            bw, bh = s['pill']
            bx = (x - rr - 7 * k - bw) if b['anchor'] == 'start' else (x + rr + 7 * k)
            o += ('<g class="dayb"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f"/>'
                  '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="%.1f">%s</text></g>'
                  % (bx, y - bh / 2, bw, bh, bh / 2, bx + bw / 2, y + 4.8 * k, 12.5 * k,
                     html.escape(s['daytext'])))
        o += '</g>'
        if s['day'] is not None:
            o = ('<a class="mklink" href="#day-%s" aria-label="%s — go to day %s">%s</a>'
                 % (s['day'], html.escape(s['label']), s['day'], o))
        elif s.get('lat') is not None:
            # TRAVEL-PREFERENCES section 8: pair maps with live navigation
            # links. Every pin has a verified coordinate, so every marker that
            # is not already a day deep-link becomes one.
            href = ('https://www.google.com/maps/search/?api=1&amp;query=%.5f,%.5f'
                    % (s['lat'], s['lon']))
            # A Place ID names one exact place, so the link opens the real
            # entry - hours, phone, Directions - instead of dropping a pin at a
            # coordinate. The coordinate stays as `query` on purpose: Google
            # uses it only when the place ID will not resolve, so an ID that
            # goes stale degrades to the right spot rather than a wrong guess.
            pid = (self.places.get(s['label'].strip()) or {}).get('place_id')
            if pid:
                href += '&amp;query_place_id=' + html.escape(pid)
            o = ('<a class="mklink" target="_blank" rel="noopener" '
                 'href="%s" aria-label="%s — open in Google Maps">%s</a>'
                 % (href, html.escape(s['label']), o))
        return o

    # Routing data is OpenStreetMap-derived and carries an ODbL attribution
    # requirement, so a map only claims a source it actually drew.
    ROUTE_CREDIT = {
        'osrm': 'Routing: OSRM — OpenStreetMap contributors, ODbL.',
        'ors': 'Routing: OpenRouteService — OpenStreetMap contributors, ODbL.',
    }

    def wrap(self, name, body, legend, cap, gmaps):
        m = self.meta[name]
        if not self.collect_only:
            self._place(name)
            specs, boxes = self._specs.get(name, []), self.placed.get(name, [])
            for i, (s, b) in enumerate(zip(specs, boxes)):
                token = '\x00mk%d\x00' % i
                if token not in body:
                    sys.exit('error: marker "%s" on map "%s" was created but never '
                             'added to the fragment body' % (s['label'], name))
                body = body.replace(token, self._svg(s, b))

        tiles = []
        W, H = m['W'], m['H']
        for tx in range(m['tx0'], m['tx1'] + 1):
            for ty in range(m['ty0'], m['ty1'] + 1):
                l = (tx * 256 - m['ox']) / W * 100
                t = (ty * 256 - m['oy']) / H * 100
                tiles.append('<img src="images/tiles/%s/%d_%d.jpg" alt="" loading="lazy" style="left:%.4f%%;top:%.4f%%;width:%.4f%%"/>'
                             % (name, tx, ty, l, t, 256 / W * 100))
        credit = ' '.join(self.ROUTE_CREDIT[s] for s in sorted(self.routed.get(name, ()))
                          if s in self.ROUTE_CREDIT)
        return ('<div class="gmapwrap">\n<div class="gmap" style="aspect-ratio:%d/%d">\n<div class="tiles">%s</div>\n'
                '<svg class="ovl" viewBox="0 0 %d %d" preserveAspectRatio="none" role="img" aria-label="%s">%s</svg>\n</div>\n'
                '%s'
                '<div class="mapside"><button class="mapzoom" type="button" aria-expanded="false">'
                '<span>Expand map</span> <i>⤢</i></button>\n%s'
                '<div class="cap">%s <span class="attrib">Basemap: Esri World Topo — Esri, HERE, Garmin, USGS, NGA, OpenStreetMap contributors.%s</span></div></div>\n'
                '<div class="gmapfoot"><div class="maplegend">%s</div>'
                '<a class="gbtn" target="_blank" rel="noopener" href="%s">Open this route in Google Maps ↗</a></div>\n</div>'
                % (W, H, ''.join(tiles), W, H, html.escape(cap[:110]), body,
                   self.live_host(name, W, H), self.live_button(name), cap,
                   ' ' + credit if credit else '', legend, gmaps))

    # --------------------------------------------------------------- live map
    def live_url(self, name):
        """The My Maps embed for this map's ground, or '' when none is configured.

        Same custom map every time - it is one map of the whole trip - but
        centred and zoomed to match the Esri map it replaces, so "go live" keeps
        you looking at the same place rather than dropping you at the trip's
        centroid.
        """
        if not self.mymaps:
            return ''
        c = self.cfg.get(name, {})
        if 'lat' not in c or 'lon' not in c:
            return ''
        lat = (c['lat'][0] + c['lat'][1]) / 2.0
        lon = (c['lon'][0] + c['lon'][1]) / 2.0
        return ('https://www.google.com/maps/d/embed?mid=%s&amp;ll=%.5f,%.5f&amp;z=%d'
                % (html.escape(self.mymaps), lat, lon, c.get('z', 10)))

    def live_host(self, name, W, H):
        """Empty container. The iframe is built by JS on first click, never on
        load, so a guide opened with no signal still costs nothing."""
        u = self.live_url(name)
        if not u:
            return ''
        return ('<div class="glive" data-embed="%s" style="aspect-ratio:%d/%d"></div>\n'
                % (u, W, H))

    def live_button(self, name):
        if not self.live_url(name):
            return ''
        return ('<button class="maplive" type="button" aria-pressed="false">'
                '<span>Live map</span> <i>◉</i></button>\n')


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
        print('wrote %s %d bytes  %d markers%s'
              % (name, len(v), len(m._specs.get(name, [])),
                 '  %d placed on a leader' % sum(1 for b in m.placed.get(name, []) if b['lead'])
                 if any(b['lead'] for b in m.placed.get(name, [])) else ''))

    # The placement boxes, for boxes.py to verify. Writing them out beats
    # re-parsing the SVG with a regex, which could only ever check whether the
    # emitter and the parser still agreed about attribute order.
    side = os.path.join(dest.mapdir, '.placement.json')
    json.dump({n: {'W': m.meta[n]['W'], 'H': m.meta[n]['H'],
                   'labels': [{k: b[k] for k in ('label', 'x0', 'x1', 'y0', 'y1', 'lead')}
                              for b in bs],
                   'dots': [[s['x'], s['y'], s['rr'], s['label']] for s in m._specs[n]]}
               for n, bs in m.placed.items()},
              open(side, 'w'), indent=0, sort_keys=True)

    fatal = 0
    if m.unsourced:
        print('\n!! %d marker(s) have no places.json entry:' % len(m.unsourced))
        for u in sorted(set(m.unsourced)):
            print('    %s' % u)
        print('   Every marker must resolve to a verified coordinate. Either add it:')
        print('     python3 tools/resolve.py --dest %s --seed && '
              'python3 tools/resolve.py --dest %s --write' % (dest.slug, dest.slug))
        print('   or pass allow_unsourced=True at the call site to draw it schematically.')
        fatal += len(m.unsourced)
    if m.outside:
        print('\n!! %d marker(s) fall outside the bounding box of the map they are drawn on:'
              % len(m.outside))
        for name, key, lat, lon in m.outside:
            c = m.cfg[name]
            print('    %-28s %.5f,%.5f  is not inside %s lat %s lon %s'
                  % (key[:28], lat, lon, name, c['lat'], c['lon']))
        print('   That is a wrong coordinate, not a wrong bounding box, nine times in ten.')
        fatal += len(m.outside)
    if m.crowded:
        print('\n!! %d label(s) could not be placed without a collision:' % len(m.crowded))
        for name, label in m.crowded:
            print('    %-12s %s' % (name, label))
        print('   Widen the map in maps.json, raise dispw, or cut a marker.')
        fatal += len(m.crowded)
    if m.schematic:
        print('\n(schematic, no fetched geometry: %s)' % ', '.join(sorted(set(m.schematic))))
    if fatal:
        sys.exit('\n%d problem(s) - fragments were written, but do not publish them.' % fatal)


if __name__ == '__main__':
    main()
