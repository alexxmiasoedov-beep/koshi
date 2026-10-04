import json, time, sys, os, collections, chain as C
from concurrent.futures import ThreadPoolExecutor
HUB="Cc3bpPzUvgAzdW9Nv7dUQ8cpap8Xa7ujJgLdpqGrTCu6"; HOURS=float(sys.argv[1]); BUDGET=float(sys.argv[2]); T=time.time()
fn='forensic/hubscan.json'; st=json.load(open(fn)) if os.path.exists(fn) else {}
if 'sigs' not in st:
    s=C.sigs_since(HUB,int(time.time()-HOURS*3600),max_pages=15)
    st={'sigs':[x['signature'] for x in s if not x['err']],'pay':{}}
    json.dump(st,open(fn,'w'))
todo=[x for x in st['sigs'] if x not in st['pay']]
print('sigs',len(st['sigs']),'todo',len(todo),file=sys.stderr)
with ThreadPoolExecutor(6) as ex:
    for sig,t in zip(todo,ex.map(C.tx,todo)):
        if t: st['pay'][sig]=[[b,round(sol,4),t['blockTime']] for a,b,sol in C.sol_transfers(t) if a==HUB]
        if time.time()-T>BUDGET: break
json.dump(st,open(fn,'w'))
print('parsed',len(st['pay']),file=sys.stderr)
