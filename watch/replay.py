"""Replay a block range through the Stage-1 rules and time it.

Usage:
  python3 -m watch.replay --chain ethereum --from 26319519 --to 26319519 \
      [--watchlist watch/watchlist.json] [--incident-tx 0x...] [--log ai/watch-replay.jsonl]

Prints one line per alert, then a summary: blocks, alerts per rule, RPC calls,
failures (unknowns), and, when --incident-tx is given, the lag between the
incident's block and the first alert on the same subject (0 = same block).
Every evaluation is appended to the JSONL log so a verdict can be replayed.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .rpc import Rpc
from .rules import RULES


class Ctx:
    def __init__(self, rpc: Rpc, watchlist: dict):
        self.rpc = rpc
        self.watchlist = {k.lower(): v for k, v in watchlist.items()}
        self._code = {}
        self.seen_batches = set()   # (sender, delegates) batches already alerted this run

    def cached_code(self, address: str):
        if address not in self._code:
            self._code[address] = self.rpc.code(address)
        return self._code[address]


def load_watchlist(path: str | None) -> dict:
    if not path:
        return {}
    return json.loads(Path(path).read_text())


def evaluate_block(block: dict, ctx: Ctx) -> tuple[list, dict]:
    """Run every rule on one block; return (alerts, per-rule seconds)."""
    alerts, timing = [], {}
    for rule in RULES:
        t0 = time.perf_counter()
        alerts.extend(rule(block, ctx))
        timing[rule.__name__] = round(time.perf_counter() - t0, 3)
    return alerts, timing


def replay(chain: str, start: int, end: int, watchlist: dict, log_path: str | None, rpc: Rpc | None = None):
    rpc = rpc or Rpc(chain)
    ctx = Ctx(rpc, watchlist)
    log = open(log_path, "a") if log_path else None
    all_alerts, missing = [], []
    for n in range(start, end + 1):
        block = rpc.block(n)
        if block is None:
            missing.append(n)
            continue
        alerts, timing = evaluate_block(block, ctx)
        all_alerts.extend(alerts)
        if log:
            log.write(json.dumps({"chain": chain, "block": n, "txs": len(block["transactions"]),
                                  "alerts": alerts, "seconds": timing, "wall": time.time()}) + "\n")
    if log:
        log.close()
    return all_alerts, missing, rpc


def incident_lag(alerts: list, incident_tx: str, rpc: Rpc):
    """Blocks between the incident tx's block and the first alert on its sender or receiver."""
    tx = rpc.call("eth_getTransactionByHash", [incident_tx])
    if not tx:
        return None, "incident tx not found (unknown)"
    subjects = {(tx.get("from") or "").lower(), (tx.get("to") or "").lower()}
    ib = int(tx["blockNumber"], 16)
    hits = [a for a in alerts if a["subject"] in subjects or a["tx"] == incident_tx]
    if not hits:
        return None, f"no alert touched the incident (block {ib})"
    first = min(a["block"] for a in hits)
    return first - ib, f"first alert at block {first}, incident at {ib}"


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--chain", default="ethereum")
    p.add_argument("--from", dest="start", type=int, required=True)
    p.add_argument("--to", dest="end", type=int)
    p.add_argument("--watchlist")
    p.add_argument("--incident-tx")
    p.add_argument("--log", default="ai/watch-replay.jsonl")
    a = p.parse_args(argv)
    end = a.end or a.start
    t0 = time.perf_counter()
    alerts, missing, rpc = replay(a.chain, a.start, end, load_watchlist(a.watchlist), a.log)
    real = [al for al in alerts if al["level"] == "alert"]
    for al in real:
        print(f"[{al['rule']}] block {al['block']} tx {al['tx']} subject {al['subject']}: "
              + "; ".join(al["reasons"]) + (f" | UNKNOWN: {al['unknowns']}" if al["unknowns"] else ""))
    per_rule = {}
    for al in real:
        per_rule[al["rule"]] = per_rule.get(al["rule"], 0) + 1
    unknown = sum(1 for al in alerts if al["unknowns"])
    print(f"\nblocks {a.start}-{end} ({end - a.start + 1}), missing {missing}, "
          f"{len(real)} alerts {per_rule}, {len(alerts) - len(real)} info-only, {unknown} with unknowns, "
          f"rpc calls {rpc.calls}, rpc failures {rpc.failures}, {time.perf_counter() - t0:.1f}s wall")
    if a.incident_tx:
        lag, note = incident_lag(real, a.incident_tx, rpc)
        print(f"incident lag: {lag} block(s). {note}")
    return 0 if not missing else 2


if __name__ == "__main__":
    sys.exit(main())
