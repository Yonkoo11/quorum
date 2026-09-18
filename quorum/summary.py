"""The run as a page for a pull request: the confirmed findings with both witnesses, and the counts.

Written by `quorum run --summary PATH`. The GitHub Action appends it to the job summary, where a
reviewer sees it from the pull request's checks; a workflow may also post it as a comment from a
job that runs no repository code. Candidates are counted, never listed: one lens is not a finding.
Source lines are escaped and cut, as in the SARIF, so a comment in a contract cannot plant a link.
"""
from __future__ import annotations

from .sarif import _what_it_reads
from .swarm import RunReport

MARK = "<!-- quorum-summary -->"


def _code(evidence: str) -> str:
    """One source line inside a code span: cut at 160 characters, backticks replaced so it cannot end the span."""
    return str(evidence)[:160].replace("`", "'").replace("\n", " ")


def markdown(report: RunReport, locations: dict[str, str]) -> str:
    found = report.promoted + report.recalled
    lines = [MARK, "## Quorum", ""]
    if not found:
        lines.append(f"Nothing confirmed. {report.scanned} lens-units read, {len(report.candidates)} candidate(s) seen by one lens and held back.")
    else:
        lines.append(f"{len(found)} finding(s) confirmed by two lenses each. {len(report.candidates)} candidate(s) seen by one lens and held back.")
        lines.append("")
        for f in found:
            where = locations.get(f["contract"], f["contract"])
            lines.append(f"**{f['risk']}** in `{where}` `{f['function']}`")
            witnesses = f.get("witnesses") or {f["lens"]: {"line": f["line"], "evidence": f["evidence"]}}
            for lens, w in sorted(witnesses.items()):
                lines.append(f"- {lens}, line {w['line']}: {_what_it_reads(lens)}. `{_code(w['evidence'])}`")
            if f.get("via") == "recall":
                lines.append(f"- recognised from memory: this idiom was confirmed earlier on {f.get('first_confirmed_on')}")
            lines.append("")
    lines.append("A finding is a shape worth review, not a vulnerability claim. Two independent readings agreed; a person decides.")
    return "\n".join(lines) + "\n"


def write(report: RunReport, locations: dict[str, str], path: str) -> None:
    with open(path, "w") as fh:
        fh.write(markdown(report, locations))
