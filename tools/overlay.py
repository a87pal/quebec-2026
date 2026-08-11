# -*- coding: utf-8 -*-
import math, json, os, html
HERE=os.path.dirname(os.path.abspath(__file__))
OUT=os.environ.get('MAPOUT', HERE+'/')
meta=json.load(open(os.path.join(HERE,'tilemeta.json')))

# --- coordinates come from places.json, not from the literals below ---------
# The lat/lon written at each marker() call site is a fallback only. If the
# label appears in places.json (built by resolve.py from OSM/Wikidata), that
# coordinate wins. Never fix a marker's position by editing the literal --
# fix the query in places.json and re-run resolve.py, or pin it as "manual:".
PLACES=json.load(open(os.path.join(HERE,'places.json'))) if os.path.exists(os.path.join(HERE,'places.json')) else {}
UNSOURCED=[]
DISPW={'route':1100,'franconia':720,'montreal':1100,'quebec':1100,'beaupre':1100,'charlevoix':720}
K={}

def mk(name):
    m=meta[name]; z=m['z']; ox=m['ox']; oy=m['oy']
    K['k']=m['W']/DISPW.get(name,1100)
    def P(lat,lon):
        n=2**z
        x=(lon+180.0)/360.0*n*256-ox
        lr=math.radians(lat)
        y=(1.0-math.log(math.tan(lr)+1/math.cos(lr))/math.pi)/2.0*n*256-oy
        return round(x,1),round(y,1)
    return P,m

def path(P,pts):
    return " ".join(("M" if i==0 else "L")+"%s,%s"%P(a,b) for i,(a,b) in enumerate(pts))

def dash(cls,P,pts,w):
    return '<path class="%s" d="%s" stroke-width="%.1f"/>'%(cls,path(P,pts),w*K['k'])

def route(P,pts,cls="rt",w=7):
    k=K['k']; d=path(P,pts)
    return ('<path class="cas" d="%s" stroke-width="%.1f"/><path class="%s" d="%s" stroke-width="%.1f"/>'
            %(d,(w+5)*k,cls,d,w*k))

def marker(P,lat,lon,label,sub="",kind="stop",n=None,anchor="start",dx=None,dy=0,r=None,day=None,daytext=None,lead=False):
    k=K.get('k',1.0)
    pl=PLACES.get(label.strip())
    if pl: lat,lon=pl['lat'],pl['lon']
    else:  UNSOURCED.append(label.strip())
    x,y=P(lat,lon)
    rr=(r if r else (11 if kind in('base','hi') else 8))*k
    dx=(dx*k) if dx is not None else (rr+8*k if anchor=="start" else -(rr+8*k))
    dy=dy*k
    fs=16*k; fs2=13*k; sw=5*k; sw2=4.2*k; cs=3.2*k
    o='<g class="mk %s">'%kind
    if lead:
        ex=x+dx-(5*k if anchor=='start' else -5*k)
        ey=y+dy+5*k-fs*0.35
        o+='<path class="ldr" d="M%.1f,%.1f L%.1f,%.1f" stroke-width="%.1f"/>'%(x,y,ex,ey,1.7*k)
    o+='<circle cx="%.1f" cy="%.1f" r="%.1f" stroke-width="%.1f"/>'%(x,y,rr,cs)
    if n: o+='<text class="mn" x="%.1f" y="%.1f" text-anchor="middle" font-size="%.1f">%s</text>'%(x,y+4*k,fs2,n)
    o+='<text class="ml" x="%.1f" y="%.1f" text-anchor="%s" font-size="%.1f" stroke-width="%.1f">%s</text>'%(x+dx,y+dy+5*k,anchor,fs,sw,html.escape(label))
    if sub: o+='<text class="ms" x="%.1f" y="%.1f" text-anchor="%s" font-size="%.1f" stroke-width="%.1f">%s</text>'%(x+dx,y+dy+5*k+fs*1.15,anchor,fs2,sw2,html.escape(sub))
    if daytext:
        bw=(len(daytext)*8.4+15)*k; bh=21*k
        bx=(x-rr-7*k-bw) if anchor=="start" else (x+rr+7*k)
        o+=('<g class="dayb"><rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%.1f"/>'
            '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="%.1f">%s</text></g>'
            %(bx,y-bh/2,bw,bh,bh/2,bx+bw/2,y+4.8*k,12.5*k,html.escape(daytext)))
    o+='</g>'
    if day is not None:
        o='<a class="mklink" href="#day-%s" aria-label="%s — go to day %s">%s</a>'%(day,html.escape(label),day,o)
    return o

