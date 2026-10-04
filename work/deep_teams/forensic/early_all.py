import json, time, sys, calendar, urllib.request, os
BUDGET=float(sys.argv[1]); T=time.time()
tok=json.load(open('forensic/fleet_tokens.json'))
fn='forensic/early_all.json'; st=json.load(open(fn)) if os.path.exists(fn) else {}
def ts(x): return calendar.timegm(time.strptime(x["timestamp"][:19],"%Y-%m-%dT%H:%M:%S"))
for m,v in sorted(tok.items(), key=lambda kv:-kv[1]['t']):
    if m in st: continue
    if time.time()-T>BUDGET: break
    u=f"https://swap-api.pump.fun/v2/coins/{m}/trades?limit=100&cursor=0-{(v['t']+61)*1000}"
    d={}
    for k in range(6):
        try: d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"Mozilla/5.0"}),timeout=30)); break
        except Exception: time.sleep(4+3*k)
    time.sleep(0.95)
    st[m]=[[x['userAddress'],round(float(x['amountSol'] or 0),4),ts(x)-v['t'],int(x['slotIndexId'][:12])] for x in (d.get('trades') or []) if x['type']=='buy' and x['userAddress']!=v['dev']]
    if len(st)%50==0: json.dump(st,open(fn,'w'))
json.dump(st,open(fn,'w')); print('done',len(st),'of',len(tok),file=sys.stderr)
