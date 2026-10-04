"""История транзакций флота (до N последних успешных tx на кошелёк) в кэш."""
import json, sys, time, chain as C
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0,'.')
N=int(sys.argv[1]); BUDGET=float(sys.argv[2]); T=time.time()
fleet=json.load(open('forensic/fleet.json'))
idx=json.load(open('forensic/sigidx.json')) if __import__('os').path.exists('forensic/sigidx.json') else {}
for a in fleet:
    if a not in idx:
        s=C.sigs_since(a,0,max_pages=max(1,N//1000+1))
        idx[a]=[x['signature'] for x in s if not x['err']][:N]
        json.dump(idx,open('forensic/sigidx.json','w'))
allsig=[s for a in fleet for s in idx[a]]
import os
todo=[s for s in allsig if not os.path.exists(os.path.join(C.CACHE,s[:2],s+'.json'))]
print('total',len(allsig),'todo',len(todo),file=sys.stderr)
with ThreadPoolExecutor(6) as ex:
    for i,_ in enumerate(ex.map(C.tx,todo)):
        if time.time()-T>BUDGET: break
left=sum(1 for s in allsig if not os.path.exists(os.path.join(C.CACHE,s[:2],s+'.json')))
print('left',left,file=sys.stderr)
