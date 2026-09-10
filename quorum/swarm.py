"""Orchestration: claim, corroborate, promote.

The swarm has no message bus, no shared queue and no direct calls between
agents. A lens learns what its peers are doing only by reading Sibyl Memory,
and it publishes only by writing to it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .agents import LENSES, Sighting
from .memory import QUORUM_THRESHOLD, SwarmMemory


@dataclass
class RunReport:
    promoted: list[dict] = field(default_factory=list)      # reached quorum this run
    recalled: list[dict] = field(default_factory=list)      # recognised from an earlier session
    candidates: list[dict] = field(default_factory=list)    # seen once, not published
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
) -> RunReport:
    report = RunReport(memory_enabled=memory.enabled)

    for contract, src in targets.items():
        if fresh_claims:
            memory.clear_claims(contract, list(LENSES))

        for lens_name, lens in LENSES.items():
            # COORDINATION: memory decides whether this agent works at all.
            if not memory.claim_work(contract, lens_name):
                report.duplicate_work += 1
                continue
            report.scanned += 1

            for s in lens(contract, src):
                _handle(memory, s, threshold, report)

    return report


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
        return

    body = memory.record_sighting(s.key, s.lens, s.as_dict())
    memory.log(evaluated={"lens": s.lens, "key": s.key}, acted={"corroborations": body["corroborations"]})

    # REFERENCE: confirmed in an earlier session on a different contract.
    # One sighting is enough, because the swarm already paid for this knowledge.
    known = memory.known_pattern(sig)
    if known:
        memory.promote(s.key, {**body, "via": "recall"})
        report.recalled.append({**body, "first_confirmed_on": known.get("first_confirmed_on")})
        memory.log(evaluated={"key": s.key}, acted={"recalled_from": known.get("first_confirmed_on")},
                   forward={"promoted": sig})
        return

    if body["corroborations"] >= threshold:
        memory.promote(s.key, body)
        report.promoted.append(body)
        memory.log(evaluated={"key": s.key}, acted={"quorum": body["seen_by"]}, forward={"pattern": sig})
    else:
        report.candidates.append(body)
