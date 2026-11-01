"""Stage 3: replay a transaction on an anvil fork at the block before it and report what left
the watched addresses (ETH balance deltas and ERC-20 Transfer events out of them).

Usage:
  python3 -m watch.simulate --chain ethereum --tx 0x... --watchlist watch/seeds/x.json [--port 8551]

Needs `anvil` (Foundry) on PATH and an RPC that serves state at that block. A fork that can't
be built or a replay that reverts is reported as unknown, not as "no funds moved".
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time

from .replay import load_watchlist
from .rpc import Rpc

TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"  # keccak("Transfer(address,address,uint256)")


def start_anvil(fork_url: str, block: int, port: int) -> subprocess.Popen | None:
    if not shutil.which("anvil"):
        return None
    proc = subprocess.Popen(["anvil", "--fork-url", fork_url, "--fork-block-number", str(block),
                             "--port", str(port), "--silent", "--no-rate-limit"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    local = Rpc("anvil", f"http://127.0.0.1:{port}", retries=0)
    for _ in range(60):
        time.sleep(0.5)
        if local.head() is not None:
            return proc
    proc.kill()
    return None


def _transfers_out(receipt: dict, watch: dict) -> list:
    out = []
    for lg in receipt.get("logs", []):
        topics = lg.get("topics") or []
        if len(topics) == 3 and topics[0] == TRANSFER:
            src = "0x" + topics[1][-40:]
            if src in watch:
                out.append({"token": lg["address"], "from": watch[src], "to": "0x" + topics[2][-40:],
                            "amount": int(lg["data"], 16) if lg.get("data") not in (None, "0x") else None})
    return out


def simulate_tx(tx: dict, local: Rpc, watch: dict) -> dict:
    """Replay `tx` impersonated on the local fork; return balance deltas and transfers out."""
    before = {a: local.call("eth_getBalance", [a, "latest"]) for a in watch}
    local.call("anvil_impersonateAccount", [tx["from"]])
    local.call("anvil_setBalance", [tx["from"], hex(10**20)])   # gas only; never a watched address
    h = local.call("eth_sendTransaction", [{"from": tx["from"], "to": tx.get("to"), "data": tx.get("input", "0x"),
                                            "value": tx.get("value", "0x0"), "gas": hex(min(int(tx["gas"], 16), 30_000_000))}])
    if not h:
        return {"unknown": f"fork rejected the transaction: {local.last_error}"}
    rcpt = None
    for _ in range(120):  # anvil mines after fetching remote state; that can take tens of seconds
        rcpt = local.call("eth_getTransactionReceipt", [h])
        if rcpt:
            break
        time.sleep(0.5)
    if not rcpt:
        return {"unknown": f"no receipt on the fork after 60 s: {local.last_error}"}
    after = {a: local.call("eth_getBalance", [a, "latest"]) for a in watch}
    deltas = {watch[a]: (int(after[a], 16) - int(before[a], 16)) / 1e18
              for a in watch if before[a] and after[a]}
    return {"status": "success" if rcpt.get("status") == "0x1" else "reverted",
            "eth_delta": deltas, "transfers_out": _transfers_out(rcpt, watch),
            "unknown": None if all(before[a] and after[a] for a in watch) else "a balance read failed"}


def simulate(chain: str, tx_hash: str, watchlist: dict, port: int = 8551) -> dict:
    rpc = Rpc(chain)
    tx = rpc.call("eth_getTransactionByHash", [tx_hash])
    if not tx:
        return {"tx": tx_hash, "unknown": "transaction not found on the RPC"}
    block = int(tx["blockNumber"], 16) - 1
    t0 = time.perf_counter()
    proc = start_anvil(rpc.url, block, port)
    if proc is None:
        return {"tx": tx_hash, "fork_block": block, "unknown": "anvil missing or fork did not come up in 30 s"}
    try:
        res = simulate_tx(tx, Rpc("anvil", f"http://127.0.0.1:{port}", retries=0),
                          {k.lower(): v for k, v in watchlist.items()})
    finally:
        proc.kill()
    res.update({"tx": tx_hash, "fork_block": block, "seconds": round(time.perf_counter() - t0, 1)})
    res["funds_left"] = bool(res.get("transfers_out")) or any(d < 0 for d in res.get("eth_delta", {}).values())
    return res


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--chain", default="ethereum")
    p.add_argument("--tx", required=True)
    p.add_argument("--watchlist", required=True)
    p.add_argument("--port", type=int, default=8551)
    a = p.parse_args(argv)
    res = simulate(a.chain, a.tx, load_watchlist(a.watchlist), a.port)
    print(json.dumps(res, indent=1))
    return 0 if res.get("unknown") is None else 2


if __name__ == "__main__":
    sys.exit(main())
