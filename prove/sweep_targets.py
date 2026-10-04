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
USDG = "0x5fc5360D0400a0Fd4f2af552ADD042D716F1d168"  # 6 decimals (CLAUDE.md verified fact)
BALANCE_OF = "0x70a08231"  # balanceOf(address) selector
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


def _rpc_batch(calls: list[dict], timeout: int = 40):
    body = json.dumps(calls)
    return json.loads(_curl(["-X", "POST", RH_RPC, "-H", "content-type: application/json",
                             "--data", body], timeout))


def enumerate_verified() -> list[dict]:
    """Every verified 4663 contract, newest first, paged by matchId cursor."""
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
        print(f"  ...enumerated {len(out)}", file=sys.stderr, flush=True)
        if len(page) < 200:
            break
        time.sleep(0.2)
    return out


def eth_price() -> float:
    try:
        return float(_get_json(ETH_PRICE_URL)["data"]["amount"])
    except Exception:
        return 0.0


def balances(addresses: list[str]) -> dict[str, dict]:
    """ETH wei and USDG (6dp) for each address, read in RPC batches at latest block."""
    out: dict[str, dict] = {}
    CHUNK = 50
    for i in range(0, len(addresses), CHUNK):
        chunk = addresses[i : i + CHUNK]
        calls = []
        for j, a in enumerate(chunk):
            calls.append({"jsonrpc": "2.0", "id": f"e{i+j}", "method": "eth_getBalance", "params": [a, "latest"]})
            data = BALANCE_OF + a[2:].rjust(64, "0").lower()
            calls.append({"jsonrpc": "2.0", "id": f"u{i+j}", "method": "eth_call",
                          "params": [{"to": USDG, "data": data}, "latest"]})
        resp = {r["id"]: r.get("result", "0x0") for r in _rpc_batch(calls)}
        for j, a in enumerate(chunk):
            eth_wei = int(resp.get(f"e{i+j}", "0x0") or "0x0", 16)
            raw = resp.get(f"u{i+j}", "0x0") or "0x0"
            usdg = int(raw, 16) / 1e6 if raw not in ("0x", "0x0") else 0.0
            out[a] = {"eth_wei": eth_wei, "usdg": usdg}
        print(f"  ...balances {min(i+CHUNK, len(addresses))}/{len(addresses)}", file=sys.stderr, flush=True)
        time.sleep(0.2)
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
