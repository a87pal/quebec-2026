# -*- coding: utf-8 -*-
"""How wide a map label renders, in em units.

Backed by tools/metrics.json, measured from headless Chrome by tools/metrics.py
and committed so nothing downstream needs a browser.

Three tiers, best first:

  1. the exact measured advance for a label we have seen before, which includes
     kerning and so beats any per-character sum;
  2. the sum of measured per-character advances, for a label added since the
     last measurement;
  3. a flat estimate, if metrics.json is missing entirely.

Widths get a safety margin because the guide ships no @font-face. Labels are
Inter where the reader has it and system-ui otherwise - SF Pro, Segoe UI or
Roboto depending on the machine - so the measured advance is representative,
not exact. The margin buys back that variation. Under-measuring puts two labels
on top of each other; over-measuring only spreads them slightly further apart.
"""
import io, json, os

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'metrics.json')

# Cross-platform slack on top of the measured font.
MARGIN = 1.06

# Only used when metrics.json is absent. This is the old len*0.56 model, kept
# as a floor so the toolchain still runs on a machine that never measured.
FALLBACK_CHAR = 0.56

_data = None


def load():
    global _data
    if _data is None:
        if os.path.exists(PATH):
            _data = json.load(io.open(PATH, encoding='utf-8'))
        else:
            _data = {'chars': {}, 'strings': {}, 'space': {}}
    return _data


def em(text, weight=800):
    """Advance width of `text` in em, before the safety margin."""
    d = load()
    key = '%d|%s' % (weight, text)
    hit = d['strings'].get(key)
    if hit is not None:
        return hit
    chars, space = d['chars'], d['space'].get(str(weight))
    if not chars:
        return len(text) * FALLBACK_CHAR
    # Nearest measured weight, so a new weight still gets real numbers.
    total = 0.0
    for ch in text:
        if ch == ' ':
            total += space if space is not None else 0.26
            continue
        w = chars.get('%d|%s' % (weight, ch))
        if w is None:                       # unmeasured glyph: assume a wide one
            w = max(chars.get('%d|M' % weight, FALLBACK_CHAR), FALLBACK_CHAR)
        total += w
    return total


def width(text, font_size, weight=800):
    """Rendered width in the same pixel units as font_size, with margin."""
    if not text:
        return 0.0
    return em(text, weight) * font_size * MARGIN
