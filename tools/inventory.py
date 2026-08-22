#!/usr/bin/env python3
"""The day and category layer over places.json + extras.json.

places.json says *where* a place is and extras.json says where the ones that
are not map markers are. Neither says *when* you go or *what kind of thing it
is*, and without those two facts the 165-place driving list cannot be grouped,
sequenced, filtered, or turned into a route. maps/inventory.json adds them.

It is a third file rather than two new columns because resolve.py, placeid.py
and extracoords.py machine-write the other two - CLAUDE.md forbids hand-editing
them, and a hand-set `day` living next to a generated `lat` is one --seed away
from being clobbered. Here, every field is hand-set and nothing generated is
written back.

    {
      "days": {
        "6": { "mode": "walking",
               "route": ["Porte Saint-Louis", "La Citadelle", "Plains of Abraham"] }
      },
      "places": {
        "Chateau Frontenac": { "day": [6], "cat": "sight" }
      }
    }

`places` tags a place for filtering and grouping. `days[n].route` is the
separate, ordered question of which of those stops the day's Google Maps route
link actually strings together - most days name more places than you visit, and
prose order is not always walking order. A place can be tagged to a day without
being on its route; a route may not name a place that is not tagged to that day.

    python3 tools/inventory.py [--dest SLUG]           coverage report, gates
    python3 tools/inventory.py [--dest SLUG] --seed    propose from guide prose

--seed reads each <details class="day" id="day-N"> block in the guide, matches
inventory keys against its prose, and proposes an assignment - the same harvest
that built extras.json by hand in commit 10e6ccd. It never overwrites a value
that is already there, so re-seeding after adding a marker is safe. It writes
the file; you review the diff. Everything here is offline.

Usage:  python3 tools/inventory.py [--dest SLUG] [--seed] [--write]
"""
import html as H
import io
import math
import json
import os
import re
import sys
import unicodedata

import _dest

# The closed vocabulary. A category not in this list is an error, not a new
# category - the filters, the legend and the saved-list grouping all read it,
# and a typo would silently create a chip nothing can select.
CATS = ('base', 'town', 'sight', 'view', 'hike', 'food', 'drink',
        'market', 'shop', 'transit', 'tour', 'admin')

# Twelve categories is the right resolution for a saved list and far too many
# chips for a map. The map filters on these four groups instead; the fine
# category still rides along for the legend and the list.
GROUP = {
    'base': 'stay', 'town': 'stay',
    'sight': 'do', 'view': 'do', 'hike': 'do', 'tour': 'do', 'shop': 'do',
    'food': 'eat', 'drink': 'eat', 'market': 'eat',
    'transit': 'move', 'admin': 'move',
}
GROUPS = ('stay', 'do', 'eat', 'move')
GROUP_LABEL = {'stay': 'Sleep', 'do': 'See & do', 'eat': 'Eat & drink', 'move': 'Getting about'}

MODES = ('driving', 'walking', 'bicycling', 'two-wheeler', 'transit')

# How far one hop inside a segment may plausibly be, in km, by travel mode.
# This is the gate that catches a stop keyed to the wrong city: "Place d'Armes"
# exists in both Montreal and Quebec, and one wrong key put a 240 km transit
# hop in the middle of an afternoon on foot in Old Montreal. Generous on
# purpose - it is looking for an impossibility, not judging an itinerary.
MAX_HOP_KM = {'walking': 8, 'bicycling': 40, 'transit': 60,
              'driving': 800, 'two-wheeler': 800}  # day 11 is Charlevoix to Connecticut


def haversine_km(a, b):
    la1, lo1, la2, lo2 = [math.radians(x) for x in (a[0], a[1], b[0], b[1])]
    h = (math.sin((la2 - la1) / 2) ** 2
         + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2)
    return 2 * 6371.0088 * math.asin(min(1.0, math.sqrt(h)))

DAY_OPEN = re.compile(r'<details class="day[^"]*" id="day-(\d+)">')


# --------------------------------------------------------------------- text

def norm(s):
    """Fold a name to something two spellings of it both land on.

    The guide is typeset prose and the keys are data: one has curly quotes and
    en dashes, the other has whatever was typed. Without this, "Schwartz's"
    matches nothing.
    """
    s = unicodedata.normalize('NFC', str(s))
    for a, b in ((' ', ' '), ('’', "'"), ('‘', "'"),
                 ('–', '-'), ('—', '-'), ('“', '"'), ('”', '"')):
        s = s.replace(a, b)
    return re.sub(r'\s+', ' ', s).strip().lower()


def plaintext(h):
    """Guide HTML down to searchable prose.

    <svg> goes first and for a real reason: every map marker's label is SVG
    <text> inside the guide, so leaving it in makes every marker match the day
    its map happens to sit above, whether or not the prose ever mentions it.
    """
    h = re.sub(r'<svg\b.*?</svg>', ' ', h, flags=re.S)
    h = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', h, flags=re.S)
    return norm(H.unescape(re.sub(r'<[^>]+>', ' ', h)))


