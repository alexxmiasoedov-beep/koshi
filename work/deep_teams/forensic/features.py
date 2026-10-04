"""Извлечение «цифровых следов» из транзакций кошелька.
feats(addr, tx) -> list of (kind, value) — значения, по которым можно связать кошельки."""
import collections, chain as C

CB = "ComputeBudget111111111111111111111111111111"
JITO = {"96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5", "HFqU5x63VTqvQss8hp11i4wVV8bD44PvwucfZ2bU7gRe",
        "Cw8CFyM9FkoMi7K7Crf6HNQqf4uEMzpKw6QNghXLvLkY", "ADaUMid9yfUytqMBgopwjb2DTLSokTSzL1zt6iGPaS49",
        "DfXygSm4jCyNCybVYYK6DwvWqjKee8pbDmJGcLWNDXjh", "ADuUkR4vqLUMWXxW9gh6D6L8pMSawimctcNZ5pGwDcEt",
        "DttWaMuVvTiduZRnguLF7jNxTgiMBZ1hyAumKUiL2KRL", "3AVi9Tg9Uo68tJfuvoKvqKNWKkC5wPdSSdeBnizKZ6jT"}


def feats(addr, t):
    out = []
    msg = t["transaction"]["message"]
    keys = msg["accountKeys"]
    ks = [k["pubkey"] if isinstance(k, dict) else k for k in keys]
    signers = [k["pubkey"] for k in keys if isinstance(k, dict) and k.get("signer")]
    if addr not in signers:
        return out  # интересуют только транзакции, подписанные самим кошельком
    payer = ks[0]
    if payer != addr: out.append(("fee_payer", payer))
    for s in signers:
        if s not in (addr, payer): out.append(("cosigner", s))
    for l in msg.get("addressTableLookups") or []:
        out.append(("alt", l["accountKey"]))
    for ix in C.all_ix(t):
        p = ix.get("parsed"); prog = ix.get("program")
        if isinstance(p, dict):
            ty = p.get("type"); info = p.get("info", {})
            if prog in ("spl-token", "spl-token-2022") and ty == "closeAccount":
                if info.get("owner") == addr and info.get("destination") != addr:
                    out.append(("close_dest", info.get("destination")))
            if prog == "system" and ty == "advanceNonce":
                out.append(("nonce", info.get("nonceAccount"))); out.append(("nonce_auth", info.get("nonceAuthority")))
            if prog == "system" and ty in ("createAccountWithSeed", "transferWithSeed"):
                out.append(("seed_base", info.get("base")))
            if prog == "spl-memo" or ix.get("programId", "").startswith("Memo"):
                out.append(("memo", str(p)[:80]))
            if prog in ("spl-token", "spl-token-2022") and ty in ("transfer", "transferChecked"):
                if info.get("authority") == addr or info.get("multisigAuthority") == addr:
                    out.append(("token_out_to_acct", info.get("destination")))
    # мелкие SOL-переводы от кошелька в торговых tx = комиссии ботов/рефералы
    logs = " ".join(t["meta"].get("logMessages") or [])
    trading = ("Instruction: Buy" in logs) or ("Instruction: Sell" in logs) or ("Instruction: Swap" in logs)
    for a, b, sol in C.sol_transfers(t):
        if a != addr or b == addr: continue
        if b in JITO: out.append(("jito_tip_lamports", int(round(sol * 1e9))))
        elif trading and sol < 0.05: out.append(("trade_fee_dest", b))
    # создательская комиссия pump: куда уходит
    if "CollectCreatorFee" in logs or "collect_creator_fee" in logs:
        for a, b, sol in C.sol_transfers(t):
            if b != addr: out.append(("creator_fee_dest", b))
        out.append(("collects_creator_fee", 1))
    # точные параметры ComputeBudget
    for ix in msg["instructions"]:
        if ix.get("programId") == CB and ix.get("data"):
            out.append(("cb_data", ix["data"]))
    return out
