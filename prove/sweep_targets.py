"""Phase 0 of the 10-05 sweep: list verified Robinhood Chain (4663) contracts that hold money.

    python prove/sweep_targets.py [--min-usd 10000] [--out prove/sweep-targets.json]

Robinhood Chain's Blockscout is Cloudflare-gated, but Sourcify's listing API serves chain 4663, so the
set of verified contracts is enumerable after all. For each one we read its ETH (gas token) and USDG
balance at the latest block over the public RPC and keep the ones worth chasing. No model runs here;
this only decides what the paid prove pass (Phase 3) would point at.

Money proxy: ETH + USDG only. Other tokens are not counted, so a contract can hold more than we see;
the number we publish is a floor, never inflated. Needs network; no API key.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

SOURCIFY = "https://sourcify.dev/server/v2/contracts/4663"
RH_RPC = "https://rpc.mainnet.chain.robinhood.com"
VERIFIED_CKPT = Path("prove/.verified-4663.json")   # enumeration, so it runs once
BAL_CKPT = Path("prove/.balances-4663.json")         # partial balances, so a long read resumes
USDG = "0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168"  # 6 decimals (CLAUDE.md verified fact)
BALANCE_OF = "0x70a08231"   # balanceOf(address)
GET_ETH_BAL = "0x4d2301cc"  # Multicall3.getEthBalance(address)
MULTICALL3 = "0xcA11bde05977b3631167028862bE2a173976CA11"  # canonical, confirmed deployed on 4663
MC3_ABI = [{"inputs": [{"components": [{"name": "target", "type": "address"},
            {"name": "allowFailure", "type": "bool"}, {"name": "callData", "type": "bytes"}],
            "name": "calls", "type": "tuple[]"}], "name": "aggregate3",
            "outputs": [{"components": [{"name": "success", "type": "bool"},
            {"name": "returnData", "type": "bytes"}], "name": "r", "type": "tuple[]"}],
            "stateMutability": "payable", "type": "function"}]
ETH_PRICE_URL = "https://api.coinbase.com/v2/prices/ETH-USD/spot"


def _curl(args: list[str], timeout: int = 60) -> str:
    """Shell out to curl (urllib's TLS is flaky against these hosts here). Retries transient drops."""
    err = ""
    for attempt in range(4):
        p = subprocess.run(["curl", "-s", "--max-time", str(timeout), *args],
                           capture_output=True, text=True)
        if p.returncode == 0 and p.stdout.strip():
            return p.stdout
        err = p.stderr.strip()[:120]
        time.sleep(1 + attempt)
    raise RuntimeError(f"curl failed after retries: {args[-1]} ({err})")


def _get_json(url: str, timeout: int = 30):
    return json.loads(_curl(["-H", "accept: application/json", url], timeout))


def _mc3():
    from web3 import Web3
    w3 = Web3(Web3.HTTPProvider(RH_RPC))
    return w3, w3.eth.contract(address=Web3.to_checksum_address(MULTICALL3), abi=MC3_ABI)


def enumerate_verified() -> list[dict]:
    """Every verified 4663 contract, newest first, paged by matchId cursor. Checkpointed so it runs once."""
    if VERIFIED_CKPT.exists():
        done = json.loads(VERIFIED_CKPT.read_text())
        if done.get("complete"):
            print(f"  enumeration from checkpoint: {len(done['items'])}", file=sys.stderr)
            return done["items"]
        out, cursor = done["items"], done["cursor"]      # resume
    else:
        out, cursor = [], None
    while True:
        url = f"{SOURCIFY}?limit=200&sort=desc"
        if cursor:
            url += f"&afterMatchId={cursor}"
        page = _get_json(url).get("results", [])
        if not page:
            break
        out.extend(page)
        cursor = page[-1]["matchId"]
        if len(out) % 5000 < 200:
            VERIFIED_CKPT.write_text(json.dumps({"complete": False, "cursor": cursor, "items": out}))
            print(f"  ...enumerated {len(out)}", file=sys.stderr, flush=True)
        if len(page) < 200:
            break
        time.sleep(0.15)
    VERIFIED_CKPT.write_text(json.dumps({"complete": True, "cursor": cursor, "items": out}))
    print(f"  enumeration complete: {len(out)}", file=sys.stderr, flush=True)
    return out


def eth_price() -> float:
    try:
        return float(_get_json(ETH_PRICE_URL)["data"]["amount"])
    except Exception:
        return 0.0


def _calldata(selector: str, addr: str) -> bytes:
    return bytes.fromhex(selector[2:] + addr[2:].rjust(64, "0"))


def balances(addresses: list[str]) -> dict[str, dict]:
    """ETH wei and USDG (6dp) per address, via one Multicall3 aggregate3 per chunk. Resumable.

    The public RPC 429s on JSON-RPC batches past ~50, but Multicall3 folds hundreds of reads into a
    single eth_call, so the whole chain is a few hundred requests instead of a few thousand.
    """
    from web3 import Web3
    out: dict[str, dict] = json.loads(BAL_CKPT.read_text()) if BAL_CKPT.exists() else {}
    todo = [a for a in addresses if a not in out]
    print(f"  balances: {len(out)} cached, {len(todo)} to read", file=sys.stderr, flush=True)
    _, mc3 = _mc3()
    usdg = Web3.to_checksum_address(USDG)
    mc3addr = Web3.to_checksum_address(MULTICALL3)
    CHUNK = 250
    for i in range(0, len(todo), CHUNK):
        chunk = todo[i : i + CHUNK]
        calls = []
        for a in chunk:
            ca = Web3.to_checksum_address(a)
            calls.append((mc3addr, True, _calldata(GET_ETH_BAL, ca)))
            calls.append((usdg, True, _calldata(BALANCE_OF, ca)))
        res = mc3.functions.aggregate3(calls).call()
        for j, a in enumerate(chunk):
            ok_e, ret_e = res[2 * j]
            ok_u, ret_u = res[2 * j + 1]
            eth_wei = int.from_bytes(ret_e, "big") if ok_e and len(ret_e) == 32 else 0
            usdg_raw = int.from_bytes(ret_u, "big") if ok_u and len(ret_u) == 32 else 0
            out[a] = {"eth_wei": eth_wei, "usdg": usdg_raw / 1e6}
        BAL_CKPT.write_text(json.dumps(out))
        print(f"  ...balances {min(i+CHUNK, len(todo))}/{len(todo)}", file=sys.stderr, flush=True)
        time.sleep(0.05)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-usd", type=float, default=10000.0)
    ap.add_argument("--out", default="prove/sweep-targets.json")
    args = ap.parse_args()

    verified = enumerate_verified()
    print(f"verified 4663 contracts (Sourcify): {len(verified)}", file=sys.stderr)
    # unique addresses, keep best match label
    seen: dict[str, dict] = {}
    for c in verified:
        a = c["address"]
        if a not in seen:
            seen[a] = {"address": a, "match": c.get("match"), "verifiedAt": c.get("verifiedAt")}
    addrs = list(seen)

    price = eth_price()
    print(f"ETH/USD: {price or 'unavailable'}", file=sys.stderr)
    bals = balances(addrs)

    rows = []
    for a in addrs:
        b = bals.get(a, {"eth_wei": 0, "usdg": 0.0})
        eth = b["eth_wei"] / 1e18
        usd = b["usdg"] + (eth * price if price else 0.0)
        rows.append({**seen[a], "chain": "robinhood", "eth": round(eth, 6),
                     "usdg": round(b["usdg"], 2), "usd": round(usd, 2)})
    rows.sort(key=lambda r: r["usd"], reverse=True)
    held = [r for r in rows if r["usd"] >= args.min_usd]

    out = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "chain": "robinhood (4663)",
        "eth_usd": price,
        "money_proxy": "ETH + USDG only (floor; other tokens not counted)",
        "min_usd": args.min_usd,
        "verified_total": len(addrs),
        "money_holding": len(held),
        "targets": held,
        "all_ranked": rows,
    }
    Path(args.out).write_text(json.dumps(out, indent=2))
    print(f"money-holding (>= ${args.min_usd:,.0f}): {len(held)} of {len(addrs)} verified", file=sys.stderr)
    for r in held[:15]:
        print(f"  ${r['usd']:>12,.0f}  {r['address']}  (usdg {r['usdg']:,.0f}, eth {r['eth']})", file=sys.stderr)
    print(f"written: {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