def day_blocks(guide_html):
    """{day number: raw HTML of its <details>}, matched by depth.

    The day cards contain nested <details> - every level-2 stop is one - so the
    first </details> is the wrong one.
    """
    out = {}
    for m in DAY_OPEN.finditer(guide_html):
        i, d = m.end(), 1
        while d:
            o = guide_html.find('<details', i)
            c = guide_html.find('</details>', i)
            if c < 0:
                sys.exit('error: day-%s is not closed' % m.group(1))
            if o != -1 and o < c:
                d += 1
                i = o + 8
            else:
                d -= 1
                i = c + 10
        out[int(m.group(1))] = guide_html[m.start():i]
    return out


# ---------------------------------------------------------------- the model

class Inventory(object):
    """The joined view: one record per place, with where, when and what kind.

    Every consumer - overlay.py's filters, dayroutes.py's links, savedlist.py's
    grouping - reads this rather than joining the three files itself, so they
    cannot disagree about which day a place belongs to.
    """

    def __init__(self, dest):
        self.dest = dest
        self.places = dest.load('places.json', default={})
        self.extras = dest.load('extras.json', default={})
        self.order = list(dest.load('maps.json', default={}).keys())
        raw = dest.load('inventory.json', default={})
        self.days = {int(k): v for k, v in (raw.get('days') or {}).items()}
        self.tags = raw.get('places') or {}

    # -- lookups ----------------------------------------------------------
    def keys(self):
        """Every place that exists, markers first, in a stable order."""
        return list(self.places) + [k for k in self.extras if k not in self.places]

    def record(self, key):
        """The coordinate/Place ID record, from whichever file holds it."""
        return self.places.get(key) or self.extras.get(key) or {}

    def days_of(self, key):
        d = (self.tags.get(key) or {}).get('day')
        if d is None:
            return []
        return [d] if isinstance(d, int) else sorted(set(d))

    def cat(self, key):
        return (self.tags.get(key) or {}).get('cat') or ''

    def label(self, key):
        """What to call this place in prose.

        The key is a join key and sometimes reads like one - "YOUR BASE - The
        Main" is shouted because it is a map label. `as` gives a sentence-cased
        name for the places where the two jobs pull apart; everything else is
        already fine as it stands.
        """
        return (self.tags.get(key) or {}).get('as') or key

    def group(self, key):
        return GROUP.get(self.cat(key), '')

    def hub(self, key):
        """Which map's ground this place sits on.

        An explicit `hub` wins; otherwise a marker uses its own region and an
        extra borrows the region of the place it sits near - the same fallback
        savedlist.rows() has always used, kept in one place so the list and the
        maps cannot group the same place differently.
        """
        h = (self.tags.get(key) or {}).get('hub')
        if h:
            return h
        p = self.places.get(key)
        if p:
            return p.get('region') or ''
        e = self.extras.get(key) or {}
        return (self.places.get(e.get('near') or '') or {}).get('region') or ''

    # -- routes -----------------------------------------------------------
    def segments(self, day):
        """[(label, mode, [keys])] for one day, from either `route` shape.

        A flat list is the common case - one mode, one line of travel. The
        object form exists for the days that genuinely change mode partway,
        and both normalise to the same thing here so dayroutes.py has one shape
        to emit.
        """
        spec = self.days.get(day) or {}
        mode = spec.get('mode') or 'driving'
        route = spec.get('route') or []
        if route and isinstance(route[0], dict):
            return [(s.get('label') or '', s.get('mode') or mode, list(s.get('stops') or []))
                    for s in route]
        return [('', mode, list(route))] if route else []

    def routed_days(self):
        return sorted(d for d in self.days if self.segments(d))

    def day_of_leg(self, rid):
        """Which day drives a legs.json leg, or None.

        Read from days[*].legs rather than from a `day` field on the leg
        itself: the day already declares which legs it drives, and a second
        copy in legs.json is a second thing to keep in sync. overlay.py uses
        this to tag a drawn line so the day filter hides the road with the
        stops it connects.
        """
        for d in sorted(self.days):
            if rid in ((self.days.get(d) or {}).get('legs') or []):
                return d
        return None


def load(dest):
    return Inventory(dest)


# ----------------------------------------------------------------- seeding

