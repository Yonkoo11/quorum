"""Live loop: poll the chain head, run the Stage-1 rules on every new block, notify.

Usage:
  python3 -m watch.live --chain ethereum --watchlist watch/seeds/binance14-2026-10-29.json \
      [--state ai/watch-state.json] [--log ai/watch-live.jsonl] [--max-blocks 3] [--dry-run]

Telegram posting uses the watcher's own bot (QUORUM_WATCH_TG_TOKEN) and chat
(QUORUM_WATCH_TG_CHAT), set up once by scripts/watch-telegram-setup.sh; the buy bot's identity
is never borrowed. Without both, alerts are printed. Messages go through watch/notify.Notifier (1 s apart, 20 per
minute, overflow digested, repeats suppressed) and a heartbeat line goes out every
--heartbeat-minutes. Catch-up: after a gap (sleep, crash) it processes every missed block up
to --catch-up, and logs the gap it skipped beyond that as unknown.

--range (sub-second chains such as Arbitrum): each poll handles every new block as ONE pass.
Code and logs are read across the span, so a watched wallet's code flip or a watched contract's
admin event is never missed; transaction bodies are not fetched, so the per-transaction rules
(type-4, admin call, deploy) do not run, and every record says so. Measured 2026-11-01: per-block
mode on arbitrum.drpc.org fell 148 s behind in 9 blocks (one call takes ~1 s, batches refused).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
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
    token, chat = os.environ.get("QUORUM_WATCH_TG_TOKEN"), os.environ.get("QUORUM_WATCH_TG_CHAT")
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
        self.blocks += rec.get("span", 1)
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


class Prover:
    """Stage 5: a watched contract whose implementation or admin changed (Upgraded / AdminChanged
    emitted by the contract itself) gets prove/hunt.py run on it in the background, at the alert's
    block, so new code is attacked within minutes of going live. A run spends model compute, so it
    is OFF unless --prove, capped at --prove-max-per-day, and one run per contract per day. The
    alert goes out first; the prover never delays it. Finished runs are reported on the next poll."""
    TRIGGERS = ("Upgraded emitted", "AdminChanged emitted")

    def __init__(self, chain: str, notify, max_per_day: int = 2, spawn=subprocess.Popen,
                 clock=time.time, log_dir: str = "ai/hunts", python: str = sys.executable):
        self.chain, self.notify, self.max_per_day, self.spawn, self.clock = chain, notify, max_per_day, spawn, clock
        self.log_dir, self.python = Path(log_dir), python
        self.jobs = []            # running: {address, block, proc, log}
        self.started = {}         # address -> day (YYYY-MM-DD) of its last run
        self.day, self.today = None, 0

    def _day(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime(self.clock()))

    def consider(self, al: dict):
        if al["rule"] != "watchlist_admin_event" or not al.get("acted"):
            return
        if not any(r.endswith(t) for r in al["reasons"] for t in self.TRIGGERS):
            return
        addr, block = al["subject"], al["block"]
        day = self._day()
        if day != self.day:
            self.day, self.today = day, 0
        if self.started.get(addr) == day:
            return self.notify(f"[Quorum watch] prover skipped for {addr}: already ran today")
        if self.today >= self.max_per_day:
            return self.notify(f"[Quorum watch] prover skipped for {addr}: {self.max_per_day} run(s) today already (cap)")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.log_dir / f"{self.chain}-{addr[:10]}-{block}.log"
        cmd = [self.python, "-m", "prove.hunt", self.chain, addr, "--block", str(block),
               "--name", f"watch-{self.chain}-{addr[:10]}-{block}"]
        log = open(log_path, "w")
        try:
            proc = self.spawn(cmd, stdout=log, stderr=subprocess.STDOUT)
        except OSError as exc:
            log.close()
            return self.notify(f"[Quorum watch] prover could NOT start for {addr}: {type(exc).__name__}: {redact(exc)}")
        self.started[addr], self.today = day, self.today + 1
        self.jobs.append({"address": addr, "block": block, "proc": proc, "log": log, "path": log_path})
        self.notify(f"[Quorum watch] prover started on {addr} ({self.chain} block {block}); log {log_path}")

    def reap(self):
        """Report every finished run once: the hunt's own summary line, or the exit code."""
        for job in list(self.jobs):
            code = job["proc"].poll()
            if code is None:
                continue
            self.jobs.remove(job); job["log"].close()
            lines = [l for l in job["path"].read_text().splitlines() if l.strip()]
            summary = next((l for l in reversed(lines) if l.startswith("===")), None)
            if code == 0 and summary:
                self.notify(f"[Quorum watch] prover finished on {job['address']}: {summary.strip('= ')}")
            else:
                tail = lines[-1] if lines else "no output"
                self.notify(f"[Quorum watch] prover FAILED on {job['address']} (exit {code}): {redact(tail)[:300]}; log {job['path']}")


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
        self.last, self.seen, self.codes, self.note = None, set(), {}, None
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            self.last = data.get("last_block")
            self.seen = {(s, tuple(d)) for s, d in data.get("seen_batches", [])}
            self.codes = dict(data.get("codes", {}))   # watched address -> code last seen
        except (ValueError, TypeError, AttributeError) as exc:  # a damaged state file restarts from head, loudly
            self.note = f"state file unreadable ({type(exc).__name__}); starting from head"
            self.last, self.seen, self.codes = None, set(), {}

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"last_block": self.last, "codes": self.codes,
                                         "seen_batches": [[s, list(d)] for s, d in self.seen]}))


