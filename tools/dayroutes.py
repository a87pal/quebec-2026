#!/usr/bin/env python3
"""Turn each day's ordered stops into Google Maps directions links.

Every place in this trip already carries a Place ID that tools/placeid.py
verified against a coordinate we resolved ourselves. Until now those IDs only
powered per-marker `maps/search` links - one place at a time - while the
guide's ten "Open this route in Google Maps" buttons were hand-typed paths of
free-text place names, one per *map*:

    /maps/dir/Porte+Saint-Louis,+Quebec+City/Citadelle+of+Quebec/...

Google re-runs a search on each of those names at click time, which is exactly
the ambiguity the Place IDs exist to remove, and a map is not a day. This
builds the other thing instead: one link per day, in the order you actually
travel, naming every stop exactly.

    https://www.google.com/maps/dir/?api=1
      &origin=<lat,lon>&origin_place_id=<ID>
      &destination=<lat,lon>&destination_place_id=<ID>
      &waypoints=<lat,lon>|<lat,lon>
      &waypoint_place_ids=<ID>|<ID>
      &travelmode=walking

The coordinate stays as the visible value with the ID beside it, the same way
savedlist.py builds a search link: Google falls back to the coordinate when an
ID will not resolve, so a stale ID degrades to the right spot rather than to a
confident wrong guess.

**Why a day is often more than one link.** Google's own limit: "up to three
waypoints supported on mobile browsers, and a maximum of nine waypoints
supported otherwise." This guide is read in a car. So a segment is cut into
links of at most MAX_STOPS stops, consecutive links overlapping by one so the
chain is continuous, and the whole-day link is emitted only when it genuinely
fits - never by quietly dropping the stops past the cap.

This is a Maps URL, not the Directions API: it opens Google's own map and
nothing it returns is drawn on ours, so the Maps Platform clauses that rule out
the Directions API here (see tools/README.md, "Why not Google") do not reach
it. No network, no key; the IDs are already committed.

Emits maps/dayroutes.html, a fragment. tools/maps.py splices each day's block
into its day card - this script never writes guide.html.

Usage:  python3 tools/dayroutes.py [--dest SLUG]
"""
import html
import io
import os
import sys
import urllib.parse

import _dest
import inventory

# Origin + 3 waypoints + destination. Three is Google's mobile-browser cap and
# this guide is used on a phone; nine would work on a laptop and silently lose
# stops in the car, which is the worse failure.
MAX_WAYPOINTS = 3
MAX_STOPS = MAX_WAYPOINTS + 2
# The desktop cap, used only to decide whether a whole-day link can exist.
MAX_WAYPOINTS_DESKTOP = 9

BASE = 'https://www.google.com/maps/dir/?api=1'

MODE_WORD = {'driving': 'Drive', 'walking': 'Walk', 'transit': 'By transit',
             'bicycling': 'Cycle', 'two-wheeler': 'Ride'}


def esc(s):
    return html.escape(str(s), quote=True)


def value(rec, name):
    """What Google is shown for a stop.

    A verified coordinate where we have one - it is the best possible fallback
    for an ID that will not resolve - and the text the place was found by where
    we do not, which is every extra that extracoords.py could not place.
    """
    if rec.get('lat') is not None and rec.get('lon') is not None:
        return '%.5f,%.5f' % (rec['lat'], rec['lon'])
    return rec.get('query') or name


def chunk(stops):
    """Cut a run of stops into legal links, overlapping by one.

    The overlap is what keeps the chain continuous: link 2 starts where link 1
    ended, so following them in order walks the whole segment. A trailing
    single stop is folded back into the previous link rather than emitted as a
    direction from a place to itself.
    """
    if len(stops) <= MAX_STOPS:
        return [stops]
    out, i = [], 0
    while i < len(stops) - 1:
        out.append(stops[i:i + MAX_STOPS])
        i += MAX_STOPS - 1
    if len(out) > 1 and len(out[-1]) < 2:
        out[-2] = out[-2] + out[-1]
        out.pop()
    return out


def url(inv, stops, mode):
    """One directions URL, or None if the stops cannot make a legal one."""
    if len(stops) < 2:
        return None
    recs = [(s, inv.record(s)) for s in stops]
    o, d = recs[0], recs[-1]
    mid = recs[1:-1]
    q = [('origin', value(o[1], o[0]))]
    if o[1].get('place_id'):
        q.append(('origin_place_id', o[1]['place_id']))
    q.append(('destination', value(d[1], d[0])))
    if d[1].get('place_id'):
        q.append(('destination_place_id', d[1]['place_id']))
    if mid:
        q.append(('waypoints', '|'.join(value(r, n) for n, r in mid)))
        # Google matches waypoint place IDs to waypoints by position, so a
        # partial list would silently attach the wrong ID to the wrong stop.
        # All or none.
        ids = [r.get('place_id') for _, r in mid]
        if all(ids):
            q.append(('waypoint_place_ids', '|'.join(ids)))
    q.append(('travelmode', mode))
    return BASE + '&' + urllib.parse.urlencode(q, safe='|,')


