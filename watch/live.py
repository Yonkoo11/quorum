"""Live loop: poll the chain head, run the Stage-1 rules on every new block, notify.

Usage:
  python3 -m watch.live --chain ethereum --watchlist watch/seeds/binance14-2026-10-29.json \
      [--state ai/watch-state.json] [--log ai/watch-live.jsonl] [--max-blocks 3] [--dry-run]

Telegram posting uses the same env names as bot/buybot.py (BUYBOT_TG_TOKEN, BUYBOT_TG_CHAT);
without them, alerts are printed. Catch-up: after a gap (sleep, crash) it processes every
missed block up to --catch-up, and logs the gap it skipped beyond that as unknown.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

from .replay import Ctx, evaluate_block, load_watchlist
from .rpc import Rpc

BLOCK_SECONDS = {"ethereum": 12, "arbitrum": 1, "base": 2}


def post_telegram(text: str) -> bool:
    token, chat = os.environ.get("BUYBOT_TG_TOKEN"), os.environ.get("BUYBOT_TG_CHAT")
    if not token or not chat:
        return False
    body = json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", body,
                                 {"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except Exception as exc:  # the alert still reaches stdout and the log
        print(f"telegram post failed: {exc}")
        return False


def format_alert(chain: str, al: dict) -> str:
    head = f"[Quorum watch] {al['rule']} on {chain} block {al['block']}"
    body = "\n".join(f"- {r}" for r in al["reasons"])
    unk = f"\nUNKNOWN: {', '.join(al['unknowns'])}" if al["unknowns"] else ""
    tx = f"\ntx {al['tx']}" if al["tx"] else ""
    sim = al.get("simulation")
    if sim:
        if sim.get("unknown"):
            sim_line = f"\nfork replay UNKNOWN: {sim['unknown']}"
        else:
            sim_line = (f"\nfork replay ({sim['seconds']}s): funds left = {sim['funds_left']}; "
                        f"ETH delta {sim['eth_delta']}; {len(sim['transfers_out'])} token transfer(s) out")
    else:
        sim_line = ""
    return f"{head}\nsubject {al['subject']}{tx}\n{body}{unk}{sim_line}\nalert only: no pause role is granted."


class State:
    def __init__(self, path: Path):
        self.path = path
        self.last, self.seen, self.note = None, set(), None
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.last = data.get("last_block")
            self.seen = {(s, tuple(d)) for s, d in data.get("seen_batches", [])}
        except (ValueError, TypeError) as exc:  # a damaged state file restarts from head, loudly
            self.note = f"state file unreadable ({type(exc).__name__}); starting from head"
            self.last, self.seen = None, set()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"last_block": self.last,
                                         "seen_batches": [[s, list(d)] for s, d in self.seen]}))


def process_block(n: int, chain: str, rpc: Rpc, ctx: Ctx, log, notify, simulate=None) -> dict:
    block = rpc.block(n)
    if block is None:
        rec = {"chain": chain, "block": n, "unknown": "block fetch failed", "wall": time.time()}
        log.write(json.dumps(rec) + "\n"); log.flush()
        notify(f"[Quorum watch] UNKNOWN: {chain} block {n} could not be fetched; it was NOT checked.")
        return rec
    t0 = time.perf_counter()
    alerts, timing = evaluate_block(block, ctx)
    real = [a for a in alerts if a["level"] == "alert"]
    for al in real:
        if simulate and al["tx"] and al["rule"] != "7702_type4":   # a delegation moves nothing by itself
            al["simulation"] = simulate(chain, al["tx"], ctx.watchlist)
        notify(format_alert(chain, al))
    rec = {"chain": chain, "block": n, "txs": len(block["transactions"]), "alerts": alerts,
           "seconds": timing, "eval_seconds": round(time.perf_counter() - t0, 3),
           "lag_seconds": round(time.time() - int(block["timestamp"], 16), 1), "wall": time.time()}
    log.write(json.dumps(rec) + "\n"); log.flush()
    print(f"block {n}: {len(block['transactions'])} txs, {len(real)} alerts, "
          f"{len(alerts) - len(real)} info, eval {rec['eval_seconds']}s, lag {rec['lag_seconds']}s")
    return rec


def run(chain: str, watchlist: dict, state: State, log_path: str, notify, max_blocks: int | None,
        catch_up: int = 50, rpc: Rpc | None = None, sleep=time.sleep, simulate=None) -> int:
    rpc = rpc or Rpc(chain)
    ctx = Ctx(rpc, watchlist)
    ctx.seen_batches = state.seen
    done = 0
    if state.note:
        notify(f"[Quorum watch] UNKNOWN: {state.note}")
    with open(log_path, "a") as log:
        while max_blocks is None or done < max_blocks:
            head = rpc.head()
            if head is None:
                log.write(json.dumps({"chain": chain, "unknown": "head fetch failed", "wall": time.time()}) + "\n")
                sleep(BLOCK_SECONDS.get(chain, 12)); continue
            start = head if state.last is None else state.last + 1
            if start > head:
                sleep(BLOCK_SECONDS.get(chain, 12)); continue
            if head - start + 1 > catch_up:
                log.write(json.dumps({"chain": chain, "unknown": f"skipped blocks {start}-{head - catch_up}",
                                      "wall": time.time()}) + "\n")
                notify(f"[Quorum watch] UNKNOWN: {chain} blocks {start}-{head - catch_up} were NOT checked "
                       f"(gap larger than the {catch_up}-block catch-up).")
                start = head - catch_up + 1
            for n in range(start, head + 1):
                process_block(n, chain, rpc, ctx, log, notify, simulate)
                state.last = n; state.save(); done += 1
                if max_blocks is not None and done >= max_blocks:
                    break
    return 0


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--chain", default="ethereum")
    p.add_argument("--watchlist")
    p.add_argument("--state", default="ai/watch-state.json")
    p.add_argument("--log", default="ai/watch-live.jsonl")
    p.add_argument("--max-blocks", type=int)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--simulate", action="store_true", help="replay flagged txs on an anvil fork (Stage 3)")
    a = p.parse_args(argv)
    sim = None
    if a.simulate:
        from .simulate import simulate as sim
    has_tg = bool(os.environ.get("BUYBOT_TG_TOKEN")) and not a.dry_run
    notify = (lambda t: post_telegram(t) or print(t)) if has_tg else print
    print(f"watch live: {a.chain}, {'Telegram' if has_tg else 'print only'}, state {a.state}")
    return run(a.chain, load_watchlist(a.watchlist), State(Path(a.state)), a.log, notify, a.max_blocks,
               simulate=sim)


if __name__ == "__main__":
    sys.exit(main())
