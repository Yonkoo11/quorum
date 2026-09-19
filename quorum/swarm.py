"""Orchestration: claim, corroborate, promote.

The swarm has no message bus, no shared queue and no direct calls between
agents. A lens learns what its peers are doing only by reading Sibyl Memory,
and it publishes only by writing to it.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .agents import LENSES, Project, Sighting
from .memory import QUORUM_THRESHOLD, SwarmMemory


@dataclass
class RunReport:
    promoted: list[dict] = field(default_factory=list)      # reached quorum this run
    recalled: list[dict] = field(default_factory=list)      # recognised from an earlier session
    candidates: list[dict] = field(default_factory=list)    # seen once, not published
    standing: list[dict] = field(default_factory=list)      # confirmed in an earlier run, still present
    suppressed: list[dict] = field(default_factory=list)    # retired by a human, stayed retired
    duplicate_work: int = 0                                  # units skipped because a peer had them
    scanned: int = 0
    memory_enabled: bool = True

    def summary(self) -> str:
        return (
            f"scanned {self.scanned} lens-units | "
            f"confirmed {len(self.promoted)} | recalled {len(self.recalled)} | "
            f"candidates {len(self.candidates)} | suppressed {len(self.suppressed)} | "
            f"duplicate work avoided {self.duplicate_work}"
        )


def run_swarm(
    memory: SwarmMemory,
    targets: dict[str, str],
    threshold: int = QUORUM_THRESHOLD,
    fresh_claims: bool = False,
    agent_id: str | None = None,
) -> RunReport:
    report = RunReport(memory_enabled=memory.enabled)
    agent_id = agent_id or f"pid-{os.getpid()}"

    project = Project.read(targets)   # what each contract inherits, so a lens is not stuck inside one file
    for contract, src in targets.items():
        if fresh_claims:
            memory.clear_claims(contract, list(LENSES))

        for lens_name, lens in LENSES.items():
            # COORDINATION: memory decides whether this agent works at all.
            if not memory.claim_work(contract, lens_name, agent_id):
                report.duplicate_work += 1
                continue
            report.scanned += 1

            for s in lens(contract, src, project):
                _handle(memory, s, threshold, report)

    return report


def _split_witness(body: dict) -> bool:
    """For unsafe-math the two readings must be of the same sum: wrap-lens on one line and bound-lens on
    another is two candidates, not a finding. Every other pair agrees on a function. Added after the
    Robinhood Chain run, where most false unsafe-math confirmations were a checked `+=` on one line and
    an `unchecked` add on another (bench/ROBINHOOD.md)."""
    if body.get("risk") != "unsafe-math":
        return False
    lines = {w.get("line") for w in (body.get("witnesses") or {}).values()}
    return len(lines) > 1


def _handle(memory: SwarmMemory, s: Sighting, threshold: int, report: RunReport) -> None:
    sig = s.signature

    # ARCHIVE: a human already threw this shape away. Never surface it again.
    retired = memory.is_retired(sig)
    if retired:
        report.suppressed.append({**s.as_dict(), "reason": retired.get("reason")})
        memory.log(evaluated=s.as_dict(), acted={"suppressed": retired.get("reason")})
        return

    existing = memory.get_finding(s.key) or {}
    if existing.get("status") == "confirmed":
        # Still there on a later run. Not new, so not promoted again, but a report that dropped it
        # would tell the Security tab the bug was fixed.
        if not any(f.get("key") == s.key for f in report.standing):
            report.standing.append({**existing, "key": s.key, "via": existing.get("confirmed_via", "quorum")})
        return

    body = memory.record_sighting(s.key, s.lens, s.as_dict())
    memory.log(evaluated={"lens": s.lens, "key": s.key}, acted={"corroborations": body["corroborations"]})

    # REFERENCE: confirmed in an earlier session on a different contract.
    # One sighting is enough, because the swarm already paid for this knowledge.
    known = memory.known_pattern(sig)
    if known and memory.trust_of(known) == "local":
        memory.promote(s.key, {**body, "via": "recall"})
        report.recalled.append({**body, "first_confirmed_on": known.get("first_confirmed_on")})
        memory.log(evaluated={"key": s.key}, acted={"recalled_from": known.get("first_confirmed_on")},
                   forward={"promoted": sig})
        return
    if known:
        # Imported, so paid for by someone else and never corroborated here. A hint on the
        # candidate, not a confirmation: the finding still needs two local lenses.
        body = {**body, "hint": known.get("imported_from", {})}

    if body["corroborations"] >= threshold and not _split_witness(body):
        memory.promote(s.key, body)
        report.promoted.append(body)
        memory.log(evaluated={"key": s.key}, acted={"quorum": body["seen_by"]}, forward={"pattern": sig})
    else:
        report.candidates.append(body)