def wrap(name,body,legend,cap,gmaps):
    m=meta[name]
    tiles=[]
    W,H=m['W'],m['H']
    for tx in range(m['tx0'],m['tx1']+1):
        for ty in range(m['ty0'],m['ty1']+1):
            l=(tx*256-m['ox'])/W*100; t=(ty*256-m['oy'])/H*100
            tiles.append('<img src="images/tiles/%s/%d_%d.jpg" alt="" loading="lazy" style="left:%.4f%%;top:%.4f%%;width:%.4f%%"/>'
                         %(name,tx,ty,l,t,256/W*100))
    return ('<div class="gmapwrap">\n<div class="gmap" style="aspect-ratio:%d/%d">\n<div class="tiles">%s</div>\n'
            '<svg class="ovl" viewBox="0 0 %d %d" preserveAspectRatio="none" role="img" aria-label="%s">%s</svg>\n</div>\n'
            '<div class="mapside"><button class="mapzoom" type="button" aria-expanded="false">'
            '<span>Expand map</span> <i>⤢</i></button>\n'
            '<div class="cap">%s <span class="attrib">Basemap: Esri World Topo — Esri, HERE, Garmin, USGS, NGA, OpenStreetMap contributors.</span></div></div>\n'
            '<div class="gmapfoot"><div class="maplegend">%s</div>'
            '<a class="gbtn" target="_blank" rel="noopener" href="%s">Open this route in Google Maps ↗</a></div>\n</div>'
            %(W,H,''.join(tiles),W,H,html.escape(cap[:110]),body,cap,legend,gmaps))

frag={}