def legs_line(dest, inv, day):
    """The measured distance and time for the day's declared legs.

    Read from routes.json, which is real fetched road geometry, rather than
    re-derived here - the leg table in the guide already prints these numbers
    and two sources would eventually disagree.
    """
    ids = (inv.days.get(day) or {}).get('legs') or []
    routes = dest.load('routes.json', default={})
    have = [routes[i] for i in ids if i in routes]
    if not have:
        return ''
    m = sum(r['distance_m'] for r in have)
    s = sum(r['duration_s'] for r in have)
    mi, km = m / 1609.344, m / 1000.0
    h, mn = int(s // 3600), int(round((s % 3600) / 60.0))
    if mn == 60:
        h, mn = h + 1, 0
    t = ('%d h %02d' % (h, mn)) if h else ('%d min' % mn)
    return '%d mi / %d km · %s at the wheel, measured' % (round(mi), round(km), t)


CSS = """
.dayroutes{margin:16px 24px;background:#f3f1f6;border:1px solid #d8d4e2;border-radius:12px;
  padding:13px 17px;font-size:.9rem}
.dayroutes h6{margin:0 0 9px;font-size:.8rem;letter-spacing:.12em;text-transform:uppercase;
  color:#4e4877;font-weight:800}
.dayroutes .drl{display:flex;flex-wrap:wrap;gap:8px;margin:0}
.dayroutes .drbtn{display:inline-flex;flex-direction:column;gap:2px;padding:8px 14px;
  border:1px solid #cdc6dd;border-radius:14px;background:#fff;text-decoration:none;
  color:var(--forest);max-width:100%}
.dayroutes .drbtn:hover{background:#faf9fd;border-color:#b3a9cc}
.dayroutes .drbtn b{font:800 .8rem Inter,system-ui,sans-serif}
.dayroutes .drbtn span{font-size:.74rem;color:var(--muted);overflow-wrap:anywhere}
.dayroutes .drfoot{margin:9px 0 0;font-size:.76rem;color:var(--muted)}
@media print{.dayroutes .drbtn{border-color:#ccc}.dayroutes{background:none}}
"""


def day_links(inv, day):
    """[(mode word, name, stops, url)] for one day, chunked to the mobile cap.

    Shared with overlay.py, which puts the same links in the footer of every
    map that day is drawn on - one implementation, so the map and the day card
    cannot offer two different routes for the same day.
    """
    links = []
    for label, mode, stops in inv.segments(day):
        parts = chunk(stops)
        for i, part in enumerate(parts):
            u = url(inv, part, mode)
            if not u:
                continue
            name = label or ('%s \u2192 %s' % (inv.label(part[0]), inv.label(part[-1])))
            if len(parts) > 1:
                name = '%s \u00b7 %d of %d' % (name, i + 1, len(parts))
            links.append((MODE_WORD.get(mode, 'Go'), name, part, u))
    return links


def whole_day(inv, day):
    """(mode word, stop count, url) for the day in one link, or None.

    Emitted only when it is legal on a laptop and the day keeps one travel mode
    throughout. A link that silently drops every stop past the ninth waypoint
    would look complete and be wrong, which is the failure worth avoiding.
    """
    segs = inv.segments(day)
    if not segs or len({m for _, m, _ in segs}) != 1:
        return None
    flat = []
    for _, _, stops in segs:
        for s in stops:
            if not flat or flat[-1] != s:
                flat.append(s)
    if not (2 <= len(flat) <= MAX_WAYPOINTS_DESKTOP + 2):
        return None
    u = url(inv, flat, segs[0][1])
    return (MODE_WORD.get(segs[0][1], 'Go'), len(flat), u) if u else None


def build(dest):
    inv = inventory.load(dest)
    probs = inventory.problems(dest, inv)
    if probs:
        print('!! inventory.json has %d problem(s); run tools/inventory.py' % len(probs))
        for p in probs:
            print('    %s' % p)
        sys.exit(1)

    out, nlinks, ndays = [], 0, 0
    for day in inv.routed_days():
        segs = inv.segments(day)
        links = day_links(inv, day)
        whole = whole_day(inv, day)
        if not links:
            continue
        ndays += 1
        nlinks += len(links)
        o = ['<div class="dayroutes" data-day="%d">' % day,
             '<h6>Navigate this day</h6>',
             '<div class="drl">']
        for word, name, part, u in links:
            o.append('<a class="drbtn" href="%s" target="_blank" rel="noopener">'
                     '<b>%s · %s</b><span>%s</span></a>'
                     % (esc(u), esc(word), esc(name),
                        esc(' → '.join(inv.label(s) for s in part))))
        if whole:
            word, count, u = whole
            o.append('<a class="drbtn" href="%s" target="_blank" rel="noopener">'
                     '<b>%s · the whole day</b><span>%d stops in one route — '
                     'a laptop shows all of them, a phone browser only the '
                     'first three waypoints</span></a>' % (esc(u), esc(word), count))
        o.append('</div>')
        foot = legs_line(dest, inv, day)
        note = ('Split into %d links because Google carries at most three waypoints '
                'on a phone; each one picks up where the last left off.' % len(links)
                if len(links) > 1 else '')
        if foot or note:
            o.append('<p class="drfoot">%s</p>'
                     % esc(' · '.join(x for x in (foot, note) if x)))
        o.append('</div>')
        out.append('\n'.join(o))

    path = os.path.join(dest.mapdir, 'dayroutes.html')
    io.open(path, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    print('%d day(s), %d directions link(s) -> %s' % (ndays, nlinks, path))
    return path


def main():
    dest, _ = _dest.from_args('Build per-day Google Maps directions links.')
    build(dest)


if __name__ == '__main__':
    main()
