"""Every Sibyl Memory read and write in Quorum happens in this file.

Quorum's agents never talk to each other. They coordinate entirely through the
five Sibyl Memory tiers, and the swarm's output is a pure function of what is
already in memory:

  HOT       state/      work claims  -> stops two agents scanning the same thing
  WARM      entities/   candidate findings + which lenses corroborated them
  COLD      journal/    append-only log of every sighting and promotion
  REFERENCE reference/  patterns that reached quorum, recognised on sight forever
  ARCHIVE   archive/    retired findings, suppressed in every later session

Run with memory disabled (`quorum run --no-memory`) and the swarm loses claims,
corroboration, recall and suppression at once: it duplicates work, never reaches
quorum, and re-reports findings a human already retired. That is the deletion
test, implemented as a runtime flag rather than a claim in a README.
"""

from __future__ import annotations

import hashlib
import json
import re
import os
import random
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

from sibyl_memory_client import MemoryClient, NotFoundError

QUORUM_THRESHOLD = 2
DEFAULT_DB = "quorum-memory.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _elapsed(since: str | None) -> float | None:
    """Seconds a finding waited for a second lens to agree with it."""
    if not since:
        return None
    try:
        return round((datetime.now(timezone.utc) - datetime.fromisoformat(since)).total_seconds(), 3)
    except ValueError:
        return None


PRIVILEGED_WORDS = re.compile(r"(owner|admin|treasury|fee|rate|price|oracle|paused|beneficiary|supply)", re.I)
CHAIN = re.compile(r"\b[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+\b")
IDENT = re.compile(r"\b[A-Za-z_]\w*\b")


def _class_of(token: str) -> str:
    return "PRIV" if PRIVILEGED_WORDS.search(token) else "X"


ASSIGN = re.compile(r"^\s*([A-Za-z_][\w.]*)\s*(\[[^\]]*\])?\s*(\+=|-=|=)(?!=)")


def signature(risk: str, evidence: str) -> str:
    """Hash the *idiom* on a line, not the identifiers on it.

    This is what lets a pattern the swarm confirmed on one contract be
    recognised in a completely different one. `msg.sender.call{value: amount}("")`
    and `protocolFeeDestination.call{value: protocolFee}("")` are the same idiom
    and hash the same; `weth.deposit{value: amountETH}()` is a different idiom
    and does not. Receiver and argument names collapse to X, the method name
    survives, and the target of a write keeps its class, so writing a
    privileged-looking variable stays distinct from writing an ordinary one.
    """
    text = re.sub(r'"[^"]*"|\'[^\']*\'', "S", evidence)
    text = re.sub(r"\b\d+(e\d+)?\b", "N", text)

    prefix = ""
    m = ASSIGN.match(text)
    if m:
        target, index, op = m.group(1), m.group(2), m.group(3)
        cls = "PRIV" if PRIVILEGED_WORDS.search(target) else "VAR"
        if index:
            cls += "MAP"
        prefix = f"{cls}{op}"
        text = text[m.end():]

    text = CHAIN.sub(lambda mm: "X." + mm.group(0).split(".")[-1], text)
    text = IDENT.sub(lambda mm: mm.group(0) if mm.group(0) in {"S", "N"} else "X", text)
    text = re.sub(r"X\s*\[[^\]]*\]", "X", text)
    shape = prefix + re.sub(r"\s+", "", text)
    return f"{risk}:{hashlib.sha256(shape.encode()).hexdigest()[:16]}"


def _retry(fn, *args, **kwargs):
    """SQLite is one file and the swarm is many processes.

    Every agent writes to the same memory, so a write can land while a peer holds
    the database. Back off and try again rather than losing the sighting.
    """
    delay = 0.02
    last: Exception | None = None
    for _ in range(10):
        try:
            return fn(*args, **kwargs)
        except sqlite3.OperationalError as exc:  # pragma: no cover - timing dependent
            if "locked" not in str(exc).lower() and "busy" not in str(exc).lower():
                raise
            last = exc
            time.sleep(delay)
            delay = min(delay * 1.7, 0.5)
    raise last  # type: ignore[misc]


