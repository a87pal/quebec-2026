import io,re,sys
def boxes(name):
    s=io.open("gmap_%s.html"%name,encoding="utf-8").read()
    out=[]
    for g in re.finditer(r'<g class="mk ([a-z]+)">(?:<path class="ldr"[^>]*/>)?<circle cx="([\d.]+)" cy="([\d.]+)" r="([\d.]+)".*?<text class="ml" x="([\d.]+)" y="([\d.]+)" text-anchor="(\w+)" font-size="([\d.]+)"[^>]*>([^<]+)</text>(?:<text class="ms" x="[\d.]+" y="([\d.]+)"[^>]*>([^<]*)</text>)?',s):
        kind,cx,cy,r,lx,ly,anc,fs,lab,sy,sub=g.groups()
        cx,cy,lx,ly,fs=float(cx),float(cy),float(lx),float(ly),float(fs)
        w=len(lab)*fs*0.56
        if sub: w=max(w,len(sub)*fs*0.75*0.56)
        x0=lx if anc=="start" else lx-w
        y0=ly-fs*0.8; y1=(float(sy) if sy else ly)+fs*0.4
        out.append(dict(lab=lab,cx=cx,cy=cy,r=float(r),x0=x0,x1=x0+w,y0=y0,y1=y1))
    return out
def ov(a,b):
    dx=min(a['x1'],b['x1'])-max(a['x0'],b['x0']); dy=min(a['y1'],b['y1'])-max(a['y0'],b['y0'])
    return dx if (dx>0 and dy>0) else 0, dy if (dx>0 and dy>0) else 0
for n in ("route","franconia","montreal","quebec","beaupre","charlevoix"):
    bs=boxes(n); bad=[]
    for i in range(len(bs)):
        for j in range(i+1,len(bs)):
            dx,dy=ov(bs[i],bs[j])
            if dx>4 and dy>4: bad.append((bs[i]['lab'],bs[j]['lab'],round(dx),round(dy)))
    # label boxes sitting on another marker's dot
    dot=[]
    for b in bs:
        for c in bs:
            if b is c: continue
            if b['x0']-4<c['cx']<b['x1']+4 and b['y0']-4<c['cy']<b['y1']+4:
                dot.append((b['lab'],'covers dot of',c['lab']))
    print("== %-11s markers=%d  label-overlaps=%d  dot-covers=%d"%(n,len(bs),len(bad),len(dot)))
    for x in bad: print("     OVERLAP %-26s x %-26s (%dx%d px)"%x)
    for x in dot: print("     DOTHIT  %-26s %s %s"%x)
