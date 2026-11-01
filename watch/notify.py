"""Notifier: spaces outgoing messages so Telegram never throttles the watcher.

Limits from the Bot API FAQ (read 2026-11-01): at most 1 message/second per chat and 20/minute
in a group; past that the API answers HTTP 429 with `retry_after` seconds. So: a 1 s gap
between sends, at most `per_minute` sends in any 60 s window, the overflow held and sent as
digests (each under the 4096-char message limit, watched-subject alerts first, the rest waits
for the next window), and a byte-identical repeat within `dedupe_seconds` counted instead of
re-sent. A message too long for one Telegram post is cut with a visible note. Everything still
reaches the jsonl log.
"""
from __future__ import annotations

import hashlib
import time

TELEGRAM_MAX = 4096
DIGEST_RESERVE = 96                      # room for the digest header inside one post
SEP = "\n---\n"


def fit(text: str) -> str:
    """Cut to one Telegram post, saying so; the full text is already in the jsonl log."""
    if len(text) <= TELEGRAM_MAX:
        return text
    note = f"\n[cut: message was {len(text)} characters; full text in the jsonl log]"
    return text[:TELEGRAM_MAX - len(note)] + note


def pack(msgs: list[str], budget: int = TELEGRAM_MAX - DIGEST_RESERVE) -> list[list[str]]:
    """Group messages into digests that fit one post each; an oversize one goes alone (and is cut)."""
    chunks, cur, size = [], [], 0
    for m in msgs:
        need = min(len(m), budget) + (len(SEP) if cur else 0)
        if cur and size + need > budget:
            chunks.append(cur); cur, size, need = [], 0, min(len(m), budget)
        cur.append(m); size += need
    if cur:
        chunks.append(cur)
    return chunks


class Notifier:
    def __init__(self, send, clock=time.time, sleep=time.sleep, per_minute=20, dedupe_seconds=600):
        self.send, self.clock, self.sleep = send, clock, sleep
        self.per_minute, self.dedupe_seconds = per_minute, dedupe_seconds
        self.sent_at: list[float] = []            # send times inside the last minute
        self.last_seen: dict = {}                 # sha256(text) -> time of the last send
        self.held: list[tuple[bool, str]] = []    # (urgent, text) overflow waiting for the digest
        self.stats = {"sent": 0, "held": 0, "suppressed": 0}

    def _room(self, now: float) -> bool:
        self.sent_at = [t for t in self.sent_at if now - t < 60]
        return len(self.sent_at) < self.per_minute

    def __call__(self, text: str) -> bool:
        return self._accept(text, urgent=False)

    def urgent(self, text: str) -> bool:
        """Same path, but goes first in any digest. The caller decides from the alert's own fields
        (review 2026-11-01: deciding from the rendered text let a planted address buy priority)."""
        return self._accept(text, urgent=True)

    def _accept(self, text: str, urgent: bool) -> bool:
        """Only a byte-identical repeat is a repeat: a new tx, block or reason is a new message
        (review 2026-11-01: keying on rule+subject let one alert hide the next from the same sender)."""
        now = self.clock()
        key = hashlib.sha256(text.encode()).hexdigest()
        self.last_seen = {k: t for k, t in self.last_seen.items() if now - t < self.dedupe_seconds}
        if key in self.last_seen:
            self.stats["suppressed"] += 1
            return False
        self.last_seen[key] = now
        return self._deliver(text, now, urgent)

    def _deliver(self, text: str, now: float, urgent: bool = False) -> bool:
        if not self._room(now):
            self.held.append((urgent, text)); self.stats["held"] += 1
            return False
        if self.sent_at and now - self.sent_at[-1] < 1:
            self.sleep(1 - (now - self.sent_at[-1]))
            now = self.clock()
        self.sent_at.append(now); self.stats["sent"] += 1
        self.send(fit(text))     # the sender reports its own failures
        return True

    def flush(self) -> bool:
        """Held messages go out as digests, watched-subject alerts first; what this minute
        cannot take stays held for the next pass. Nothing is dropped."""
        if not self.held or not self._room(self.clock()):
            return False
        self.held.sort(key=lambda it: not it[0])   # stable: urgent first, then arrival
        urgent = {text for u, text in self.held if u}
        chunks, self.held = pack([text for _, text in self.held]), []
        for i, chunk in enumerate(chunks):
            if not self._room(self.clock()):
                self.held = [(m in urgent, m) for c in chunks[i:] for m in c]
                break
            head = f"[Quorum watch] digest {i + 1}/{len(chunks)}: {len(chunk)} message(s) held by the rate limit\n"
            self._deliver(head + SEP.join(chunk), self.clock())
        return True

    def summary(self) -> str:
        s = self.stats
        return f"{s['sent']} sent, {s['held']} held for digest, {s['suppressed']} repeats suppressed"
