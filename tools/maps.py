#!/usr/bin/env python3
"""Splice regenerated maps into the guide, add thumbnail/expand behaviour."""
import io, re, sys
SRC="/Users/anand.palaniappan1/src/qubec/quebec-v3.html"
GEN="/Users/anand.palaniappan1/src/qubec/tools/"
T=io.open(SRC,encoding="utf-8").read()

def close_div(s,i):
    o=re.compile(r"<div[\s>]"); c=re.compile(r"</div>"); d=0
    while True:
        mo=o.search(s,i); mc=c.search(s,i)
        if mo and mo.start()<mc.start(): d+=1; i=mo.end()
        else:
            d-=1; i=mc.end()
            if d==0: return i

# ---- replace each gmapwrap block with the regenerated one -----------------
out=[]; pos=0; n=0
for m in re.finditer(r'<div class="gmapwrap">',T):
    if m.start()<pos: continue
    end=close_div(T,m.start())
    block=T[m.start():end]
    name=re.search(r'images/tiles/([a-z]+)/',block).group(1)
    gen=io.open(GEN+"gmap_%s.html"%name,encoding="utf-8").read().strip()
    out.append(T[pos:m.start()]); out.append(gen); pos=end; n+=1
out.append(T[pos:])
T="".join(out)
if n!=6: sys.exit("replaced %d maps, expected 6"%n)

# ---- CSS: thumbnail by default, full size when opened --------------------
ANCHOR=".gmapwrap{background:var(--card);border:1px solid var(--line);border-radius:18px;padding:14px;margin:20px 0}"
assert ANCHOR in T
if ".mapzoom{" in T:
    io.open(SRC,"w",encoding="utf-8").write(T)
    print("spliced %d maps (css/js already present) · %d KB"%(n,len(T)//1024)); raise SystemExit
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
T=T.replace(ANCHOR,CSS,1)

# ---- JS: toggle -----------------------------------------------------------
JS_ANCHOR="/* print: everything open */"
assert JS_ANCHOR in T
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
T=T.replace(JS_ANCHOR,JS,1)

PR_OLD="window.addEventListener('beforeprint',function(){ document.querySelectorAll('details').forEach(function(d){ d.dataset.pre=d.open?'1':''; d.open=true; }); });"
assert PR_OLD in T
PR_NEW=("window.addEventListener('beforeprint',function(){ document.querySelectorAll('details').forEach(function(d){ d.dataset.pre=d.open?'1':''; d.open=true; });"
        " document.querySelectorAll('.gmapwrap').forEach(function(w){ w.dataset.pre=w.classList.contains('mapopen')?'1':''; w.classList.add('mapopen'); }); });")
T=T.replace(PR_OLD,PR_NEW,1)
PA_OLD="window.addEventListener('afterprint',function(){ document.querySelectorAll('details').forEach(function(d){ d.open=d.dataset.pre==='1'; }); });"
assert PA_OLD in T
PA_NEW=("window.addEventListener('afterprint',function(){ document.querySelectorAll('details').forEach(function(d){ d.open=d.dataset.pre==='1'; });"
        " document.querySelectorAll('.gmapwrap').forEach(function(w){ w.classList.toggle('mapopen',w.dataset.pre==='1'); }); });")
T=T.replace(PA_OLD,PA_NEW,1)

io.open(SRC,"w",encoding="utf-8").write(T)
print("spliced %d maps · %d KB"%(n,len(T)//1024))
