#!/usr/bin/env python3
"""Measure how wide map labels actually render, and bake the table into metrics.json.

boxes.py used to estimate a label's width as len(text) * font_size * 0.56 - a
raw character count. That is wrong in both directions and worst on exactly the
labels these guides are full of: "Sainte-Anne-de-Beaupre" is mostly narrow
letters, "MONTREAL" is all caps, and the middle dot in "C$4.25 - sunset" is
nothing like an average character. Placement decisions made on those numbers
are guesses.

This reads real advance widths out of a font file - the sfnt hmtx table, in
about eighty lines of stdlib - and writes tools/metrics.json, which is
committed so overlay.py, boxes.py and CI need nothing but python3.

  python3 tools/metrics.py --measure          rebuild metrics.json
  python3 tools/metrics.py                    show what is cached

Why a font file and not the browser: measuring through headless Chrome sounds
more authoritative and is not. The published guide ships no @font-face, so
labels render in Inter where the reader has it and system-ui otherwise - SF
Pro, Segoe UI or Roboto depending on the machine - and there is no single right
answer to measure. A static bold sans-serif is a good proxy for all of them,
parsing it is deterministic on any machine, and _metrics.py adds a safety
margin on top. The point is to stop labels colliding, not to predict a pixel.

Arial Bold is preferred because it is slightly wider than Inter, so the error
runs towards spreading labels apart rather than letting them touch.

Usage:  python3 tools/metrics.py [--measure] [--dest SLUG]
"""
import argparse, io, json, os, struct, sys, time

import _dest, _metrics

# (regular, bold) pairs, best first. Weight 800 uses bold; weight 600 sits
# between the two and is interpolated.
FONTS = [
    ('/Library/Fonts/Inter-Regular.ttf', '/Library/Fonts/Inter-ExtraBold.ttf'),
    (os.path.expanduser('~/Library/Fonts/Inter-Regular.ttf'),
     os.path.expanduser('~/Library/Fonts/Inter-ExtraBold.ttf')),
    ('/System/Library/Fonts/Supplemental/Arial.ttf',
     '/System/Library/Fonts/Supplemental/Arial Bold.ttf'),
    ('/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
     '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'),
    ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
     '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'),
]

WEIGHTS = (800, 600)


# ------------------------------------------------------------------ sfnt
class Font(object):
    """Just enough of a TrueType file to ask how wide a character is."""

    def __init__(self, path):
        self.path = path
        self.data = io.open(path, 'rb').read()
        d = self.data
        if d[:4] == b'ttcf':                       # collection: take the first face
            off = struct.unpack('>I', d[12:16])[0]
        else:
            off = 0
        n = struct.unpack('>H', d[off + 4:off + 6])[0]
        self.tables = {}
        for i in range(n):
            p = off + 12 + i * 16
            tag = d[p:p + 4].decode('latin-1')
            to, tl = struct.unpack('>II', d[p + 8:p + 16])
            self.tables[tag] = (to, tl)
        for need in ('head', 'hhea', 'hmtx', 'cmap'):
            if need not in self.tables:
                raise ValueError('%s has no %s table' % (path, need))

        ho = self.tables['head'][0]
        self.upem = float(struct.unpack('>H', d[ho + 18:ho + 20])[0])
        ao = self.tables['hhea'][0]
        self.n_hmetrics = struct.unpack('>H', d[ao + 34:ao + 36])[0]
        self.cmap = self._cmap()

    def _cmap(self):
        """Character -> glyph id, from a format 4 subtable."""
        d = self.data
        co = self.tables['cmap'][0]
        n = struct.unpack('>H', d[co + 2:co + 4])[0]
        best = None
        for i in range(n):
            pid, eid, off = struct.unpack('>HHI', d[co + 4 + i * 8:co + 12 + i * 8])
            rank = {(3, 1): 0, (0, 3): 1, (0, 4): 1, (3, 0): 2, (0, 0): 3, (1, 0): 4}.get((pid, eid), 9)
            if best is None or rank < best[0]:
                best = (rank, co + off)
        sub = best[1]
        fmt = struct.unpack('>H', d[sub:sub + 2])[0]
        out = {}
        if fmt != 4:
            raise ValueError('%s: cmap format %d not supported' % (self.path, fmt))
        segx2 = struct.unpack('>H', d[sub + 6:sub + 8])[0]
        seg = segx2 // 2
        ends = struct.unpack('>%dH' % seg, d[sub + 14:sub + 14 + segx2])
        so = sub + 16 + segx2
        starts = struct.unpack('>%dH' % seg, d[so:so + segx2])
        do = so + segx2
        deltas = struct.unpack('>%dh' % seg, d[do:do + segx2])
        ro = do + segx2
        ranges = struct.unpack('>%dH' % seg, d[ro:ro + segx2])
        for i in range(seg):
            for c in range(starts[i], min(ends[i], 0xFFFF) + 1):
                if ranges[i] == 0:
                    g = (c + deltas[i]) & 0xFFFF
                else:
                    gp = ro + i * 2 + ranges[i] + (c - starts[i]) * 2
                    if gp + 2 > len(d):
                        continue
                    g = struct.unpack('>H', d[gp:gp + 2])[0]
                    if g:
                        g = (g + deltas[i]) & 0xFFFF
                if g:
                    out[c] = g
        return out

    def advance(self, ch):
        """Advance width of one character, in em."""
        g = self.cmap.get(ord(ch))
        if g is None:
            return None
        d = self.data
        ho = self.tables['hmtx'][0]
        i = min(g, self.n_hmetrics - 1)
        return struct.unpack('>H', d[ho + i * 4:ho + i * 4 + 2])[0] / self.upem