class SwarmMemory:
    """The swarm's shared brain. All five tiers, all load-bearing."""

    enabled = True

    def __init__(self, path: str = DEFAULT_DB) -> None:
        self.client = _retry(MemoryClient.local, path)
        self.path = path

    # ---------- HOT / state: work claims (agent-to-agent coordination) ----------

    def claim_work(self, target: str, lens: str, agent_id: str | None = None) -> bool:
        """Claim a (target, lens) unit. False means a peer already holds it.

        Claiming is optimistic, because many agent processes share one memory and
        a read-then-write is not atomic: an agent writes its own id into the
        claim, waits out the window in which a peer could be writing too, then
        reads the claim back. Exactly one agent sees its own id and proceeds; the
        others stand down. This is the only coordination mechanism in Quorum, and
        it lives entirely in the HOT tier.
        """
        agent_id = agent_id or f"pid-{os.getpid()}"
        key = f"claim:{target}:{lens}"

        row = self.client.get_state(key)
        body = (row or {}).get("body") or {}
        if body.get("claimed_by") and not body.get("released_at"):
            return False

        _retry(self.client.set_state, key, {"lens": lens, "target": target,
                                            "claimed_by": agent_id, "claimed_at": _now()})
        time.sleep(0.03 + random.random() * 0.02)

        confirmed = (self.client.get_state(key) or {}).get("body") or {}
        return confirmed.get("claimed_by") == agent_id

    def clear_claims(self, target: str, lens_names: list[str]) -> None:
        for lens in lens_names:
            self.client.set_state(f"claim:{target}:{lens}", {"released_at": _now()})

    # ---------- WARM / entities: candidate findings and corroboration ----------

    def record_sighting(self, key: str, lens: str, meta: dict[str, Any]) -> dict[str, Any]:
        """Add one lens's sighting to a candidate finding and return its new state."""
        body = self.get_finding(key) or {}
        seen_by = sorted(set(body.get("seen_by", [])) | {lens})
        witnesses = {**body.get("witnesses", {}), lens: {"line": meta.get("line"), "evidence": meta.get("evidence")}}
        body = {
            **meta,
            "seen_by": seen_by,
            "witnesses": witnesses,  # what each lens saw, kept per lens so a finding can name both
            "corroborations": len(seen_by),
            "status": body.get("status", "candidate"),
            "first_seen": body.get("first_seen", _now()),
            "last_seen": _now(),
        }
        _retry(self.client.set_entity, "finding", key, body)
        return body

    def get_finding(self, key: str) -> dict[str, Any] | None:
        try:
            found = self.client.get_entity("finding", key)
        except NotFoundError:
            return None
        return (found or {}).get("body")

    def findings(self, status: str | None = None) -> list[dict[str, Any]]:
        out = []
        for row in self.client.list_entities(category="finding", limit=500):
            body = row.get("body") or {}
            if status is None or body.get("status") == status:
                out.append({"key": row["name"], **body})
        return out

    # ---------- COLD / journal: append-only audit trail ----------

    def log(self, evaluated: Any, acted: Any, forward: Any = None) -> str:
        return _retry(self.client.write_event, evaluated=evaluated, acted=acted, forward=forward)

    def events(self, limit: int = 50, since: str | None = None, until: str | None = None) -> list[dict[str, Any]]:
        """Read the journal, optionally only the slice inside a time window."""
        return self.client.read_events(limit=limit, since=since, until=until)

    def learned_since(self, since: str) -> list[dict[str, Any]]:
        """Patterns the swarm confirmed after a point in time.

        Time-travel over the REFERENCE tier: what does the swarm know now that it
        did not know when you last looked?
        """
        return [p for p in self.confirmed_patterns() if (p.get("confirmed_at") or "") >= since]

    # ---------- REFERENCE: patterns that reached quorum ----------

    def promote(self, key: str, body: dict[str, Any]) -> None:
        """Quorum reached, or an already-confirmed idiom recognised again.

        A pattern is confirmed once. Recognising it in a later contract adds to
        its provenance rather than rewriting it: the swarm must never lose the
        record of where it originally paid for this knowledge.
        """
        sig = body["signature"]
        contract = body.get("contract")
        existing = self.known_pattern(sig)

        if existing:
            seen_again = list(dict.fromkeys(existing.get("recognised_on", []) + [contract]))
            reference = {
                **existing,
                "recognised_on": [c for c in seen_again if c and c != existing.get("first_confirmed_on")],
            }
        else:
            reference = {
                "risk": body["risk"],
                "signature": sig,
                "confirmed_by": body["seen_by"],
                "first_confirmed_on": contract,
                "evidence": body.get("evidence", ""),
                "confirmed_at": _now(),
                "held_as_candidate_seconds": _elapsed(body.get("first_seen")),
                "recognised_on": [],
            }

        _retry(self.client.set_reference, f"pattern:{sig}", reference)
        _retry(self.client.set_entity, "finding", key,
               {**body, "status": "confirmed", "confirmed_via": body.get("via", "quorum")})

    @staticmethod
    def _body(row: Any) -> dict[str, Any] | None:
        """Reference bodies come back as JSON text; give callers a dict either way."""
        if not row:
            return None
        body = row.get("body") if isinstance(row, dict) else row
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                return None
        return body if isinstance(body, dict) else None

    def known_pattern(self, sig: str) -> dict[str, Any] | None:
        """Has the swarm confirmed this shape before, in any earlier session?"""
        return self._body(self.client.get_reference(f"pattern:{sig}"))

    def import_pattern(self, revealed: dict[str, Any], claim_tx: str, burn_tx: str) -> bool:
        """Learn a pattern another swarm confirmed, revealed and paid to publish.

        This is the only way knowledge enters the REFERENCE tier without this
        swarm reaching quorum itself, so the bar is the on-chain one: the caller
        has already checked the reveal matches the claim digest and the claim's
        fee was really burned. Returns False if the shape is already known.
        """
        sig = revealed["signature"]
        if self.known_pattern(sig):
            return False
        reference = {
            "risk": revealed["risk"],
            "signature": sig,
            "confirmed_by": revealed.get("corroborated_by", []),
            "first_confirmed_on": revealed.get("contract"),
            "evidence": "",
            "confirmed_at": _now(),
            "recognised_on": [],
            "imported_from": {"claim_tx": claim_tx, "fee_burn_tx": burn_tx},
        }
        _retry(self.client.set_reference, f"pattern:{sig}", reference)
        self.log(evaluated={"claim_tx": claim_tx}, acted={"imported": sig}, forward={"fee_burn_tx": burn_tx})
        return True

    def confirmed_patterns(self) -> list[dict[str, Any]]:
        hits = self.client.search("signature", limit=200, tiers=("reference",))
        out = []
        for h in list(hits):
            body = self._body(h)
            if body and body.get("signature") and "reason" not in body:
                out.append(body)
        return out

    # ---------- ARCHIVE: retired findings stay retired ----------

    def retire(self, key: str, reason: str) -> bool:
        """A human calls this a false positive. No later session re-reports it."""
        body = self.get_finding(key)
        if body is None:
            return False
        _retry(
            self.client.set_reference,
            f"retired:{body['signature']}",
            {"risk": body["risk"], "signature": body["signature"], "reason": reason, "retired_at": _now()},
        )
        _retry(self.client.archive_entity, "finding", key, reason=reason)
        self.log(evaluated={"finding": key}, acted={"retired": reason}, forward={"suppress": body["signature"]})
        return True

    def is_retired(self, sig: str) -> dict[str, Any] | None:
        return self._body(self.client.get_reference(f"retired:{sig}"))

    # ---------- housekeeping ----------

    def status(self) -> dict[str, Any]:
        findings = self.findings()
        return {
            "db": self.path,
            "tier": self.client.get_tier(),
            "candidates": sum(1 for f in findings if f.get("status") == "candidate"),
            "confirmed": sum(1 for f in findings if f.get("status") == "confirmed"),
            "patterns": len(self.confirmed_patterns()),
            "events": len(self.events(limit=500)),
            "bytes": self.client.free_tier_status()["db_size_bytes"],
        }