# ---------------- ROUTE ----------------
P,m=mk('route')
b=[]
b.append(route(P,[(41.499,-72.900),(41.76,-72.68),(42.10,-72.59),(42.62,-72.58),(43.13,-72.49),(43.65,-72.32),(44.02,-72.02),(44.046,-71.678)]))
b.append(route(P,[(44.046,-71.678),(44.42,-71.85),(44.65,-72.02),(44.80,-72.10),(45.005,-72.100),(45.15,-72.15),(45.281,-72.248)]))
b.append(route(P,[(45.281,-72.248),(45.40,-72.60),(45.47,-73.10),(45.508,-73.567)]))
b.append(route(P,[(45.508,-73.567),(45.75,-73.30),(46.05,-72.90),(46.343,-72.542),(46.55,-72.15),(46.652,-71.921),(46.75,-71.55),(46.813,-71.208)]))
b.append(route(P,[(46.813,-71.208),(47.02,-70.93),(47.25,-70.70),(47.443,-70.501),(47.483,-70.343),(47.573,-70.212),(47.653,-70.152),(47.85,-69.95),(48.02,-69.79),(48.107,-69.731)]))
b.append(dash('spur',P,[(47.443,-70.501),(47.60,-70.50),(47.75,-70.46),(47.868,-70.421)],6))
b.append(dash('back',P,[(47.443,-70.501),(46.813,-71.208),(46.343,-72.542),(45.508,-73.567),(45.00,-73.37),(44.70,-73.45),(43.30,-73.60),(42.65,-73.76),(42.10,-73.35),(41.499,-72.900)],4))
b.append(marker(P,41.499,-72.900,"Cheshire, CT","start · finish","home",r=10,dy=-6,day=0,daytext="0 · 11"))
b.append(marker(P,44.046,-71.678,"Lincoln, NH","2 nights · Franconia","base",r=11,dy=-6,day=1,daytext="0–1"))
b.append(marker(P,45.281,-72.248,"St-Benoît-du-Lac","the abbey","stop",anchor="start",dy=6,day=2,daytext="2"))
b.append(marker(P,45.005,-72.100,"Derby Line","border","stop",anchor="end",dy=12,r=6))
b.append(marker(P,45.508,-73.567,"MONTRÉAL","3 nights","base",r=13,anchor="end",dy=-20,day=2,daytext="2–4"))
b.append(marker(P,46.343,-72.542,"Trois-Rivières","","stop",anchor="end",dy=10,r=6,day=5,daytext="5"))
b.append(marker(P,46.652,-71.921,"Deschambault","","stop",anchor="end",dy=-4,r=6))
b.append(marker(P,46.813,-71.208,"QUÉBEC CITY","4 nights","base",r=13,dy=-16,day=5,daytext="5–8"))
b.append(marker(P,47.443,-70.501,"Baie-Saint-Paul","2 nights","base",r=11,dy=10,day=9,daytext="9–10"))
b.append(marker(P,47.868,-70.421,"Hautes-Gorges","","hi",anchor="end",dy=-4,day=10,daytext="10"))
b.append(marker(P,48.107,-69.731,"Baie-Ste-Catherine","whales","ev",dy=-6,day=9,daytext="9"))
frag['route']=wrap('route',''.join(b),
 '<span><i class="lg base"></i>Base</span><span><i class="lg hi"></i>Marquee</span><span><i class="lg ev"></i>Whales</span>'
 '<span><i class="lg ln"></i>Outbound</span><span><i class="lg ln bk"></i>Direct run home</span>',
 '<b>The numbered badges are day numbers — click one to jump to that day below.</b> The full loop: Cheshire → Franconia Notch → the abbey → Montréal → the Chemin du Roy → Québec City → Charlevoix → the whales, then straight home.',
 'https://www.google.com/maps/dir/Cheshire,+CT/Lincoln,+NH/Saint-Beno%C3%AEt-du-Lac,+QC/Montreal,+QC/Trois-Rivi%C3%A8res,+QC/Quebec+City,+QC/Baie-Saint-Paul,+QC/Baie-Sainte-Catherine,+QC')

# ---------------- FRANCONIA ----------------
P,m=mk('franconia')
b=[]
b.append(route(P,[(44.1417,-71.6816),(44.1401,-71.6757),(44.1387,-71.6688),(44.1392,-71.6598),(44.1402,-71.6508),(44.1413,-71.6437)],w=6))
b.append(route(P,[(44.1413,-71.6437),(44.1445,-71.6440),(44.1483,-71.6444),(44.1545,-71.6449),(44.1605,-71.6446)],"ridge",w=8))
b.append(route(P,[(44.1605,-71.6446),(44.1610,-71.6553),(44.1580,-71.6641),(44.1516,-71.6725),(44.1450,-71.6789),(44.1417,-71.6816)],w=6))
b.append(marker(P,44.1417,-71.6816,"Lafayette Place trailhead","park by 7:15 a.m. · free","base",anchor="end",dy=-6,r=10))
b.append(marker(P,44.1413,-71.6437,"Little Haystack ≈4,760 ft","treeline · not on the NH48","stop",dy=-4))
b.append(marker(P,44.1483,-71.6444,"Mt. Lincoln 5,089 ft","","stop",dy=4))
b.append(marker(P,44.1605,-71.6446,"Mt. Lafayette 5,249 ft","high point","hi",dy=-6,r=11))
b.append(marker(P,44.1610,-71.6553,"Greenleaf Hut","water · soup · bail-out","stop",anchor="end",dy=6))
b.append(marker(P,44.0975,-71.6796,"Flume Gorge","storm-day plan","stop",dy=4))
b.append(marker(P,44.1216,-71.6829,"The Basin","free · 5 min","stop",anchor="end",dy=4,r=6))
b.append(marker(P,44.1786,-71.6897,"Artist's Bluff","sunrise, Day 2","stop",dy=-4))
b.append(marker(P,44.1719,-71.6976,"Cannon Mtn Tramway","","stop",anchor="end",dy=8,r=6))
b.append(marker(P,44.0462,-71.6712,"Lincoln","your base","base",dy=4,r=10))
frag['franconia']=wrap('franconia',''.join(b),
 '<span><i class="lg base"></i>Base / trailhead</span><span><i class="lg hi"></i>High point</span>'
 '<span><i class="lg ln"></i>Trail</span><span><i class="lg ln rg"></i>Above treeline</span>',
 'The loop runs clockwise: up Falling Waters, 1.7 miles along the open crest, down Greenleaf and the Old Bridle Path.',
 'https://www.google.com/maps/dir/Lincoln,+NH/Lafayette+Place+Campground,+Franconia,+NH')

