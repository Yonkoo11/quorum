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
from datetime import datetime, timezone
from typing import Any

from sibyl_memory_client import MemoryClient, NotFoundError

QUORUM_THRESHOLD = 2
DEFAULT_DB = "quorum-memory.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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


class SwarmMemory:
    """The swarm's shared brain. All five tiers, all load-bearing."""

    enabled = True

    def __init__(self, path: str = DEFAULT_DB) -> None:
        self.client = MemoryClient.local(path)
        self.path = path

    # ---------- HOT / state: work claims (agent-to-agent coordination) ----------

    def claim_work(self, target: str, lens: str) -> bool:
        """Claim a (target, lens) unit. False means another agent already has it.

        This is the only thing stopping two agents from doing identical work, and
        it holds across processes and sessions because it lives in memory rather
        than in any one agent's head.
        """
        key = f"claim:{target}:{lens}"
        row = self.client.get_state(key)
        body = (row or {}).get("body") or {}
        if body.get("claimed_at") and not body.get("released_at"):
            return False
        self.client.set_state(key, {"lens": lens, "target": target, "claimed_at": _now()})
        return True

    def clear_claims(self, target: str, lens_names: list[str]) -> None:
        for lens in lens_names:
            self.client.set_state(f"claim:{target}:{lens}", {"released_at": _now()})

    # ---------- WARM / entities: candidate findings and corroboration ----------

    def record_sighting(self, key: str, lens: str, meta: dict[str, Any]) -> dict[str, Any]:
        """Add one lens's sighting to a candidate finding and return its new state."""
        body = self.get_finding(key) or {}
        seen_by = sorted(set(body.get("seen_by", [])) | {lens})
        body = {
            **meta,
            "seen_by": seen_by,
            "corroborations": len(seen_by),
            "status": body.get("status", "candidate"),
            "first_seen": body.get("first_seen", _now()),
            "last_seen": _now(),
        }
        self.client.set_entity("finding", key, body)
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
        return self.client.write_event(evaluated=evaluated, acted=acted, forward=forward)

    def events(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.client.read_events(limit=limit)

    # ---------- REFERENCE: patterns that reached quorum ----------

    def promote(self, key: str, body: dict[str, Any]) -> None:
        """Quorum reached. The pattern becomes permanent swarm knowledge."""
        sig = body["signature"]
        self.client.set_reference(
            f"pattern:{sig}",
            {
                "risk": body["risk"],
                "signature": sig,
                "confirmed_by": body["seen_by"],
                "first_confirmed_on": body.get("contract"),
                "evidence": body.get("evidence", ""),
                "confirmed_at": _now(),
            },
        )
        self.client.set_entity("finding", key, {**body, "status": "confirmed"})

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
        self.client.set_reference(
            f"retired:{body['signature']}",
            {"risk": body["risk"], "signature": body["signature"], "reason": reason, "retired_at": _now()},
        )
        self.client.archive_entity("finding", key, reason=reason)
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

    def claim_work(self, target: str, lens: str) -> bool:
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

    def events(self, limit: int = 50) -> list[dict[str, Any]]:
        return []

    def promote(self, key: str, body: dict[str, Any]) -> None:
        return None

    def known_pattern(self, sig: str) -> dict[str, Any] | None:
        return None

    def confirmed_patterns(self) -> list[dict[str, Any]]:
        return []

    def retire(self, key: str, reason: str) -> bool:
        return False

    def is_retired(self, sig: str) -> dict[str, Any] | None:
        return None

    def status(self) -> dict[str, Any]:
        return {"db": None, "tier": "ablated", "candidates": 0, "confirmed": 0, "patterns": 0, "events": 0, "bytes": 0}
