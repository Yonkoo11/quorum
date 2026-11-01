"""Zcash supply reader: one Zebra `getblockchaininfo` call per poll, three checks, no model.

Facts from Zebra's own source (zebra-rpc/src/methods/types/get_blockchain_info.rs, read 2026-11-01):
`valuePools` has six entries with ids transparent, sprout, sapling, orchard, lockbox, ironwood,
each with `chainValueZat`; `monitored` just means "balance is not zero", it is NOT a sync flag;
`chainSupply.chainValueZat` is the sum of the six pools (the NU7 reserve is deliberately left out,
so supply may fall as fees burn). Bound from zebra-chain/src/parameters/network/subsidy/constants.rs:
MAX_BLOCK_SUBSIDY = 12.5 ZEC, the most any one block has ever been allowed to add.

Checks per reading: the six pools are present and non-negative; their sum equals chainSupply;
supply rose by no more than MAX_BLOCK_SUBSIDY per block since the last reading. A node that is
unreachable or behind its own estimated height gives UNKNOWN, never a clean reading. The local
node on this machine is a Regtest at height 0, so it reads UNKNOWN by design.

Usage: python3 -m watch.zcash --rpc http://127.0.0.1:18232 [--state ai/zcash-state.json]
           [--log ai/zcash-live.jsonl] [--every 60] [--once] [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

from .simulate import redact

POOLS = ("transparent", "sprout", "sapling", "orchard", "lockbox", "ironwood")
MAX_BLOCK_SUBSIDY_ZAT = 1_250_000_000          # 12.5 ZEC (Zebra constants.rs)
ZAT = 100_000_000
SYNC_SLACK = 2                                 # blocks behind the node's own estimate still counts as synced


def rpc_call(url: str, method: str, params=(), timeout: int = 20):
    """None = unknown (unreachable, error, bad JSON); the reason is printed with URLs redacted."""
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": list(params)}).encode()
    req = urllib.request.Request(url, body, {"content-type": "application/json", "user-agent": "quorum-watch"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.load(r)
    except Exception as exc:
        print(f"zcash rpc {method} failed: {redact(exc)}")
        return None
    if not isinstance(data, dict) or data.get("error") or "result" not in data:
        print(f"zcash rpc {method}: error answer")
        return None
    return data["result"]


def parse_info(info: dict) -> dict:
    """Turn a getblockchaininfo answer into one reading; `unknown` set when it cannot be trusted."""
    try:
        pools = {p["id"]: int(p["chainValueZat"]) for p in info["valuePools"]}
        out = {"chain": info.get("chain"), "height": int(info["blocks"]), "estimated": int(info.get("estimatedheight", 0)),
               "pools": {p: pools[p] for p in POOLS if p in pools}, "supply": int(info["chainSupply"]["chainValueZat"]),
               "wall": time.time()}
    except (KeyError, TypeError, ValueError) as exc:
        return {"unknown": f"answer missing or malformed ({type(exc).__name__})", "wall": time.time()}
    missing = [p for p in POOLS if p not in pools]
    if missing:
        out["unknown"] = f"pools missing: {', '.join(missing)}"
    elif out["height"] < out["estimated"] - SYNC_SLACK:
        out["unknown"] = f"node not synced: height {out['height']} of about {out['estimated']}"
    return out


def read_supply(url: str) -> dict:
    info = rpc_call(url, "getblockchaininfo")
    return parse_info(info) if info is not None else {"unknown": "node unreachable", "wall": time.time()}


def _finding(cur: dict, reasons: list, level: str, unknowns=()) -> dict:
    return {"rule": "zcash_supply", "version": 1, "level": level, "block": cur.get("height"),
            "block_ts": None, "tx": None, "subject": "zcash", "reasons": reasons, "unknowns": list(unknowns)}


def check(prev: dict | None, cur: dict) -> list[dict]:
    """Findings for one reading against the previous trusted one."""
    if "unknown" in cur:
        return [_finding(cur, ["supply NOT checked"], "unknown", [cur["unknown"]])]
    reasons = []
    negative = [p for p, v in cur["pools"].items() if v < 0]
    if negative:
        reasons.append(f"negative pool balance: {', '.join(negative)}")
    total = sum(cur["pools"].values())
    if total != cur["supply"]:
        reasons.append(f"pools sum to {total / ZAT:.8f} ZEC but chainSupply says {cur['supply'] / ZAT:.8f}")
    if prev and "unknown" not in prev:
        blocks, rise = cur["height"] - prev["height"], cur["supply"] - prev["supply"]
        if blocks < 0:
            reasons.append(f"height fell {prev['height']} -> {cur['height']} (reorg?)")
        elif rise > blocks * MAX_BLOCK_SUBSIDY_ZAT:
            reasons.append(f"supply rose {rise / ZAT:.8f} ZEC over {blocks} block(s); "
                           f"the protocol allows at most {blocks * MAX_BLOCK_SUBSIDY_ZAT / ZAT:.1f}")
    if reasons:
        return [_finding(cur, reasons, "alert")]
    return [_finding(cur, [f"height {cur['height']}, supply {cur['supply'] / ZAT:.8f} ZEC, pools consistent"], "info")]


def run(url: str, state_path: Path, log_path: str, notify, every: int, once: bool, sleep=time.sleep) -> int:
    from .live import format_alert
    prev = json.loads(state_path.read_text()).get("prev") if state_path.exists() else None
    with open(log_path, "a") as log:
        while True:
            cur = read_supply(url)
            findings = check(prev, cur)
            log.write(json.dumps({"reading": cur, "findings": findings}) + "\n"); log.flush()
            for f in findings:
                if f["level"] != "info":
                    notify(format_alert("zcash", f))
                print(f"zcash {f['level']}: {'; '.join(f['reasons'] + f['unknowns'])}")
            if "unknown" not in cur:
                prev = cur
                state_path.parent.mkdir(parents=True, exist_ok=True)
                state_path.write_text(json.dumps({"prev": prev}))
            if once:
                return 0
            if hasattr(notify, "flush"):
                notify.flush()
            sleep(every)


def main(argv=None):
    from .live import make_notifier
    p = argparse.ArgumentParser()
    p.add_argument("--rpc", default="http://127.0.0.1:18232")
    p.add_argument("--state", default="ai/zcash-state.json")
    p.add_argument("--log", default="ai/zcash-live.jsonl")
    p.add_argument("--every", type=int, default=60, help="seconds between readings")
    p.add_argument("--once", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    return run(a.rpc, Path(a.state), a.log, make_notifier(a.dry_run), a.every, a.once)


if __name__ == "__main__":
    sys.exit(main())
