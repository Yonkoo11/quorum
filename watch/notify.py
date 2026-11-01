"""Notifier: spaces outgoing messages so Telegram never throttles the watcher.

Limits from the Bot API FAQ (read 2026-11-01): at most 1 message/second per chat and 20/minute
in a group; past that the API answers HTTP 429 with `retry_after` seconds. So: a 1 s gap
between sends, at most `per_minute` sends in any 60 s window, the overflow held and sent as one
digest once the window has room, and an identical alert (same rule + subject) within
`dedupe_seconds` counted instead of re-sent. Everything still reaches the jsonl log.
"""
from __future__ import annotations

import re
import time

ALERT_HEAD = re.compile(r"^\[Quorum watch\] (\S+) on \S+ block \d+\nsubject (\S+)")
TELEGRAM_MAX = 4096


class Notifier:
    def __init__(self, send, clock=time.time, sleep=time.sleep, per_minute=20, dedupe_seconds=600):
        self.send, self.clock, self.sleep = send, clock, sleep
        self.per_minute, self.dedupe_seconds = per_minute, dedupe_seconds
        self.sent_at: list[float] = []            # send times inside the last minute
        self.last_seen: dict = {}                 # (rule, subject) -> time of the last send
        self.held: list[str] = []                 # overflow waiting for the digest
        self.stats = {"sent": 0, "held": 0, "suppressed": 0}

    def _room(self, now: float) -> bool:
        self.sent_at = [t for t in self.sent_at if now - t < 60]
        return len(self.sent_at) < self.per_minute

    def __call__(self, text: str) -> bool:
        now = self.clock()
        m = ALERT_HEAD.match(text)
        if m:
            key = m.groups()
            if key in self.last_seen and now - self.last_seen[key] < self.dedupe_seconds:
                self.stats["suppressed"] += 1
                return False
            self.last_seen[key] = now
        if not self._room(now):
            self.held.append(text); self.stats["held"] += 1
            return False
        if self.sent_at and now - self.sent_at[-1] < 1:
            self.sleep(1 - (now - self.sent_at[-1]))
            now = self.clock()
        self.sent_at.append(now); self.stats["sent"] += 1
        self.send(text[:TELEGRAM_MAX])     # the sender reports its own failures
        return True

    def flush(self) -> bool:
        """Send everything held back as one digest, once the minute window has room."""
        if not self.held or not self._room(self.clock()):
            return False
        held, self.held = self.held, []
        body = "\n---\n".join(held)
        return self(f"[Quorum watch] digest: {len(held)} message(s) held by the rate limit\n{body}")

    def summary(self) -> str:
        s = self.stats
        return f"{s['sent']} sent, {s['held']} held for digest, {s['suppressed']} repeats suppressed"
