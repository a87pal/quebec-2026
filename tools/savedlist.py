#!/usr/bin/env python3
"""Build the checklist for loading this trip into a Google Maps saved list.

You navigate from a saved list - it draws on the main Google Maps map, syncs to
the phone and hands you native navigation, which a My Maps layer cannot do. But
there is no API for saved lists and no import path, so the list is loaded by
hand, one place at a time.

This page makes that loop fast without automating anything:

    [Enter] opens the place    you click Save    [Space] ticks and advances

Deliberately no browser automation. Driving a signed-in Google account with
Playwright or an extension means Google's terms, an account worth more than the
15 minutes it saves, and selectors against a UI that rotates its class names.
The sequencing is the slow part, and sequencing needs no automation.

Every link carries a Place ID where tools/placeid.py has found one, so it opens
one exact place rather than a search you have to check. The verified coordinate
stays in the URL as `query`: Google's docs say `query` is used only when the
place ID cannot be resolved, so a stale ID degrades to the right spot rather
than a confident wrong guess.

Emits maps/savedlist.html, a fragment. tools/maps.py splices it in - this script
never writes guide.html, so the snapshot-before-rewrite safety net stays in one
place. CSS and JS live inside the fragment rather than being injected into the
guide's own blocks, which makes re-splicing idempotent by construction instead
of by a matched-once dance.

Usage:  python3 tools/savedlist.py [--dest SLUG]
"""
import html
import io
import os
import urllib.parse

import _dest

MAX_MATCHED = 64


def esc(s):
    return html.escape(str(s), quote=True)


def link(name, p):
    """A Maps URL that names the place exactly when we know its Place ID.

    `query` is required by the api=1 spec and is what Google falls back to when
    the place ID will not resolve. A map marker has a verified coordinate, which
    is the best possible fallback. An extra has none, so it falls back to the
    text it was found by.
    """
    if p.get('lat') is not None and p.get('lon') is not None:
        u = ('https://www.google.com/maps/search/?api=1&query=%.5f,%.5f'
             % (p['lat'], p['lon']))
    else:
        u = ('https://www.google.com/maps/search/?api=1&query='
             + urllib.parse.quote(p.get('query') or name))
    if p.get('place_id'):
        u += '&query_place_id=' + p['place_id']
    return u


def rows(dest, places, extras):
    """Places grouped by region, in the order the maps are declared.

    Regions that are not maps - the home-* legs - sort to the end rather than
    being dropped, the same fallback tripmap.py uses.

    Extras have no region of their own; they inherit the one belonging to the
    place they sit near, so the whale wharf lands beside Baie-Ste-Catherine
    rather than in a bucket of its own.
    """
    order = list(dest.load('maps.json').keys())
    groups = {}
    for name, p in places.items():
        if p.get('lat') is None or p.get('lon') is None:
            continue
        groups.setdefault(p.get('region') or 'elsewhere', []).append((name, p))
    for name, e in extras.items():
        anchor = places.get(e.get('near') or '') or {}
        groups.setdefault(anchor.get('region') or 'elsewhere', []).append((name, e))
    def rank(r):
        return (order.index(r), '') if r in order else (len(order), r)
    return [(r, sorted(groups[r])) for r in sorted(groups, key=rank)]