# ---------------- MONTREAL ----------------
P,m=mk('montreal')
b=[]
b.append(dash('walk',P,[(45.5227,-73.6031),(45.5300,-73.6100),(45.5366,-73.6152)],5))
b.append(dash('walk',P,[(45.5152,-73.5849),(45.5090,-73.5880),(45.5039,-73.5877),(45.4990,-73.6020),(45.4923,-73.6180)],5))
b.append(marker(P,45.5230,-73.5960,"YOUR BASE — Plateau / Mile End","nights 3–5","base",anchor="end",dy=-34,r=12))
b.append(marker(P,45.5227,-73.6031,"St-Viateur & Fairmount Bagel","4 min apart · 24 h","stop",anchor="end",dy=70,r=7,lead=True))
b.append(marker(P,45.5366,-73.6152,"Marché Jean-Talon","peak harvest","hi",anchor="end",dy=-4))
b.append(marker(P,45.5152,-73.5849,"Tam-Tams","Sun 12–6 · free","ev",anchor="end",dy=-32))
b.append(marker(P,45.5039,-73.5877,"Kondiaronk Belvédère","the view","stop",anchor="end",dy=6))
b.append(marker(P,45.4923,-73.6180,"Saint Joseph's Oratory","largest dome in Canada","hi",dy=6))
b.append(marker(P,45.5045,-73.5560,"Notre-Dame Basilica + AURA","","hi",dy=-6))
b.append(marker(P,45.5024,-73.5541,"Pointe-à-Callière","","stop",dy=12,r=7))
b.append(marker(P,45.5085,-73.5654,"Esplanade Tranquille","MUTEK free stage, 5 p.m.","ev",anchor="end",dy=-4))
b.append(marker(P,45.5590,-73.5620,"Botanical Garden","Gardens of Light","ev",anchor="end",dy=4))
b.append(marker(P,45.4790,-73.5793,"Atwater Market","Lachine Canal","stop",dy=4,r=6))
frag['montreal']=wrap('montreal',''.join(b),
 '<span><i class="lg base"></i>Your base</span><span><i class="lg hi"></i>Marquee</span>'
 '<span><i class="lg ev"></i>Evening</span><span><i class="lg ln wk"></i>Suggested walk</span>',
 'Everything here is Métro or foot. The dotted lines are the two walks worth doing end to end: bagels to Jean-Talon, and Tam-Tams over the mountain to the Oratory.',
 'https://www.google.com/maps/dir/Mile+End,+Montreal/March%C3%A9+Jean-Talon/Mont+Royal+Chalet/Saint+Joseph%27s+Oratory')

