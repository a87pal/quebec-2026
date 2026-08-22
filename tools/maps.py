#!/usr/bin/env python3
"""Splice regenerated maps into the guide, add thumbnail/expand behaviour.

Uses depth-aware <div> matching rather than a regex - the blocks contain
nested divs and a regex silently eats the wrong closing tag. Idempotent: the
CSS and JS are only injected once.

Usage:  python3 tools/maps.py [--dest SLUG]
"""
import io, os, re, sys

import _dest
import dayroutes


def close_div(s, i):
    o = re.compile(r"<div[\s>]"); c = re.compile(r"</div>"); d = 0
    while True:
        mo = o.search(s, i); mc = c.search(s, i)
        if mo and mo.start() < mc.start():
            d += 1; i = mo.end()
        else:
            d -= 1; i = mc.end()
            if d == 0:
                return i


def need(s, anchor, what):
    if anchor not in s:
        sys.exit('error: %s anchor not found in the guide - did it change?\n  looking for: %s'
                 % (what, anchor[:90]))


def km_mi(m):
    mi = m / 1609.344
    if m < 30000:
        return '%d mi / %d km' % (round(mi), round(m / 1000.0))
    return '≈%d mi / %d km' % (round(mi / 5.0) * 5, round(m / 1000.0 / 5.0) * 5)


