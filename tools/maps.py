#!/usr/bin/env python3
"""Splice regenerated maps into the guide, add thumbnail/expand behaviour.

Uses depth-aware <div> matching rather than a regex - the blocks contain
nested divs and a regex silently eats the wrong closing tag. Idempotent: the
CSS and JS are only injected once.

Usage:  python3 tools/maps.py [--dest SLUG]
"""
import io, os, re, sys

import _dest


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


def main():
    dest, _ = _dest.from_args('Splice generated map fragments into the guide.')
    src = dest.guide
    expected = len(dest.load('maps.json'))
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

    # ---- CSS: thumbnail by default, full size when opened --------------------
    ANCHOR = ".gmapwrap{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:14px;margin:20px 0}"
    need(T, ANCHOR, 'map CSS')
    if ".mapzoom{" in T:
        io.open(src, "w", encoding="utf-8").write(T)
        print("spliced %d maps, %d leg row(s) (css/js already present) · %d KB"
              % (n, legs, len(T) // 1024))
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
    print("spliced %d maps, %d leg row(s) · %d KB" % (n, legs, len(T) // 1024))


if __name__ == '__main__':
    main()