# ---------------- QUEBEC ----------------
P,m=mk('quebec')
b=[]
b.append(dash('walk',P,[(46.8108,-71.2247),(46.8112,-71.2188),(46.8109,-71.2117),(46.8078,-71.2065),(46.8030,-71.2192),(46.8072,-71.2150),(46.8120,-71.2052),(46.8144,-71.2076),(46.8137,-71.2049),(46.8123,-71.2028),(46.8135,-71.2033),(46.8135,-71.2003)],5))
b.append(marker(P,46.8108,-71.2247,"YOUR BASE — St-Jean-Baptiste","nights 6–9","base",anchor="end",dy=-6,r=12))
b.append(marker(P,46.8109,-71.2117,"Porte Saint-Louis","start the ramparts","stop",anchor="end",dy=33,r=7))
b.append(marker(P,46.8078,-71.2065,"La Citadelle","star fort","hi",dy=14))
b.append(marker(P,46.8030,-71.2192,"Plains of Abraham","1759 battlefield","hi",dy=16))
b.append(marker(P,46.8120,-71.2052,"Château Frontenac","Dufferin Terrace","hi",dx=16,dy=70,lead=True))
b.append(marker(P,46.8144,-71.2076,"Notre-Dame de Québec","the Holy Door","hi",anchor="end",dx=-13,dy=-26))
b.append(marker(P,46.8139,-71.2086,"Morrin Centre","jail → library","stop",anchor="end",dx=-13,dy=4,r=7))
b.append(marker(P,46.8135,-71.2033,"Place Royale","Champlain, 1608","hi",dx=62,dy=-46,lead=True))
b.append(marker(P,46.8123,-71.2028,"Petit-Champlain","Escalier Casse-Cou","stop",dx=54,dy=14,r=7,lead=True))
b.append(marker(P,46.8145,-71.2013,"Musée de la civilisation","closed Mondays","stop",dx=29,dy=-66,r=7,lead=True))
b.append(marker(P,46.8135,-71.2003,"Lévis ferry","C$4.25 · sunset","ev",dx=12,dy=0,lead=True))
frag['quebec']=wrap('quebec',''.join(b),
 '<span><i class="lg base"></i>Your base</span><span><i class="lg hi"></i>Marquee</span>'
 '<span><i class="lg ev"></i>Evening</span><span><i class="lg ln wk"></i>Day 6 walking route</span>',
 'The dotted line is the whole of Day 6, in order — walls, Citadelle, Plains, cathedral, Dufferin Terrace, down the Breakneck Steps, out on the ferry. Under four miles.',
 'https://www.google.com/maps/dir/Porte+Saint-Louis,+Quebec+City/Citadelle+of+Quebec/Plains+of+Abraham/Ch%C3%A2teau+Frontenac/Place+Royale,+Quebec+City/Quebec+City+ferry+terminal')

# ---------------- BEAUPRE ----------------
P,m=mk('beaupre')
b=[]
b.append(route(P,[(46.8135,-71.2160),(46.8500,-71.1800),(46.8905,-71.1475),(46.9200,-71.1000),(46.9600,-71.0200),(47.0000,-70.9600),(47.0225,-70.9310),(47.0450,-70.8800),(47.0570,-70.8560)]))
b.append(route(P,[(46.8930,-71.1450),(46.8700,-71.1420),(46.8530,-71.1370),(46.8570,-71.0900),(46.8620,-71.0250),(46.8900,-70.9500),(46.9150,-70.9050),(46.9550,-70.8400),(46.9700,-70.8600),(46.9600,-70.9600),(46.9300,-71.0300),(46.9060,-71.0790),(46.8930,-71.1450)],"loop",w=5))
b.append(marker(P,46.8135,-71.2160,"Québec City","your base","base",anchor="end",dy=4,r=11))
b.append(marker(P,46.8905,-71.1475,"Montmorency Falls","83 m · taller than Niagara","hi",anchor="end",dy=-6,r=11))
b.append(marker(P,46.8530,-71.1370,"Sainte-Pétronille","best view back to the city","stop",anchor="end",dy=8))
b.append(marker(P,46.9060,-71.0790,"Cassis Monna & Filles","","stop",anchor="end",dy=-2,r=7))
b.append(marker(P,46.9611,-70.9586,"Sainte-Famille","1743 church","stop",anchor="end",dy=-2,r=7))
b.append(marker(P,46.9145,-70.9036,"Saint-Jean","Manoir Mauvide-Genest, 1734","stop",dy=8,r=7))
b.append(marker(P,47.0225,-70.9310,"Sainte-Anne-de-Beaupré","1 M pilgrims a year","hi",dy=-6,r=11))
b.append(marker(P,47.0570,-70.8560,"Canyon Sainte-Anne","74 m falls · 3 bridges","stop",dy=6))
frag['beaupre']=wrap('beaupre',''.join(b),
 '<span><i class="lg base"></i>Base</span><span><i class="lg hi"></i>Marquee</span>'
 '<span><i class="lg ln"></i>Route 138 out</span><span><i class="lg ln lp"></i>Chemin Royal, 67 km</span>',
 'Day 7 in one picture: out along the Côte-de-Beaupré on Route 138, then the island loop anticlockwise, finishing at Sainte-Pétronille for sunset.',
 'https://www.google.com/maps/dir/Quebec+City/Montmorency+Falls/Basilica+of+Sainte-Anne-de-Beaupr%C3%A9/Canyon+Sainte-Anne/Sainte-P%C3%A9tronille,+QC')