def hm(sec):
    """Driving time, rounded the way a person would say it."""
    h, mn = int(sec // 3600), int(round((sec % 3600) / 60.0))
    if mn == 60:
        h, mn = h + 1, 0
    if not h:
        return '%d min' % mn
    return '%d h %02d' % (h, mn) if mn else '%d h' % h


MEASURED = re.compile(r'<span class="legm">.*?</span>', re.S)

SL_OPEN = '<section class="part" id="savedlist">'
SL_CLOSE = '</section>'


def savedlist(T, dest):
    """Replace the saved-list section with the generated one.

    Sections do not nest in these guides, so this matches to the first
    </section> rather than counting depth the way the gmapwrap blocks have to -
    but it checks that assumption instead of trusting it, because a nested
    <section> would make it eat the wrong closing tag silently.
    """
    frag = os.path.join(dest.mapdir, 'savedlist.html')
    if not os.path.exists(frag):
        return T, False
    n = T.count(SL_OPEN)
    if n != 1:
        sys.exit('error: expected exactly 1 saved-list section, found %d' % n)
    i = T.index(SL_OPEN)
    j = T.index(SL_CLOSE, i)
    if '<section' in T[i + len(SL_OPEN):j]:
        sys.exit('error: a <section> is nested inside the saved-list section - '
                 'this splice would eat the wrong closing tag')
    gen = io.open(frag, encoding='utf-8').read().strip()
    if not gen.startswith(SL_OPEN) or not gen.endswith(SL_CLOSE):
        sys.exit('error: %s is not a whole saved-list section' % frag)
    return T[:i] + gen + T[j + len(SL_CLOSE):], True


def legtable(T, dest):
    """Fill the Distance cell of any <tr data-leg="..."> row, annotate Driving.

    Distance is replaced outright: it is an objective number and the written
    values were approximations.

    Driving is NOT replaced, only annotated. The hand-written times carry things
    a router does not know and cannot infer - "2 h 45 + border", "3 h direct ·
    5-6 h with stops", "8 h 30 - 9 h 30". Overwriting those with a single figure
    loses the border wait and the whole point of a day built around stopping.
    The measured time is appended in a muted span instead, so you can see both
    and notice when they disagree. Same reasoning as the Notes column, which is
    left alone entirely.

    Idempotent: any previous annotation is stripped before a new one is added.
    """
    routes = dest.load('routes.json', default={})
    rows = re.findall(r'<tr data-leg="([a-z0-9-]+)">', T)
    if not rows:
        return T, 0, len(routes)
    if not routes:
        print('  leg table: %d tagged row(s), but no routes.json yet - '
              'run tools/routes.py --fetch (needs network). Numbers left as written.' % len(rows))
        return T, 0, 0

    done = 0
    for rid in rows:
        r = routes.get(rid)
        if not r:
            print('  leg table: no fetched route for "%s" - row left as written' % rid)
            continue
        # Two cells after the leg name; the row's own <td> structure is fixed by
        # the table header, so anchor on the row and rewrite in place.
        pat = re.compile(r'(<tr data-leg="%s">.*?</td>)<td>.*?</td><td>(.*?)</td>' % re.escape(rid),
                         re.S)

        def swap(m):
            written = MEASURED.sub('', m.group(2)).strip()
            note = '<span class="legm"> · %s measured</span>' % hm(r['duration_s'])
            return '%s<td>%s</td><td>%s%s</td>' % (m.group(1), km_mi(r['distance_m']), written, note)

        new, n = pat.subn(swap, T, count=1)
        if n != 1:
            sys.exit('error: leg row "%s" did not rewrite exactly once (matched %d)' % (rid, n))
        T, done = new, done + 1

    if done and '.legm{' not in T:
        anchor = '.mono{'
        need(T, anchor, 'leg-table measured-time CSS')
        T = T.replace(anchor, '.legm{color:var(--muted);font-weight:400;white-space:nowrap}\n'
                              '@media print{.legm{color:#777}}\n' + anchor, 1)
    return T, done, len(routes)


DR_OPEN = re.compile(r'<div class="dayroutes" data-day="(\d+)">')
DAYCARD = r'<details class="day[^"]*" id="day-%s">'
DAYBODY = '<div class="daybody">'


def dayroutebars(T, dest):
    """Splice each day's Google Maps navigation links into its day card.

    The block lands after the first block inside .daybody - .dayhead where the
    day has a photograph, .daycopy where it does not, which is why this counts
    divs rather than looking for one class. That puts it directly under the
    day's travel-time line and above the meals, which is where you look when
    you are about to leave. Idempotent: any block already in the guide is cut
    first, so re-running replaces rather than stacks.
    """
    frag = os.path.join(dest.mapdir, 'dayroutes.html')
    if not os.path.exists(frag):
        return T, 0
    gen = io.open(frag, encoding='utf-8').read()
    blocks = [(m.group(1), gen[m.start():close_div(gen, m.start())])
              for m in DR_OPEN.finditer(gen)]

    while True:
        m = DR_OPEN.search(T)
        if not m:
            break
        T = T[:m.start()].rstrip('\n') + '\n' + T[close_div(T, m.start()):].lstrip('\n')

    done = 0
    for day, block in blocks:
        pat = re.compile(DAYCARD % day)
        hits = pat.findall(T)
        if len(hits) != 1:
            sys.exit('error: day card id="day-%s" appears %d times, expected 1' % (day, len(hits)))
        i = pat.search(T).end()
        b = T.find(DAYBODY, i)
        nxt = T.find('<details class="day', i)
        if b < 0 or (nxt >= 0 and nxt < b):
            sys.exit('error: day card id="day-%s" has no %s to hang its routes on'
                     % (day, DAYBODY))
        j = re.compile(r'<div[\s>]').search(T, b + len(DAYBODY)).start()
        k = close_div(T, j)
        T = T[:k] + '\n' + block + T[k:]
        done += 1
    return T, done


FILT_CSS = """
.mapfilt{display:none;flex-wrap:wrap;gap:7px 16px;margin:11px 0 0}
.gmapwrap.mapopen .mapfilt{display:flex;order:2}
.mfrow{display:flex;flex-wrap:wrap;align-items:center;gap:5px}
.mfl{font:800 .68rem Inter,system-ui,sans-serif;letter-spacing:.1em;text-transform:uppercase;
  color:var(--muted);margin-right:2px}
.mfc{background:#f6f3ec;border:1px solid var(--line);border-radius:999px;padding:4px 11px;
  font:700 .74rem Inter,system-ui,sans-serif;color:var(--forest);cursor:pointer;line-height:1.35}
.mfc:hover{background:#ece6da}
.mfc.on{background:var(--forest);border-color:var(--forest);color:#fff}
.ovl .mkoff{display:none}
.gbtns{display:flex;flex-wrap:wrap;gap:7px;justify-content:flex-end;margin-left:auto}
.gbtns .gbtn{padding:5px 11px;font-size:.72rem}
.gbtns .gbtn.alt{background:#f6f3ec;border-style:dashed}
@media print{.mapfilt{display:none!important}.ovl .mkoff{display:inline!important}}
"""

FILT_JS = """/* maps: filter one map's markers and lines by day and by kind.
   Placement was computed once against the full marker set and is never
   recomputed - a filtered map is sparser than optimal, never wrong. Markers
   carrying no data-day or no data-grp are map furniture and always stay. */
document.querySelectorAll('.gmapwrap').forEach(function(w){
  var bar=w.querySelector('.mapfilt'), svg=w.querySelector('.ovl');
  if(!bar||!svg) return;
  var sel={day:'',grp:''};
  function apply(){
    svg.querySelectorAll('[data-day],[data-grp]').forEach(function(el){
      var d=el.getAttribute('data-day'), g=el.getAttribute('data-grp');
      var okd=!sel.day||!d||d.split(' ').indexOf(sel.day)>=0;
      var okg=!sel.grp||!g||g===sel.grp;
      el.classList.toggle('mkoff',!(okd&&okg));
    });
  }
  bar.querySelectorAll('.mfc').forEach(function(b){
    b.addEventListener('click',function(){
      var f=b.getAttribute('data-f');
      sel[f]=b.getAttribute('data-v');
      bar.querySelectorAll('.mfc[data-f="'+f+'"]').forEach(function(o){
        o.classList.toggle('on',o===b);
      });
      apply();
    });
  });
});
"""


def filterblock(T):
    """Inject the day-route and filter CSS/JS once.

    Separate from the CSS/JS block in main(), which returns early on a guide
    that already has the zoom behaviour - so anything added there would never
    reach an existing guide. Each half guards on its own marker instead.
    """
    if '.mfc{' not in T:
        anchor = ".gmapwrap{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:14px;margin:20px 0}"
        need(T, anchor, 'map-filter CSS')
        T = T.replace(anchor, anchor + FILT_CSS + dayroutes.CSS, 1)
    if "/* maps: filter one map's markers" not in T:
        anchor = "/* print: everything open */"
        need(T, anchor, 'map-filter JS')
        T = T.replace(anchor, FILT_JS + anchor, 1)
    return T


def main():
    dest, _ = _dest.from_args('Splice generated map fragments into the guide.')
    src = dest.guide
    expected = len(dest.load('maps.json'))
    # This script rewrites the guide in place. Snapshot it first: an
    # uncommitted prose pass has been lost here before, and a copy costs
    # nothing. See _dest.snapshot_guide.
    dest.snapshot_guide()
    T = io.open(src, encoding="utf-8").read()

    # ---- replace each gmapwrap block with the regenerated one -----------------
    out = []; pos = 0; n = 0
    for m in re.finditer(r'<div class="gmapwrap">', T):
        if m.start() < pos:
            continue
        end = close_div(T, m.start())
        block = T[m.start():end]
        found = re.search(r'images/tiles/([a-z0-9_-]+)/', block)
        if not found:
            sys.exit('error: a gmapwrap block has no images/tiles/<name>/ reference')
        name = found.group(1)
        frag = dest.fragment(name)
        if not os.path.exists(frag):
            sys.exit('error: %s missing - run overlay.py first' % frag)
        gen = io.open(frag, encoding="utf-8").read().strip()
        out.append(T[pos:m.start()]); out.append(gen); pos = end; n += 1
    out.append(T[pos:])
    T = "".join(out)
    if n != expected:
        sys.exit("replaced %d maps, expected %d (maps.json)" % (n, expected))

    # ---- leg table: measured distances and times ------------------------------
    T, legs, have = legtable(T, dest)

    # ---- saved-list checklist -------------------------------------------------
    # Carries its own CSS and JS, so re-splicing replaces them wholesale and the
    # inject-once dance below does not apply to it.
    T, sl = savedlist(T, dest)

    # ---- per-day Google Maps navigation links ---------------------------------
    T, dr = dayroutebars(T, dest)

    # ---- filter chips and day-route styling -----------------------------------
    T = filterblock(T)

    # ---- CSS: thumbnail by default, full size when opened --------------------
    ANCHOR = ".gmapwrap{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:14px;margin:20px 0}"
    need(T, ANCHOR, 'map CSS')
    if ".mapzoom{" in T:
        io.open(src, "w", encoding="utf-8").write(T)
        print("spliced %d maps, %d leg row(s), %d day route bar(s)%s "
              "(css/js already present) · %d KB"
              % (n, legs, dr, ', saved list' if sl else '', len(T) // 1024))
        return
    CSS = ANCHOR + """
.gmapwrap{display:grid;grid-template-columns:auto minmax(0,1fr);gap:0 16px;align-items:start}
.gmapwrap .gmap{height:210px;width:auto;cursor:zoom-in}
.gmapwrap .gmapfoot{display:none}
.mapside{display:flex;flex-direction:column;align-items:flex-start;gap:9px;min-width:0}
.mapzoom{background:#f2ece0;border:1px solid #d9cfba;border-radius:999px;padding:7px 14px;
  font:800 .76rem Inter,system-ui,sans-serif;color:var(--forest);cursor:pointer;white-space:nowrap;
  display:inline-flex;align-items:center;gap:7px;letter-spacing:.04em;text-transform:uppercase}
.mapzoom:hover{background:#e6ddc9}
.mapzoom i{font-style:normal;color:var(--gold);font-size:.95rem}
.gmapwrap .cap{margin:0}
.gmapwrap.mapopen{display:flex;flex-direction:column;gap:0}
.gmapwrap.mapopen .gmap{height:auto;width:100%;cursor:zoom-out;order:1}
.gmapwrap.mapopen .gmapfoot{display:flex;order:2}
.gmapwrap.mapopen .mapside{order:3;flex-direction:column-reverse;align-items:stretch;margin-top:10px}
.gmapwrap.mapopen .mapzoom{align-self:flex-start;margin-top:10px}
@media(max-width:760px){
 .gmapwrap{grid-template-columns:1fr;gap:12px}
 .gmapwrap .gmap{height:auto;width:100%}
 .mapzoom{align-self:flex-start}
}"""
    T = T.replace(ANCHOR, CSS, 1)

    # ---- JS: toggle -----------------------------------------------------------
    JS_ANCHOR = "/* print: everything open */"
    need(T, JS_ANCHOR, 'map JS')
    JS = """/* maps: thumbnail until clicked */
document.querySelectorAll('.gmapwrap').forEach(function(w){
  var btn=w.querySelector('.mapzoom'), map=w.querySelector('.gmap');
  if(!btn||!map) return;
  function set(open){
    w.classList.toggle('mapopen',open);
    btn.setAttribute('aria-expanded',open?'true':'false');
    btn.querySelector('span').textContent=open?'Collapse map':'Expand map';
  }
  btn.addEventListener('click',function(){ set(!w.classList.contains('mapopen')); });
  map.addEventListener('click',function(e){
    if(e.target.closest('a')) return;              /* day badges keep working */
    set(!w.classList.contains('mapopen'));
  });
});
""" + JS_ANCHOR
    T = T.replace(JS_ANCHOR, JS, 1)

    PR_OLD = "window.addEventListener('beforeprint',function(){ document.querySelectorAll('details').forEach(function(d){ d.dataset.pre=d.open?'1':''; d.open=true; }); });"
    need(T, PR_OLD, 'beforeprint handler')
    PR_NEW = ("window.addEventListener('beforeprint',function(){ document.querySelectorAll('details').forEach(function(d){ d.dataset.pre=d.open?'1':''; d.open=true; });"
              " document.querySelectorAll('.gmapwrap').forEach(function(w){ w.dataset.pre=w.classList.contains('mapopen')?'1':''; w.classList.add('mapopen'); }); });")
    T = T.replace(PR_OLD, PR_NEW, 1)
    PA_OLD = "window.addEventListener('afterprint',function(){ document.querySelectorAll('details').forEach(function(d){ d.open=d.dataset.pre==='1'; }); });"
    need(T, PA_OLD, 'afterprint handler')
    PA_NEW = ("window.addEventListener('afterprint',function(){ document.querySelectorAll('details').forEach(function(d){ d.open=d.dataset.pre==='1'; });"
              " document.querySelectorAll('.gmapwrap').forEach(function(w){ w.classList.toggle('mapopen',w.dataset.pre==='1'); }); });")
    T = T.replace(PA_OLD, PA_NEW, 1)

    io.open(src, "w", encoding="utf-8").write(T)
    print("spliced %d maps, %d leg row(s), %d day route bar(s)%s · %d KB"
          % (n, legs, dr, ', saved list' if sl else '', len(T) // 1024))


if __name__ == '__main__':
    main()