CSS = """<style>
#savedlist .sl{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:0;overflow:hidden}
#savedlist .sl:focus{outline:2px solid var(--forest);outline-offset:2px}
#savedlist .slbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;
  padding:13px 17px;border-bottom:1px solid var(--line);background:#f7f4ec}
#savedlist .slcount{font:800 .95rem Inter,system-ui,sans-serif;color:var(--forest);white-space:nowrap}
#savedlist .slkeys{font-size:.8rem;color:var(--muted);flex:1;min-width:180px}
#savedlist .slkeys kbd{font:inherit;font-weight:700;color:var(--forest);background:#edf2ee;
  border:1px solid #c9d8cf;border-radius:5px;padding:1px 5px;margin:0 2px}
#savedlist .slreset{background:none;border:1px solid var(--line);border-radius:999px;
  padding:5px 12px;font:700 .74rem Inter,system-ui,sans-serif;color:var(--muted);cursor:pointer;
  text-transform:uppercase;letter-spacing:.04em}
#savedlist .slreset:hover{color:var(--wine);border-color:var(--wine)}
#savedlist ol.sllist{list-style:none;margin:0;padding:0}
#savedlist .slsep{padding:11px 17px 5px;font:800 .72rem Inter,system-ui,sans-serif;
  color:var(--gold);text-transform:uppercase;letter-spacing:.09em}
#savedlist .slrow{display:grid;grid-template-columns:26px 1fr;gap:0 10px;align-items:baseline;
  padding:7px 17px;border-top:1px solid #f0ebe0}
#savedlist .slrow:before{content:"\\2610";color:var(--gold);font-size:1rem;line-height:1.4}
#savedlist .slrow.on:before{content:"\\2713";color:var(--forest)}
#savedlist .slrow.on a{color:var(--muted);text-decoration:line-through}
#savedlist .sl.slon .slrow.cur{background:#edf2ee}
#savedlist .sl.slon .slrow.cur:after{content:"\\2190 Enter opens it";grid-column:2;
  font-size:.75rem;color:var(--forest);font-weight:700}
#savedlist .slrow a{font-weight:700;font-size:.95rem}
#savedlist .slsub{grid-column:2;font-size:.78rem;color:var(--muted)}
#savedlist .slhint{padding:11px 17px;border-top:1px solid var(--line);
  font-size:.8rem;color:var(--muted);background:#f7f4ec}
@media print{#savedlist{display:none}}
</style>"""


JS = """<script>
(function(){
  var root=document.getElementById('savedlist'); if(!root) return;
  var box=root.querySelector('.sl'); if(!box) return;
  var KEY=box.getAttribute('data-key');
  var rows=[].slice.call(root.querySelectorAll('.slrow'));
  var out=root.querySelector('.slcount');
  if(!rows.length) return;
  var done={}, cur=0, pending=-1;
  try{
    var st=JSON.parse(localStorage.getItem(KEY));
    if(st&&typeof st==='object'){ done=st.done||{}; cur=st.cur||0; }
  }catch(e){}
  if(cur<0||cur>=rows.length) cur=0;
  function save(){ try{ localStorage.setItem(KEY,JSON.stringify({done:done,cur:cur})); }catch(e){} }
  function idOf(r){ return r.getAttribute('data-id'); }
  function render(scroll){
    var n=0,i;
    for(i=0;i<rows.length;i++){
      var on=!!done[idOf(rows[i])];
      if(on) n++;
      rows[i].className='slrow'+(on?' on':'')+(i===cur?' cur':'');
    }
    out.textContent=n+' / '+rows.length;
    if(scroll&&rows[cur]) rows[cur].scrollIntoView({block:'nearest'});
  }
  function tick(v){ if(v){ done[idOf(rows[cur])]=1; } else { delete done[idOf(rows[cur])]; } }
  function step(d){ cur=Math.max(0,Math.min(rows.length-1,cur+d)); }
  root.addEventListener('click',function(e){
    var r=e.target.closest?e.target.closest('.slrow'):null;
    if(r){ var i=rows.indexOf(r); if(i>=0){ cur=i; if(e.target.tagName==='A') pending=i; save(); render(false); } }
  });
  box.addEventListener('focus',function(){ box.classList.add('slon'); });
  box.addEventListener('blur',function(){ box.classList.remove('slon'); });
  box.addEventListener('keydown',function(e){
    var t=e.target;
    /* Let the controls be controls: a focused Reset must answer Space, and a
       focused link must answer Enter itself rather than being opened twice. */
    if(t&&/^(INPUT|TEXTAREA|SELECT|BUTTON)$/.test(t.tagName)) return;
    if(t&&t.tagName==='A'){
      if(e.key!=='Enter') return;
      var r=t.closest?t.closest('.slrow'):null;
      var i=r?rows.indexOf(r):-1;
      if(i>=0){ pending=i; cur=i; save(); render(false); }
      return;
    }
    if(e.key==='Enter'){
      var a=rows[cur].querySelector('a');
      if(a){ pending=cur; window.open(a.href,'_blank','noopener'); }
    }
    else if(e.key===' '||e.key==='Spacebar'){ tick(true); step(1); }
    else if(e.key==='ArrowLeft'){ step(-1); tick(false); }
    else if(e.key==='ArrowDown'){ step(1); }
    else if(e.key==='ArrowUp'){ step(-1); }
    else return;
    e.preventDefault(); save(); render(true);
  });
  document.addEventListener('visibilitychange',function(){
    if(document.visibilityState!=='visible'||pending<0) return;
    /* Came back from the tab we opened: assume it was saved and move on.
       Forgiving on purpose - ArrowLeft undoes a wrong tick, which is cheaper
       than confirming every one of them. */
    done[idOf(rows[pending])]=1;
    if(cur===pending) step(1);
    pending=-1; save(); render(true);
  });
  var rst=root.querySelector('.slreset');
  if(rst) rst.addEventListener('click',function(){
    done={}; cur=0; pending=-1; save(); render(true);
  });
  render(false);
})();
</script>"""