# ---------------- CHARLEVOIX ----------------
P,m=mk('charlevoix')
b=[]
b.append(route(P,[(47.443,-70.501),(47.520,-70.420),(47.600,-70.290),(47.653,-70.152),(47.760,-70.010),(47.900,-69.870),(48.020,-69.790),(48.107,-69.731)]))
b.append(route(P,[(47.443,-70.501),(47.483,-70.343),(47.530,-70.270),(47.573,-70.212),(47.620,-70.175),(47.653,-70.152)],"scenic",w=7))
b.append(dash('spur',P,[(47.653,-70.152),(47.720,-70.270),(47.790,-70.370),(47.868,-70.421)],6))
b.append(marker(P,47.443,-70.501,"Baie-Saint-Paul","nights 10–11","base",anchor="end",dy=16,r=12))
b.append(marker(P,47.483,-70.343,"Les Éboulements","centre of the crater","stop",anchor="end",dy=-16))
b.append(marker(P,47.573,-70.212,"Saint-Irénée","beach · Domaine Forget","stop",anchor="end",dy=-14,r=7))
b.append(marker(P,47.653,-70.152,"La Malbaie","Manoir Richelieu","stop",dy=4))
b.append(marker(P,47.868,-70.421,"Hautes-Gorges","800 m walls · Acropole","hi",anchor="end",dy=-6,r=12))
b.append(marker(P,48.107,-69.731,"Baie-Ste-Catherine","whale cruises, 10:15 a.m.","ev",anchor="end",dy=12,r=11))
b.append(marker(P,48.1391,-69.7194,"Tadoussac","free ferry, 10 min","stop",dy=-6))
frag['charlevoix']=wrap('charlevoix',''.join(b),
 '<span><i class="lg base"></i>Your base</span><span><i class="lg hi"></i>Hautes-Gorges</span>'
 '<span><i class="lg ev"></i>Whales</span><span><i class="lg ln"></i>Rte 138 out</span><span><i class="lg ln sc"></i>Rte 362 back</span>',
 'Day 9 goes out on Route 138 in the morning and comes back on Route 362 — the balcony road — in the evening light. Day 10 is the gold spur up to the gorge.',
 'https://www.google.com/maps/dir/Baie-Saint-Paul,+QC/Baie-Sainte-Catherine,+QC/La+Malbaie,+QC/Les+%C3%89boulements,+QC/Baie-Saint-Paul,+QC')

for k,v in frag.items():
    open(OUT+'gmap_%s.html'%k,'w',encoding='utf-8').write(v)
    print('wrote',k,len(v),'bytes')
if UNSOURCED:
    print('\n!! %d markers have no places.json entry (using the literal in this file):'%len(UNSOURCED))
    for u in sorted(set(UNSOURCED)): print('   ',u)
    print('   run: python3 tools/resolve.py --seed && python3 tools/resolve.py --write')