class NoMemory(SwarmMemory):
    """The ablation. Same interface, forgets everything the instant it is written.

    This is the deletion test the rules ask for: every claim succeeds (so agents
    duplicate each other), every sighting looks like the first (so corroboration
    never accumulates and quorum is never reached), nothing is ever recognised
    from an earlier session, and retirements do not stick.
    """

    enabled = False

    def __init__(self, path: str | None = None) -> None:  # noqa: D107
        self.path = None

    def claim_work(self, target: str, lens: str, agent_id: str | None = None) -> bool:
        return True

    def clear_claims(self, target: str, lens_names: list[str]) -> None:
        return None

    def record_sighting(self, key: str, lens: str, meta: dict[str, Any]) -> dict[str, Any]:
        return {**meta, "seen_by": [lens], "corroborations": 1, "status": "candidate"}

    def get_finding(self, key: str) -> dict[str, Any] | None:
        return None

    def findings(self, status: str | None = None) -> list[dict[str, Any]]:
        return []

    def log(self, evaluated: Any, acted: Any, forward: Any = None) -> str:
        return ""

    def events(self, limit: int = 50, since: str | None = None, until: str | None = None) -> list[dict[str, Any]]:
        return []

    def learned_since(self, since: str) -> list[dict[str, Any]]:
        return []

    def promote(self, key: str, body: dict[str, Any]) -> None:
        return None

    def known_pattern(self, sig: str) -> dict[str, Any] | None:
        return None

    def import_pattern(self, revealed: dict[str, Any], claim_tx: str, burn_tx: str) -> bool:
        return False

    def confirmed_patterns(self) -> list[dict[str, Any]]:
        return []

    def retire(self, key: str, reason: str) -> bool:
        return False

    def is_retired(self, sig: str) -> dict[str, Any] | None:
        return None

    def status(self) -> dict[str, Any]:
        return {"db": None, "tier": "ablated", "candidates": 0, "confirmed": 0, "patterns": 0, "events": 0, "bytes": 0}