def build(dest):
    # Default rather than fatal: check.sh walks every destination, and a new one
    # can legitimately have the section before it has any resolved coordinates.
    places = dest.load('places.json', default={})
    extras = dest.load('extras.json', default={})
    meta = dest.meta()
    grouped = rows(dest, places, extras)
    total = sum(len(v) for _, v in grouped)
    withid = sum(1 for _, v in grouped for _, p in v if p.get('place_id'))

    o = ['<section class="part" id="savedlist">',
         '<div class="parthead"><div class="pnum">Appendix</div>'
         '<h2>Load the driving list</h2>'
         '<p class="plede">Google Maps has no way to import a saved list, so it goes in '
         'one place at a time. This does the sequencing and remembers where you stopped; '
         'you click Save. Do it once on a laptop, then share the list rather than '
         'loading it twice.</p></div>',
         CSS,
         '<div class="sl" tabindex="0" data-key="travel.%s.savedlist.v1">' % esc(dest.slug),
         '<div class="slbar"><div class="slcount">0 / %d</div>' % total,
         '<div class="slkeys">Click the list, then <kbd>Enter</kbd> opens the next place · '
         '<kbd>Space</kbd> ticks it · <kbd>←</kbd> steps back and unticks</div>',
         '<button class="slreset" type="button">Reset</button></div>',
         '<ol class="sllist">']

    for region, items in grouped:
        o.append('<li class="slsep">%s</li>' % esc(region))
        for name, p in items:
            sub = str(p.get('note') or p.get('matched') or p.get('source') or '')
            if len(sub) > MAX_MATCHED:
                sub = sub[:MAX_MATCHED - 1] + '…'
            o.append('<li class="slrow" data-id="%s">'
                     '<a href="%s" target="_blank" rel="noopener">%s</a>'
                     '<span class="slsub">%s</span></li>'
                     % (esc(name), esc(link(name, p)), esc(name), esc(sub)))

    o.append('</ol>')
    o.append('<div class="slhint">%d of %d places open an exact Google place; the rest '
             'open the verified coordinate. Progress is kept in this browser only.</div>'
             % (withid, total))
    o.append('</div>')
    o.append(JS)
    o.append('</section>')

    path = os.path.join(dest.mapdir, 'savedlist.html')
    io.open(path, 'w', encoding='utf-8').write('\n'.join(o) + '\n')
    print('%s: %d places in %d regions, %d with a Place ID -> %s'
          % (meta.get('title', dest.slug), total, len(grouped), withid, path))
    if withid < total:
        print('  run tools/placeid.py --write to sharpen the remaining %d'
              % (total - withid))


if __name__ == '__main__':
    dest, _ = _dest.from_args('Build the saved-list loading checklist.')
    build(dest)