def process_block(n: int, chain: str, rpc: Rpc, ctx: Ctx, log, notify, simulate=None, prover=None) -> dict:
    block = rpc.block(n)
    if block is None:
        rec = {"chain": chain, "block": n, "unknown": "block fetch failed", "error": redact(getattr(rpc, "last_error", None), getattr(rpc, "url", None)), "wall": time.time()}
        log.write(json.dumps(rec) + "\n"); log.flush()
        notify(f"[Quorum watch] UNKNOWN: {chain} block {n} could not be fetched; it was NOT checked.")
        return rec
    t0 = time.perf_counter()
    alerts, timing = evaluate_block(block, ctx)
    real = [a for a in alerts if a["level"] == "alert"]
    for al in real:
        _send(notify, format_alert(chain, al), al)   # the alert goes out first; a slow or broken replay never delays it
        if prover:
            prover.consider(al)
        if simulate and al["tx"] and al["rule"] != "7702_type4":   # a delegation moves nothing by itself
            try:
                al["simulation"] = simulate(chain, al["tx"], ctx.watchlist)
            except Exception as exc:
                al["simulation"] = {"unknown": f"replay raised {type(exc).__name__}"}
            notify(f"[Quorum watch] replay of {al['tx']} ({al['subject']}):{format_simulation(al['simulation'])}")
    rec = {"chain": chain, "block": n, "txs": len(block["transactions"]), "alerts": alerts,
           "seconds": timing, "eval_seconds": round(time.perf_counter() - t0, 3),
           "lag_seconds": round(time.time() - int(block["timestamp"], 16), 1), "wall": time.time()}
    return _finish(rec, log, len(real))


def process_range(start: int, end: int, chain: str, rpc: Rpc, ctx: Ctx, log, notify, prover=None) -> dict:
    """Range mode (sub-second chains): one pass over blocks start..end. Code and logs are read
    across the whole span, so the watched-address rules miss nothing; transaction bodies are not
    fetched, so the per-transaction rules do not run and the record says so."""
    header = rpc.header(end)
    if header is None:
        rec = {"chain": chain, "blocks": [start, end], "unknown": "head block fetch failed", "error": redact(getattr(rpc, "last_error", None), getattr(rpc, "url", None)), "wall": time.time()}
        log.write(json.dumps(rec) + "\n"); log.flush()
        notify(f"[Quorum watch] UNKNOWN: {chain} blocks {start}-{end} could not be fetched; they were NOT checked.")
        return rec
    t0 = time.perf_counter()
    alerts, timing = evaluate_block({**header, "transactions": [], "range_start": start}, ctx)
    real = [a for a in alerts if a["level"] == "alert"]
    for al in real:
        _send(notify, format_alert(chain, al), al)
        if prover:
            prover.consider(al)
    rec = {"chain": chain, "block": end, "blocks": [start, end], "span": end - start + 1, "txs": "not read",
           "alerts": alerts, "seconds": timing, "eval_seconds": round(time.perf_counter() - t0, 3),
           "lag_seconds": round(time.time() - int(header["timestamp"], 16), 1), "wall": time.time(),
           "unknowns": [f"transaction bodies of blocks {start}-{end} not read "
                        "(range mode: the type-4, admin-call and deploy rules did not run)"]}
    return _finish(rec, log, len(real))


def _finish(rec: dict, log, real: int) -> dict:
    log.write(json.dumps(rec) + "\n"); log.flush()
    span = f"blocks {rec['blocks'][0]}-{rec['blocks'][1]}" if "blocks" in rec else f"block {rec['block']}"
    print(f"{span}: {rec['txs']} txs, {real} alerts, {len(rec['alerts']) - real} info, "
          f"eval {rec['eval_seconds']}s, lag {rec['lag_seconds']}s")
    return rec