def pick():
    for reg, bold in FONTS:
        if os.path.exists(reg) and os.path.exists(bold):
            return Font(reg), Font(bold)
    sys.exit('error: no usable font found. metrics.json is committed, so this is\n'
             'only needed when remeasuring; the checked-in table stays valid.\n'
             'Tried:\n  ' + '\n  '.join(b for _, b in FONTS))


# ------------------------------------------------------------------ labels
def labels(dest):
    """Every label and sublabel this destination actually draws."""
    import overlay
    m = overlay.Maps(dest)
    m.collect_only = True
    overlay.load_markers(dest).build(m)
    out = set()
    for spec in m.all_specs():
        if spec.get('label'):
            out.add((800, spec['label']))
        if spec.get('sub'):
            out.add((600, spec['sub']))
    return out


def main():
    ap = argparse.ArgumentParser(description='Measure label text metrics from a font file.')
    _dest.add_arg(ap)
    ap.add_argument('--measure', action='store_true', help='rebuild metrics.json')
    a = ap.parse_args()

    if not a.measure:
        d = _metrics.load()
        print('%s' % _metrics.PATH)
        print('  font       : %s' % d.get('font', '?'))
        print('  characters : %d' % len(d.get('chars', {})))
        print('  strings    : %d' % len(d.get('strings', {})))
        print('  measured   : %s' % d.get('measured', 'never'))
        print('\npass --measure to rebuild (result is committed).')
        return 0

    reg, bold = pick()
    print('regular: %s\nbold   : %s' % (reg.path, bold.path))

    chars = set(chr(c) for c in range(32, 127))
    strings = set()
    for dest in (_dest.Dest(s) for s in _dest.slugs()):
        if not os.path.exists(os.path.join(dest.mapdir, 'markers.py')):
            continue
        for weight, text in labels(dest):
            strings.add((weight, text))
            chars.update(text)

    def adv(ch, weight):
        b, r = bold.advance(ch), reg.advance(ch)
        if b is None and r is None:
            return None
        if b is None:
            b = r
        if r is None:
            r = b
        # 800 is the bold face; 600 sits between the two.
        return b if weight >= 800 else r + (b - r) * 0.5

    out = {'font': os.path.basename(bold.path), 'measured': time.strftime('%Y-%m-%d'),
           'stack': 'Inter, system-ui, sans-serif', 'chars': {}, 'strings': {}, 'space': {}}
    missing = set()
    for c in sorted(chars):
        for w in WEIGHTS:
            v = adv(c, w)
            if v is None:
                missing.add(c)
                continue
            if c == ' ':
                out['space'][str(w)] = round(v, 5)
            else:
                out['chars']['%d|%s' % (w, c)] = round(v, 5)

    # Real labels get an exact entry: a per-character sum is all this font file
    # can give (no kerning), but storing the label directly means a later
    # change to the summing rule cannot silently move existing maps.
    for w, t in sorted(strings):
        total = 0.0
        for ch in t:
            v = adv(ch, w)
            total += v if v is not None else adv('M', w)
        out['strings']['%d|%s' % (w, t)] = round(total, 5)

    json.dump(out, io.open(_metrics.PATH, 'w'), indent=0, ensure_ascii=False, sort_keys=True)
    print('wrote %d characters and %d strings -> %s'
          % (len(out['chars']), len(out['strings']), _metrics.PATH))
    if missing:
        print('!! %d character(s) not in the font, estimated as "M": %s'
              % (len(missing), ' '.join(sorted(missing))))

    worst = []
    for k, real in out['strings'].items():
        w, t = k.split('|', 1)
        worst.append((abs(len(t) * 0.56 - real) / max(real, 1e-6), t, len(t) * 0.56, real))
    worst.sort(reverse=True)
    print('\nworst errors in the old len*0.56 model:')
    for err, t, old, real in worst[:8]:
        print('  %5.1f%%  %-34s estimated %5.2f em, actually %5.2f em'
              % (err * 100, t[:34], old, real))
    return 0


if __name__ == '__main__':
    sys.exit(main())
