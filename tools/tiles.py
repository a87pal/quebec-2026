# -*- coding: utf-8 -*-
import math, os, urllib.request, time, json, html
HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.dirname(HERE)
DEST=os.path.join(ROOT,'images','tiles')
# tilemeta.json is the contract with overlay.py - it MUST land where overlay reads it.
OUT=os.environ.get('MAPOUT', HERE+'/')
os.makedirs(DEST,exist_ok=True)
H={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36'}
TPL="https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}"

def px(lat,lon,z):
    n=2**z
    x=(lon+180.0)/360.0*n*256
    lr=math.radians(lat)
    y=(1.0-math.log(math.tan(lr)+1/math.cos(lr))/math.pi)/2.0*n*256
    return x,y

MAPS={
 'route':      dict(z=8,  lat=(41.10,48.60), lon=(-76.60,-67.40)),
 'franconia':  dict(z=13, lat=(44.015,44.205), lon=(-71.760,-71.590)),
 'montreal':   dict(z=13, lat=(45.462,45.578), lon=(-73.665,-73.495)),
 'quebec':     dict(z=15, lat=(46.7955,46.8235), lon=(-71.2400,-71.1855)),
 'beaupre':    dict(z=12, lat=(46.795,47.095), lon=(-71.290,-70.775)),
 'charlevoix': dict(z=10, lat=(47.330,48.230), lon=(-70.760,-69.560)),
}
meta={}
for name,cfg in MAPS.items():
    z=cfg['z']
    x0,y1=px(cfg['lat'][0],cfg['lon'][0],z)   # SW -> min x, max y
    x1,y0=px(cfg['lat'][1],cfg['lon'][1],z)   # NE -> max x, min y
    tx0,tx1=int(x0//256), int(x1//256)
    ty0,ty1=int(y0//256), int(y1//256)
    nw,nh=tx1-tx0+1, ty1-ty0+1
    meta[name]=dict(z=z,tx0=tx0,tx1=tx1,ty0=ty0,ty1=ty1,W=nw*256,H=nh*256,
                    ox=tx0*256,oy=ty0*256)
    print(name,'z',z,'tiles',nw,'x',nh,'=',nw*nh,'  px',nw*256,'x',nh*256)
json.dump(meta,open(OUT+'tilemeta.json','w'))
total=sum((m['tx1']-m['tx0']+1)*(m['ty1']-m['ty0']+1) for m in meta.values())
print('TOTAL TILES',total)

got=0;fail=0
for name,m in meta.items():
    d=os.path.join(DEST,name); os.makedirs(d,exist_ok=True)
    for tx in range(m['tx0'],m['tx1']+1):
        for ty in range(m['ty0'],m['ty1']+1):
            f=os.path.join(d,'%d_%d.jpg'%(tx,ty))
            if os.path.exists(f) and os.path.getsize(f)>1500: got+=1; continue
            u=TPL.format(z=m['z'],x=tx,y=ty)
            ok=False
            for a in range(3):
                try:
                    b=urllib.request.urlopen(urllib.request.Request(u,headers=H),timeout=30).read()
                    open(f,'wb').write(b); ok=True; got+=1; break
                except Exception as e:
                    time.sleep(2+a*3)
            if not ok: fail+=1; print('FAIL',name,tx,ty)
            time.sleep(0.12)
    print('done',name)
print('tiles ok',got,'failed',fail)
