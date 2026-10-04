import json, time, sys, os, random, chain as C, features as Fz
from concurrent.futures import ThreadPoolExecutor
name=sys.argv[1]; addrs=json.load(open(sys.argv[2])); N=int(sys.argv[3]); BUDGET=float(sys.argv[4]); T=time.time()
fn=f'forensic/prof_{name}.json'; st=json.load(open(fn)) if os.path.exists(fn) else {}
for a in addrs:
    if a in st and st[a].get('done'): continue
    if time.time()-T>BUDGET: break
    s=C.sigs_since(a,0,max_pages=1); ok=[x['signature'] for x in s if not x['err']][:N]
    with ThreadPoolExecutor(6) as ex: txs=[t for t in ex.map(C.tx,ok) if t]
    feats={}
    for t in txs:
        for k,v in Fz.feats(a,t): feats[f"{k}={v}"]=feats.get(f"{k}={v}",0)+1
    st[a]={'done':True,'n':len(txs),'feats':feats}
    json.dump(st,open(fn,'w'))
print(name,'profiled',sum(1 for v in st.values() if v.get('done')),'of',len(addrs),file=sys.stderr)
