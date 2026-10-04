"""Общие on-chain утилиты для глубокого анализа: подписи адреса, транзакции (с дисковым кэшем),
разбор SOL-переводов и токен-движений по кошельку."""
import json, os, time, random, threading, hashlib
import urllib.request, urllib.error

D = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(D, "txcache"); os.makedirs(CACHE, exist_ok=True)
MAIN = "https://api.mainnet-beta.solana.com"
TX_RPCS = ["https://public.rpc.solanavibestation.com"] * 3 + ["https://solana.api.pocket.network", MAIN]
WSOL = "So11111111111111111111111111111111111111112"
PUMP = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMP_AMM = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
SYSTEM = "11111111111111111111111111111111"
_lk = threading.Lock(); _rr = [0]


def post(url, body, timeout=40):
    req = urllib.request.Request(url, json.dumps(body).encode(),
                                 {"content-type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def sigs(addr, limit_pages=50, until_ts=None):
    """Все подписи адреса (новые -> старые). Кэш на диске."""
    fn = os.path.join(CACHE, f"sigs_{addr}.json")
    if os.path.exists(fn):
        return json.load(open(fn))
    out, before = [], None
    for _ in range(limit_pages):
        opt = {"limit": 1000}
        if before: opt["before"] = before
        page = None
        for i in range(12):
            try:
                d = post(MAIN, {"jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress", "params": [addr, opt]})
                if "result" in d: page = d["result"]; break
            except Exception:
                pass
            time.sleep(1.5 + i)
        if page is None: raise RuntimeError("sigs " + addr)
        out += [{"sig": s["signature"], "t": s["blockTime"], "slot": s["slot"], "err": bool(s["err"])} for s in page]
        if len(page) < 1000 or (until_ts and page[-1]["blockTime"] and page[-1]["blockTime"] < until_ts): break
        before = page[-1]["signature"]
    json.dump(out, open(fn, "w"))
    return out


def tx(sig):
    fn = os.path.join(CACHE, sig[:2], sig + ".json")
    if os.path.exists(fn):
        return json.load(open(fn))
    for i in range(25):
        with _lk:
            url = TX_RPCS[_rr[0] % len(TX_RPCS)]; _rr[0] += 1
        try:
            d = post(url, {"jsonrpc": "2.0", "id": 1, "method": "getTransaction",
                           "params": [sig, {"maxSupportedTransactionVersion": 1, "encoding": "jsonParsed"}]})
            if d.get("result"):
                os.makedirs(os.path.dirname(fn), exist_ok=True)
                json.dump(d["result"], open(fn, "w"))
                return d["result"]
        except urllib.error.HTTPError:
            time.sleep(0.3 + 0.1 * i)
        except Exception:
            time.sleep(0.5)
    return None


def keys_of(t):
    return [k["pubkey"] if isinstance(k, dict) else k for k in t["transaction"]["message"]["accountKeys"]]


def all_ix(t):
    """Все инструкции (внешние + внутренние) в jsonParsed."""
    out = list(t["transaction"]["message"]["instructions"])
    for g in t["meta"].get("innerInstructions") or []:
        out += g["instructions"]
    return out


def sol_transfers(t):
    """Системные переводы SOL: [(from, to, sol)]."""
    res = []
    for ix in all_ix(t):
        p = ix.get("parsed")
        if ix.get("program") == "system" and isinstance(p, dict) and p.get("type") in ("transfer", "transferWithSeed"):
            i = p["info"]; res.append((i.get("source"), i.get("destination"), i.get("lamports", 0) / 1e9))
        if ix.get("program") == "system" and isinstance(p, dict) and p.get("type") == "createAccount":
            i = p["info"]; res.append((i.get("source"), i.get("newAccount"), i.get("lamports", 0) / 1e9))
    return res


def sol_delta(t, addr):
    ks = keys_of(t)
    if addr not in ks: return 0.0
    i = ks.index(addr)
    return (t["meta"]["postBalances"][i] - t["meta"]["preBalances"][i]) / 1e9


def token_deltas(t, owner):
    """Изменение токенов владельца: {mint: delta_ui}."""
    pre = {(b["mint"], b.get("owner")): float(b["uiTokenAmount"]["uiAmount"] or 0) for b in t["meta"].get("preTokenBalances") or []}
    post_ = {(b["mint"], b.get("owner")): float(b["uiTokenAmount"]["uiAmount"] or 0) for b in t["meta"].get("postTokenBalances") or []}
    out = {}
    for k in set(pre) | set(post_):
        if k[1] != owner: continue
        d = post_.get(k, 0) - pre.get(k, 0)
        if abs(d) > 0: out[k[0]] = d
    return out


def programs(t):
    return sorted({ix.get("programId") for ix in t["transaction"]["message"]["instructions"]})


def logs_has(t, s):
    return any(s in l for l in t["meta"].get("logMessages") or [])


def sigs_since(addr, since_ts, max_pages=8):
    """Свежие подписи адреса (без кэша) не старше since_ts, с повторами на 429."""
    out, before = [], None
    for _ in range(max_pages):
        opt = {"limit": 1000}
        if before: opt["before"] = before
        page = None
        for i in range(12):
            try:
                d = post(MAIN, {"jsonrpc": "2.0", "id": 1, "method": "getSignaturesForAddress", "params": [addr, opt]})
                if "result" in d: page = d["result"]; break
            except Exception:
                pass
            time.sleep(2 + i)
        if not page: break
        out += [s for s in page if s["blockTime"] and s["blockTime"] >= since_ts]
        if len(page) < 1000 or page[-1]["blockTime"] < since_ts: break
        before = page[-1]["signature"]
        time.sleep(0.5)
    return out
