import json, collections, time, os, sys, chain as C
from concurrent.futures import ThreadPoolExecutor
BUDGET=float(sys.argv[1]); T=time.time()
fleet=json.load(open('forensic/fleet.json')); idx=json.load(open('forensic/sigidx.json'))
fn='forensic/orders_state.json'
st=json.load(open(fn)) if os.path.exists(fn) else {}
if 'rcpt' not in st:
    rcpt={}
    for a in fleet:
        for s in idx.get(a,[]):
            t=C.tx(s)
            if not t: continue
            for x,y,sol in C.sol_transfers(t):
                if x==a and y!=a and 0.05<=sol<=20:
                    r=rcpt.setdefault(y,{"sol":0.0,"from":[],"t":0}); r["sol"]+=sol; r["t"]=max(r["t"],t["blockTime"])
                    if a[:6] not in r["from"]: r["from"].append(a[:6])
    addrs=[a for a in rcpt if a not in fleet]; own={}
    for i in range(0,len(addrs),100):
        for k in range(8):
            try: v=C.post(C.MAIN,{"jsonrpc":"2.0","id":1,"method":"getMultipleAccounts","params":[addrs[i:i+100],{"encoding":"base64","dataSlice":{"offset":0,"length":0}}]})['result']['value']; break
            except Exception: time.sleep(3)
        for a,x in zip(addrs[i:i+100],v): own[a]=x['owner'] if x else None
        time.sleep(0.4)
    st={'rcpt':{a:rcpt[a] for a in addrs if own.get(a) in (C.SYSTEM,None)},'checked':{}}
    json.dump(st,open(fn,'w'))
print('wallet recipients',len(st['rcpt']),'checked',len(st['checked']),file=sys.stderr)
def chk(a):
    for k in range(6):
        try: s=C.post(C.MAIN,{"jsonrpc":"2.0","id":1,"method":"getSignaturesForAddress","params":[a,{"limit":6}]})['result']; break
        except Exception: time.sleep(2+k)
    else: return a,None
    hit=0
    for x in [x for x in s if not x['err']][:3]:
        t=C.tx(x['signature'])
        if t and any(i.get('programId','').startswith('MAyhSmzX') for i in C.all_ix(t)): hit+=1
    return a,hit
todo=[a for a in st['rcpt'] if a not in st['checked']]
with ThreadPoolExecutor(3) as ex:
    for a,h in ex.map(chk,todo):
        if h is not None: st['checked'][a]=h
        if time.time()-T>BUDGET: break
json.dump(st,open(fn,'w'))
orders=[a for a,h in st['checked'].items() if h]
print('checked',len(st['checked']),'/',len(st['rcpt']),'orders',len(orders),file=sys.stderr)