def _send(notify, text: str, al: dict):
    """An alert where a watched address itself acted goes out as urgent (first in any digest).
    Decided from the rule's own `acted` field, never from the message text and never from being
    targeted (review 2026-11-01: a planted address, a tx sent to a watched wallet or a deploy
    embedding it are all open to anyone; a signature from the watched key is not)."""
    if al.get("acted") and hasattr(notify, "urgent"):
        notify.urgent(text)
    else:
        notify(text)


def _first_block(chain: str, state: State, head: int, catch_up: int, log, notify) -> int:
    start = head if state.last is None else state.last + 1
    if head - start + 1 > catch_up:
        log.write(json.dumps({"chain": chain, "unknown": f"skipped blocks {start}-{head - catch_up}",
                              "wall": time.time()}) + "\n")
        notify(f"[Quorum watch] UNKNOWN: {chain} blocks {start}-{head - catch_up} were NOT checked "
               f"(gap larger than the {catch_up}-block catch-up).")
        start = head - catch_up + 1
    return start


def _targets(start: int, head: int, range_mode: bool) -> list:
    """Range mode: the whole span is one pass (flat cost on fast chains); else one block at a time.
    A span of one block is read in full either way (its transaction rules can run, so they do)."""
    return [(start, head)] if range_mode and head > start else [(n, n) for n in range(start, head + 1)]


def run(chain: str, watchlist: dict, state: State, log_path: str, notify, max_blocks: int | None,
        catch_up: int = 50, rpc: Rpc | None = None, sleep=time.sleep, simulate=None,
        heartbeat_seconds: int = 0, clock=time.time, range_mode: bool = False, prover=None) -> int:
    rpc = rpc or Rpc(chain)
    ctx = Ctx(rpc, watchlist, state.codes)
    ctx.seen_batches = state.seen
    done, beat = 0, Heartbeat(chain, notify, heartbeat_seconds, clock)
    if state.note:
        notify(f"[Quorum watch] UNKNOWN: {state.note}")
    with open(log_path, "a") as log:
        while max_blocks is None or done < max_blocks:
            if prover:
                prover.reap()
            head = rpc.head()
            if head is None:
                log.write(json.dumps({"chain": chain, "unknown": "head fetch failed", "error": redact(getattr(rpc, "last_error", None), getattr(rpc, "url", None)), "wall": time.time()}) + "\n")
                sleep(BLOCK_SECONDS.get(chain, 12)); continue
            start = _first_block(chain, state, head, catch_up, log, notify)
            if start > head:
                sleep(BLOCK_SECONDS.get(chain, 12)); continue
            for a, b in _targets(start, head, range_mode):
                beat.tick(process_block(a, chain, rpc, ctx, log, notify, simulate, prover) if a == b
                          else process_range(a, b, chain, rpc, ctx, log, notify, prover))
                state.last = b; state.save(); done += 1
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
    p.add_argument("--range", action="store_true", help="one pass per poll over all new blocks (fast chains)")
    p.add_argument("--catch-up", type=int, default=50, help="blocks processed after a gap; the rest is logged unknown")
    p.add_argument("--prove", action="store_true",
                   help="Stage 5: run prove/hunt.py on a watched contract after its Upgraded/AdminChanged (spends model compute)")
    p.add_argument("--prove-max-per-day", type=int, default=2, help="cap on prover runs per UTC day")
    a = p.parse_args(argv)
    sim = None
    if a.simulate:
        from .simulate import simulate as sim
    prover = Prover(a.chain, make_notifier(a.dry_run), a.prove_max_per_day) if a.prove else None
    watchlist = load_watchlist(a.watchlist)
    notify = make_notifier(a.dry_run)
    print(f"watch live: {a.chain}, {'range' if a.range else 'per-block'} mode, "
          f"{'Telegram' if has_telegram(a.dry_run) else 'print only'}, state {a.state}, "
          f"heartbeat every {a.heartbeat_minutes} min, prover {'on, ' + str(a.prove_max_per_day) + '/day' if prover else 'off'}")
    return run(a.chain, watchlist, State(Path(a.state)), a.log, notify, a.max_blocks, catch_up=a.catch_up,
               simulate=sim, heartbeat_seconds=a.heartbeat_minutes * 60, range_mode=a.range, prover=prover)


def has_telegram(dry_run: bool) -> bool:
    return bool(os.environ.get("QUORUM_WATCH_TG_TOKEN") and os.environ.get("QUORUM_WATCH_TG_CHAT")) and not dry_run


def make_notifier(dry_run: bool) -> Notifier:
    """Telegram when the bot env is set, print otherwise. Digest priority is the caller's call
    (see _send): it comes from the alert's own fields, not from anything in the message text."""
    send = (lambda t: post_telegram(t) or print(t)) if has_telegram(dry_run) else print
    return Notifier(send)


if __name__ == "__main__":
    sys.exit(main())