# Rules are ordered and first-match-wins, so put the specific before the
# general: "Marche Jean-Talon" is a market before it is a "marche".
CAT_RULES = (
    ('base', r'your base|airbnb|the lodge|manoir richelieu|where you sleep'),
    ('transit', r'\bmetro\b|\bmétro\b|funicular|ascenseur|ferry|gare du|station|'
                r'parking|tramway|traversier|\bbus\b'),
    ('market', r'march[ée]|market|grocer|epicerie|épicerie|iga\b|price chopper|'
               r'metro plus|d[ée]penneur|laiterie|boulangerie'),
    ('tour', r'croisi[èe]res|cruise|whale|audio walk|guided|tour\b|excursion'),
    ('hike', r'trail|ridge|summit|mtn|mount |mt\.|acropole|sentier|gorges|'
             r'haystack|lafayette|bluff'),
    ('view', r'belv[ée]d[èe]re|lookout|viewpoint|panoram|chalet|terrasse|terrace'),
    ('drink', r'brewery|brasserie|microbrasserie|pub\b|\bbar\b|cidre|cider|'
              r'vignoble|winery|distiller'),
    ('food', r'caf[ée]|restaurant|bistro|snack|deli|ramen|falafel|patati|'
             r'bagel|creperie|crêperie|poutine|binerie|d[ée]jeuner|izakaya|'
             r'p[âa]tisserie|glacier|casse-cro[ûu]te'),
    ('shop', r'atelier|boutique|librairie|shop\b|galerie|gallery'),
    ('admin', r'border|douane|visitor cent|information|welcome cent|poste frontal'),
    ('town', r'^(cheshire|lincoln|montr[ée]al|qu[ée]bec city|baie-|la malbaie|'
             r'les [ée]boulements|saint-ir[ée]n[ée]e|tadoussac|trois-rivi[èe]res|'
             r'deschambault|derby line|st-beno[îi]t)'),
)


def guess_cat(key, rec):
    hay = norm(' '.join(str(rec.get(f) or '') for f in ('query', 'note', 'matched', 'source')))
    name = norm(key)
    for cat, pat in CAT_RULES:
        if re.search(pat, name) or re.search(pat, hay):
            return cat
    return 'sight'


def seed(dest, inv):
    """Propose day tags and categories from the guide's own prose.

    Three passes, weakest last:
      1. the key appears verbatim in a day's prose,
      2. an extra with no day of its own borrows its `near` anchor's days,
      3. whatever is left is listed for you to assign by hand.

    Nothing already set is overwritten - not the day, not the category, not a
    route. Re-seeding after adding one marker touches only that marker.
    """
    guide = io.open(dest.guide, encoding='utf-8').read()
    blocks = day_blocks(guide)
    if not blocks:
        sys.exit('error: no <details class="day" id="day-N"> sections in %s' % dest.guide)
    text = {n: plaintext(v) for n, v in blocks.items()}

    keys = inv.keys()
    found = {}
    for k in keys:
        n = norm(k)
        aliases = [n] + [norm(a) for a in ((inv.tags.get(k) or {}).get('alias') or [])]
        hits = sorted(d for d in text if any(a and a in text[d] for a in aliases))
        if hits:
            found[k] = hits

    inherited = 0
    for k in keys:
        if k in found or k in inv.places:
            continue
        anchor = (inv.extras.get(k) or {}).get('near')
        if anchor and found.get(anchor):
            found[k] = found[anchor]
            inherited += 1

    tags = dict(inv.tags)
    added_day = added_cat = 0
    for k in keys:
        cur = dict(tags.get(k) or {})
        if 'day' not in cur and found.get(k):
            cur['day'] = found[k]
            added_day += 1
        if 'cat' not in cur:
            cur['cat'] = guess_cat(k, inv.record(k))
            added_cat += 1
        if cur:
            tags[k] = cur

    days = {str(n): (inv.days.get(n) or {'mode': 'driving', 'route': []})
            for n in sorted(blocks)}
    for n, v in inv.days.items():
        days.setdefault(str(n), v)

    doc = {'days': {k: days[k] for k in sorted(days, key=int)},
           'places': {k: tags[k] for k in sorted(tags)}}
    path = os.path.join(dest.mapdir, 'inventory.json')
    with io.open(path, 'w', encoding='utf-8') as f:
        f.write(json.dumps(doc, ensure_ascii=False, indent=1) + '\n')

    missing = [k for k in keys if not (tags.get(k) or {}).get('day')]
    print('seeded %s' % path)
    print('  %d place(s) matched a day in the prose, %d inherited from a `near` anchor'
          % (len(found) - inherited, inherited))
    print('  %d day tag(s) and %d category guess(es) added; nothing existing was touched'
          % (added_day, added_cat))
    if missing:
        print('\n  %d place(s) need a day by hand - they are named nowhere in a day card:'
              % len(missing))
        for k in missing:
            print('      %s' % k)
    print('\n  Review the diff. Every category is a guess; the route arrays are empty '
          'until you fill them.')


# --------------------------------------------------------------- reporting

