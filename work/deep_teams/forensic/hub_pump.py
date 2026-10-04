import json, time, sys, os, urllib.request
BUDGET=float(sys.argv[1]); T=time.time()
rc=json.load(open('forensic/hub_recips.json'))
fn='forensic/hub_pump.json'; st=json.load(open(fn)) if os.path.exists(fn) else {}
for b in rc:
    if b in st: continue
    if time.time()-T>BUDGET: break
    d=None
    for k in range(5):
        try: d=json.load(urllib.request.urlopen(urllib.request.Request(f"https://frontend-api-v3.pump.fun/coins?creator={b}&limit=50&offset=0&sort=created_timestamp&order=DESC&includeNsfw=true",headers={"User-Agent":"Mozilla/5.0"}),timeout=30)); break
        except Exception: time.sleep(6)
    time.sleep(1.02)
    st[b]=[[x['mint'],x['symbol'],x['created_timestamp']//1000,x.get('ath_market_cap')] for x in (d or [])]
    if len(st)%40==0: json.dump(st,open(fn,'w'))
json.dump(st,open(fn,'w')); print('checked',len(st),'of',len(rc),'with tokens',sum(1 for v in st.values() if v),file=sys.stderr)
