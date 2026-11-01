"""Live loop: poll the chain head, run the Stage-1 rules on every new block, notify.

Usage:
  python3 -m watch.live --chain ethereum --watchlist watch/seeds/binance14-2026-10-29.json \
      [--state ai/watch-state.json] [--log ai/watch-live.jsonl] [--max-blocks 3] [--dry-run]

Telegram posting uses the same env names as bot/buybot.py (BUYBOT_TG_TOKEN, BUYBOT_TG_CHAT);
without them, alerts are printed. Messages go through watch/notify.Notifier (1 s apart, 20 per
minute, overflow digested, repeats suppressed) and a heartbeat line goes out every
--heartbeat-minutes. Catch-up: after a gap (sleep, crash) it processes every missed block up
to --catch-up, and logs the gap it skipped beyond that as unknown.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from .notify import Notifier
from .replay import Ctx, evaluate_block, load_watchlist
from .rpc import Rpc
from .simulate import redact

BLOCK_SECONDS = {"ethereum": 12, "arbitrum": 1, "base": 2}


def post_telegram(text: str, sleep=time.sleep) -> bool:
    """One send; on HTTP 429 waits the API's own `retry_after` (Bot API ResponseParameters) and
    retries once. Any failure is printed (URLs redacted) and the message stays in the log."""
    token, chat = os.environ.get("BUYBOT_TG_TOKEN"), os.environ.get("BUYBOT_TG_CHAT")
    if not token or not chat:
        return False
    body = json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode()
    for attempt in (1, 2):
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", body,
                                     {"content-type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.status == 200
        except urllib.error.HTTPError as exc:
            if exc.code == 429 and attempt == 1:
                wait = _retry_after(exc)
                print(f"telegram flood control: waiting {wait}s")
                sleep(wait); continue
            print(f"telegram post failed: HTTP {exc.code}")
        except Exception as exc:  # the alert still reaches stdout and the log
            print(f"telegram post failed: {redact(exc)}")
        return False
    return False


def _retry_after(exc) -> int:
    try:
        return max(1, int(json.load(exc)["parameters"]["retry_after"]))
    except Exception:
        return 5


class Heartbeat:
    """Every `every` seconds, one line: blocks checked, alerts, info rows, lag, notifier stats."""
    def __init__(self, chain: str, notify, every: int, clock=time.time):
        self.chain, self.notify, self.every, self.clock = chain, notify, every, clock
        self.since, self.blocks, self.alerts, self.info, self.lag = clock(), 0, 0, 0, None

    def tick(self, rec: dict):
        self.blocks += 1
        if "alerts" in rec:
            real = sum(1 for a in rec["alerts"] if a["level"] == "alert")
            self.alerts += real; self.info += len(rec["alerts"]) - real; self.lag = rec["lag_seconds"]
        now = self.clock()
        if self.every and now - self.since >= self.every:
            stats = f"; {self.notify.summary()}" if hasattr(self.notify, "summary") else ""
            self.notify(f"[Quorum watch] heartbeat: {self.chain} watching, {self.blocks} blocks in "
                        f"{round((now - self.since) / 60)} min, {self.alerts} alert(s), {self.info} info, "
                        f"lag {self.lag}s{stats}")
            self.since, self.blocks, self.alerts, self.info = now, 0, 0, 0


def format_alert(chain: str, al: dict) -> str:
    head = f"[Quorum watch] {al['rule']} on {chain} block {al['block']}"
    body = "\n".join(f"- {r}" for r in al["reasons"])
    unk = f"\nUNKNOWN: {', '.join(al['unknowns'])}" if al["unknowns"] else ""
    tx = f"\ntx {al['tx']}" if al["tx"] else ""
    sim_line = format_simulation(al["simulation"]) if al.get("simulation") else ""
    return f"{head}\nsubject {al['subject']}{tx}\n{body}{unk}{sim_line}\nalert only: no pause role is granted."


def format_simulation(sim: dict) -> str:
    if sim.get("unknown"):
        return f"\nfork replay UNKNOWN: {sim['unknown']}"
    return (f"\nfork replay ({sim['seconds']}s): funds left = {sim['funds_left']}; "
            f"ETH delta {sim['eth_delta']}; {len(sim['transfers_out'])} token transfer(s) out")


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
        notify(format_alert(chain, al))   # the alert goes out first; a slow or broken replay never delays it
        if simulate and al["tx"] and al["rule"] != "7702_type4":   # a delegation moves nothing by itself
            try:
                al["simulation"] = simulate(chain, al["tx"], ctx.watchlist)
            except Exception as exc:
                al["simulation"] = {"unknown": f"replay raised {type(exc).__name__}"}
            notify(f"[Quorum watch] replay of {al['tx']} ({al['subject']}):{format_simulation(al['simulation'])}")
    rec = {"chain": chain, "block": n, "txs": len(block["transactions"]), "alerts": alerts,
           "seconds": timing, "eval_seconds": round(time.perf_counter() - t0, 3),
           "lag_seconds": round(time.time() - int(block["timestamp"], 16), 1), "wall": time.time()}
    log.write(json.dumps(rec) + "\n"); log.flush()
    print(f"block {n}: {len(block['transactions'])} txs, {len(real)} alerts, "
          f"{len(alerts) - len(real)} info, eval {rec['eval_seconds']}s, lag {rec['lag_seconds']}s")
    return rec


def _first_block(chain: str, state: State, head: int, catch_up: int, log, notify) -> int:
    start = head if state.last is None else state.last + 1
    if head - start + 1 > catch_up:
        log.write(json.dumps({"chain": chain, "unknown": f"skipped blocks {start}-{head - catch_up}",
                              "wall": time.time()}) + "\n")
        notify(f"[Quorum watch] UNKNOWN: {chain} blocks {start}-{head - catch_up} were NOT checked "
               f"(gap larger than the {catch_up}-block catch-up).")
        start = head - catch_up + 1
    return start


def run(chain: str, watchlist: dict, state: State, log_path: str, notify, max_blocks: int | None,
        catch_up: int = 50, rpc: Rpc | None = None, sleep=time.sleep, simulate=None,
        heartbeat_seconds: int = 0, clock=time.time) -> int:
    rpc = rpc or Rpc(chain)
    ctx = Ctx(rpc, watchlist)
    ctx.seen_batches = state.seen
    done, beat = 0, Heartbeat(chain, notify, heartbeat_seconds, clock)
    if state.note:
        notify(f"[Quorum watch] UNKNOWN: {state.note}")
    with open(log_path, "a") as log:
        while max_blocks is None or done < max_blocks:
            head = rpc.head()
            if head is None:
                log.write(json.dumps({"chain": chain, "unknown": "head fetch failed", "wall": time.time()}) + "\n")
                sleep(BLOCK_SECONDS.get(chain, 12)); continue
            start = _first_block(chain, state, head, catch_up, log, notify)
            if start > head:
                sleep(BLOCK_SECONDS.get(chain, 12)); continue
            for n in range(start, head + 1):
                beat.tick(process_block(n, chain, rpc, ctx, log, notify, simulate))
                state.last = n; state.save(); done += 1
                if max_blocks is not None and done >= max_blocks:
                    break
            if hasattr(notify, "flush"):
                notify.flush()          # anything the rate limit held back goes out as one digest
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
    p.add_argument("--heartbeat-minutes", type=int, default=60, help="0 = no heartbeat")
    a = p.parse_args(argv)
    sim = None
    if a.simulate:
        from .simulate import simulate as sim
    watchlist = load_watchlist(a.watchlist)
    notify = make_notifier(a.dry_run, watchlist)
    print(f"watch live: {a.chain}, {'Telegram' if has_telegram(a.dry_run) else 'print only'}, "
          f"state {a.state}, heartbeat every {a.heartbeat_minutes} min")
    return run(a.chain, watchlist, State(Path(a.state)), a.log, notify, a.max_blocks,
               simulate=sim, heartbeat_seconds=a.heartbeat_minutes * 60)


def has_telegram(dry_run: bool) -> bool:
    return bool(os.environ.get("BUYBOT_TG_TOKEN")) and not dry_run


def make_notifier(dry_run: bool, watchlist: dict) -> Notifier:
    """Telegram when the bot env is set, print otherwise; an alert whose subject is a watched address
    goes first in any digest (review 2026-11-01: noise must not crowd out the watchlist, and a reason
    line that merely mentions a watched address must not buy priority)."""
    send = (lambda t: post_telegram(t) or print(t)) if has_telegram(dry_run) else print
    watched = {k.lower() for k in watchlist}
    return Notifier(send, priority=lambda t: is_watched_subject(t, watched))


SUBJECT_LINE = re.compile(r"^subject (\S+)$", re.M)


def is_watched_subject(text: str, watched: set) -> bool:
    """Only the alert's own `subject` line counts, matched exactly against the watchlist keys:
    an address an attacker plants in a reason line (a delegate target, say) must not jump the queue."""
    m = SUBJECT_LINE.search(text)
    return bool(m) and m.group(1).lower() in watched


if __name__ == "__main__":
    sys.exit(main())
