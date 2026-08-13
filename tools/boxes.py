# -*- coding: utf-8 -*-
"""Check that no two map labels overlap and no label covers another marker's dot.

overlay.py places labels by trying candidate positions and rejecting the ones
that collide, so in principle this can never fail. That is exactly why it is
worth running: it checks the placer's work against the placer's own output, and
a bug in the candidate search shows up here rather than on a printed map.

It reads maps/.placement.json, written by overlay.py, rather than parsing the
generated SVG. The previous version recovered every box with one long regex
over the emitted markup, which meant it was really testing whether the emitter
and the regex still agreed about attribute order - reorder an attribute in
marker() and it silently matched zero markers and reported all clear. The
marker count is still cross-checked against the fragment, so the two halves
cannot drift apart unnoticed.

Both counts must be zero before publishing. Exits non-zero if anything
collides, so CI can gate on it.

Usage:  python3 tools/boxes.py [--dest SLUG]
"""
import io, json, os, re, sys

import _dest

SLACK = 4.0     # composite px of overlap tolerated, matching overlay.PAD/SLACK
GROUP = re.compile(r'<g class="mk ')


def overlap(a, b):
    dx = min(a['x1'], b['x1']) - max(a['x0'], b['x0'])
    dy = min(a['y1'], b['y1']) - max(a['y0'], b['y0'])
    return (dx, dy) if (dx > 0 and dy > 0) else (0, 0)


def covers_dot(b, cx, cy, r):
    """True if the label box reaches the dot's circle, not just its centre."""
    nx = min(max(cx, b['x0']), b['x1'])
    ny = min(max(cy, b['y0']), b['y1'])
    return (cx - nx) ** 2 + (cy - ny) ** 2 < r * r


def main():
    dest, _ = _dest.from_args('Check map label placement for collisions.')
    side = os.path.join(dest.mapdir, '.placement.json')
    if not os.path.exists(side):
        sys.exit('error: %s missing - run tools/overlay.py first' % side)
    placement = json.load(io.open(side, encoding='utf-8'))
    names = list(dest.load('maps.json').keys())

    problems = 0
    for n in names:
        p = dest.fragment(n)
        if not os.path.exists(p):
            print('== %-11s MISSING - run overlay.py' % n)
            problems += 1
            continue
        if n not in placement:
            print('== %-11s no placement data - run overlay.py' % n)
            problems += 1
            continue
        pl = placement[n]
        bs, dots = pl['labels'], pl['dots']

        # The fragment and the placement data must describe the same map.
        drawn = len(GROUP.findall(io.open(p, encoding='utf-8').read()))
        if drawn != len(bs):
            print('== %-11s MISMATCH: %d markers in the fragment, %d placed'
                  % (n, drawn, len(bs)))
            problems += 1
            continue

        bad = []
        for i in range(len(bs)):
            for j in range(i + 1, len(bs)):
                dx, dy = overlap(bs[i], bs[j])
                if dx > SLACK and dy > SLACK:
                    bad.append((bs[i]['label'], bs[j]['label'], round(dx), round(dy)))
        hit = []
        for b in bs:
            for cx, cy, r, label in dots:
                if label == b['label']:
                    continue
                if covers_dot(b, cx, cy, r):
                    hit.append((b['label'], 'covers dot of', label))
        out = []
        for b in bs:
            if (b['x0'] < 0 or b['y0'] < 0 or b['x1'] > pl['W'] or b['y1'] > pl['H']):
                out.append(b['label'])

        leads = sum(1 for b in bs if b['lead'])
        print('== %-11s markers=%d  label-overlaps=%d  dot-covers=%d  off-map=%d  leaders=%d'
              % (n, len(bs), len(bad), len(hit), len(out), leads))
        for x in bad:
            print('     OVERLAP %-26s x %-26s (%dx%d px)' % x)
        for x in hit:
            print('     DOTHIT  %-26s %s %s' % x)
        for x in out:
            print('     OFFMAP  %s' % x)
        problems += len(bad) + len(hit) + len(out)

    if problems:
        sys.exit('\n%d label placement problem(s). overlay.py places labels '
                 'automatically, so this is a bug in the placer, not something to '
                 'fix by hand in markers.py.' % problems)
    print('\nall clear: 0 overlaps, 0 dot-covers, 0 off-map')


if __name__ == '__main__':
    main()