def problems(dest, inv):
    """Everything that would make a downstream tool wrong. Fatal, as a list."""
    out = []
    known = set(inv.keys())
    guide = io.open(dest.guide, encoding='utf-8').read() if os.path.exists(dest.guide) else ''
    real_days = set(day_blocks(guide)) if guide else set()

    for k, t in sorted(inv.tags.items()):
        if k not in known:
            out.append('inventory names "%s", which is in neither places.json nor extras.json' % k)
            continue
        c = t.get('cat')
        if c and c not in CATS:
            out.append('"%s" has category "%s"; the vocabulary is %s' % (k, c, ', '.join(CATS)))
        for d in inv.days_of(k):
            if real_days and d not in real_days:
                out.append('"%s" is tagged day %d, but the guide has no id="day-%d"' % (k, d, d))

    known_legs = set(dest.load('legs.json', default={}))
    for d in sorted(inv.days):
        if real_days and d not in real_days:
            out.append('inventory declares day %d, which the guide does not have' % d)
        for rid in (inv.days[d].get('legs') or []):
            if rid not in known_legs:
                out.append('day %d claims leg "%s", which legs.json does not declare' % (d, rid))
        for label, mode, stops in inv.segments(d):
            where = 'day %d%s' % (d, ' (%s)' % label if label else '')
            if mode not in MODES:
                out.append('%s has travelmode "%s"; Google accepts %s'
                           % (where, mode, ', '.join(MODES)))
            for s in stops:
                if s not in known:
                    out.append('%s routes through "%s", which is not a known place' % (where, s))
                elif d not in inv.days_of(s):
                    out.append('%s routes through "%s", which is not tagged to that day'
                               % (where, s))
            if len(stops) == 1:
                out.append('%s has a one-stop route, which cannot be a direction' % where)
            cap = MAX_HOP_KM.get(mode)
            for a, b in zip(stops, stops[1:]):
                ra, rb = inv.record(a), inv.record(b)
                if not cap or None in (ra.get('lat'), rb.get('lat')):
                    continue
                km = haversine_km((ra['lat'], ra['lon']), (rb['lat'], rb['lon']))
                if km > cap:
                    out.append('%s goes "%s" -> "%s", %d km apart by %s - one of those '
                               'keys is almost certainly the wrong place'
                               % (where, a, b, round(km), mode))
    return out


def report(dest, inv, brief=False):
    """Coverage, and the problems that make it fatal.

    `brief` is what check.sh runs: one line and then whatever is wrong, because
    a passing gate should be quiet and a failing one should say why. The full
    report is for authoring.
    """
    keys = inv.keys()
    tagged = [k for k in keys if inv.days_of(k)]
    catted = [k for k in keys if inv.cat(k)]
    if brief:
        probs = problems(dest, inv)
        print('inventory: %d place(s), %d with a day, %d with a category, %d route day(s)%s'
              % (len(keys), len(tagged), len(catted), len(inv.routed_days()),
                 '' if not probs else ' - %d PROBLEM(S)' % len(probs)))
        for p in probs:
            print('    %s' % p)
        if probs:
            sys.exit(1)
        return
    print('=== inventory: %s ===' % dest.slug)
    print('   %d place(s): %d marker(s), %d extra(s)'
          % (len(keys), len(inv.places), len(keys) - len(inv.places)))
    print('   %d with a day, %d with a category' % (len(tagged), len(catted)))

    if len(tagged) < len(keys):
        print('\n   no day yet (%d):' % (len(keys) - len(tagged)))
        for k in keys:
            if not inv.days_of(k):
                print('      %s' % k)

    print('\n   by day:')
    for d in sorted(set(inv.days) | {x for k in keys for x in inv.days_of(k)}):
        on = [k for k in keys if d in inv.days_of(k)]
        segs = inv.segments(d)
        stops = sum(len(s[2]) for s in segs)
        print('      day %-3d %3d tagged  %s'
              % (d, len(on),
                 ('route: %d stop(s) in %d segment(s)' % (stops, len(segs))) if segs
                 else 'no route'))

    print('\n   by category:')
    for c in CATS:
        n = sum(1 for k in keys if inv.cat(k) == c)
        if n:
            print('      %-8s %-6s %3d' % (c, GROUP[c], n))

    probs = problems(dest, inv)
    if probs:
        print('\n!! %d problem(s):' % len(probs))
        for p in probs:
            print('    %s' % p)
        sys.exit(1)
    print('\nOK')


def main():
    def extra(ap):
        ap.add_argument('--seed', action='store_true',
                        help='propose day tags and categories from the guide prose')
        ap.add_argument('--brief', action='store_true',
                        help='one summary line plus any problems, for check.sh')
    dest, a = _dest.from_args('Day and category layer over places.json + extras.json.', extra)
    inv = Inventory(dest)
    if a.seed:
        seed(dest, inv)
        return
    report(dest, inv, brief=a.brief)


if __name__ == '__main__':
    main()
