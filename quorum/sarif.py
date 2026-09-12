"""Confirmed findings as SARIF 2.1.0, for the GitHub Security tab and any SARIF viewer.

A Quorum finding is not a line number. Each result names the two lenses that agreed, the
different evidence each one read, and the idiom signature the swarm will recognise it by. Only
confirmed and recalled findings are written: a candidate seen by one lens is not a finding, and
the export does not pretend otherwise.
"""

from __future__ import annotations

import json
from pathlib import Path

from .agents import LENSES
from .swarm import RunReport

VERSION = "0.1.0"
RULES = {
    "reentrancy": "An external call is made before the state it depends on is written, in a function with no guard.",
    "unguarded-state-write": "Storage that looks privileged is written by a function anyone can call.",
    "unsafe-math": "Arithmetic that can wrap or lose precision.",
}
NOTICE = "Not a vulnerability claim: two independent readings agreed on a shape worth review."


def _what_it_reads(lens: str) -> str:
    doc = (LENSES[lens].__doc__ or "").strip()
    return doc.removeprefix("Evidence: ").rstrip(".")


def _message(f: dict) -> str:
    where = f"{f['risk']} in {f['contract']}:{f['function']}."
    witnesses = f.get("witnesses") or {f["lens"]: {"line": f["line"], "evidence": f["evidence"]}}
    seen = "; ".join(f"{lens} (line {w['line']}) reads: {_what_it_reads(lens)}: `{w['evidence']}`"
                     for lens, w in sorted(witnesses.items()))
    if f.get("via") == "recall":
        opening = (f"Recognised from memory. This idiom was confirmed earlier on {f.get('first_confirmed_on')} "
                   f"by two lenses; one sighting is enough the second time.")
    else:
        opening = "Two lenses agreed from different evidence."
    return f"{where} {opening} {seen}. {NOTICE} Idiom signature {f['signature']}."


def _result(f: dict, locations: dict[str, str]) -> dict:
    return {
        "ruleId": f["risk"],
        "level": "warning",
        "message": {"text": _message(f)},
        "locations": [{"physicalLocation": {
            "artifactLocation": {"uri": locations.get(f["contract"], f["contract"])},
            "region": {"startLine": max(1, int(f["line"]))},
        }}],
        "partialFingerprints": {"quorum/idiom/v1": f["signature"]},
        "properties": {"seenBy": f.get("seen_by", []), "confirmedVia": f.get("via", "quorum")},
    }


def to_sarif(report: RunReport, locations: dict[str, str]) -> dict:
    """`locations` maps a target name (what the swarm calls the file) to its path from the repo root."""
    rules = [{
        "id": risk,
        "name": risk,
        "shortDescription": {"text": text},
        "fullDescription": {"text": f"{text} Published only when two lenses that read different evidence agree. {NOTICE}"},
        "helpUri": "https://runquorum.site/lenses/",
        "defaultConfiguration": {"level": "warning"},
    } for risk, text in RULES.items()]
    findings = [{**f, "via": "recall"} for f in report.recalled] + [{**f, "via": "quorum"} for f in report.promoted]
    results = [_result(f, locations) for f in findings]
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "Quorum", "version": VERSION, "informationUri": "https://runquorum.site",
                                "rules": rules}},
            "results": results,
        }],
    }


def write(report: RunReport, locations: dict[str, str], path: str) -> int:
    log = to_sarif(report, locations)
    Path(path).write_text(json.dumps(log, indent=2) + "\n")
    return len(log["runs"][0]["results"])
