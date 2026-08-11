#!/usr/bin/env python3
import io, re, collections
NEW="/Users/anand.palaniappan1/src/qubec/quebec-v3.html"
OLD="/private/tmp/claude-502/-Users-anand-palaniappan1-src-qubec/8705e06a-a0af-496c-a5b3-429a9ac323b5/scratchpad/quebec-v3.bak2.html"
new=io.open(NEW,encoding="utf-8").read(); old=io.open(OLD,encoding="utf-8").read()

print("=== tag balance ===")
bad=0
for tag in ("section","div","details","summary","article","table","tbody","thead","ul","ol","li","p","span","a","h2","h3","h4","h5","td","tr","th","main","svg","g","text","nav","button"):
    o=len(re.findall(r"<%s[\s>]"%tag,new)); c=len(re.findall(r"</%s>"%tag,new))
    if o!=c: print("  UNBALANCED %-8s open=%d close=%d"%(tag,o,c)); bad+=1
print("  all balanced" if not bad else "  %d unbalanced"%bad)

print("\n=== outline ===")
for m in re.finditer(r'<section class="part[^"]*" id="([^"]+)">|<h2>(.*?)</h2>|<div class="subsec" id="([^"]+)">|<h3>(.*?)</h3>',new):
    if m.group(1): print("PART  #%s"%m.group(1))
    elif m.group(2): print("  h2   %s"%m.group(2)[:70])
    elif m.group(3): print("  SUB  #%s"%m.group(3))
    elif m.group(4): print("    h3 %s"%m.group(4)[:70])

print("\n=== nav ===")
nav=re.search(r"<nav>\n(.*?)\n</nav>",new,re.S).group(1)
print("  ",re.findall(r'href="#([^"]+)">([^<]+)<',nav))
miss=[h for h,_ in re.findall(r'href="#([^"]+)">([^<]+)<',nav) if ('id="%s"'%h) not in new]
print("   unresolved:",miss or "none")

print("\n=== all internal links resolve ===")
miss=sorted({h for h in re.findall(r'href="#([^"]+)"',new) if ('id="%s"'%h) not in new})
print("   ",miss or "all resolve")

print("\n=== days ===")
print("   collapsed day details:",len(re.findall(r'<details class="day dayd" id="day-',new)))
print("   leftover <article id=\"day-:",len(re.findall(r'<article id="day-',new)))
print("   day-by-day table drawer:", 'id="daytable"' in new)
print("   open-by-default details:", len(re.findall(r'<details[^>]*\sopen',new)))

print("\n=== duplicate ids ===")
d=[k for k,v in collections.Counter(re.findall(r'\sid="([^"]+)"',new)).items() if v>1]
print("   ",d or "none")

print("\n=== drawer order in reservations ===")
res=new[new.index('id="reservations"'):]
res=res[:res.index("</section>")+400]
print("   ",re.findall(r'<details class="l1" id="([^"]+)">',res))

print("\n=== content preserved ===")
def textof(t):
    t=re.sub(r"<script.*?</script>","",t,flags=re.S); t=re.sub(r"<style.*?</style>","",t,flags=re.S)
    return re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",t)).strip()
o,n=textof(old),textof(new)
os_=set(s.strip() for s in re.split(r"(?<=[.!?]) ",o) if len(s.strip())>40)
ns_=set(s.strip() for s in re.split(r"(?<=[.!?]) ",n) if len(s.strip())>40)
lost=sorted(os_-ns_)
print("   old %d / new %d / dropped %d"%(len(os_),len(ns_),len(lost)))
for s in lost[:25]: print("     - "+s[:140])
