"""Measure the six lenses and the quorum rule against SmartBugs-curated.

    git clone --depth 1 https://github.com/smartbugs/smartbugs-curated /tmp/smartbugs-curated
    python bench/run.py /tmp/smartbugs-curated > bench/BENCHMARK.md

The corpus labels vulnerable LINES per file and one category per label. Quorum reports
(contract, function, risk), so the unit of comparison here is the function: a label counts as
a target when its line falls inside a parsed function and its category maps to a risk Quorum
covers. A finding is a hit when it names that function with that risk. Every other finding on
the corpus is counted as a false positive, which is the harsh reading: the corpus labels one
category per file, so some of those may be real, unlabelled bugs. The number is still the one
to publish.

The rule reproduced here is the swarm's own: a key is confirmed when two distinct lenses
report it (QUORUM_THRESHOLD). Memory recall between contracts is deliberately not used, so the
result does not depend on the order the files are read.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quorum.agents import LENSES, parse_functions  # noqa: E402
from quorum.memory import QUORUM_THRESHOLD  # noqa: E402

CATEGORY_TO_RISK = {
    "reentrancy": "reentrancy",
    "access_control": "unguarded-state-write",
    "arithmetic": "unsafe-math",
}
RISKS = list(CATEGORY_TO_RISK.values())


def function_at(functions, line):
    for fn in functions:
        end = fn.start_line + (fn.header + fn.body).count("\n")
        if fn.start_line <= line <= end:
            return fn.name
    return None


def main(corpus: str) -> None:
    root = Path(corpus)
    entries = json.loads((root / "vulnerabilities.json").read_text())
    try:
        commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        commit = "unknown"

    targets: set[tuple[str, str, str]] = set()
    labels_outside = Counter()
    labels_seen = Counter()
    sightings: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    lens_hits: dict[str, set] = defaultdict(set)
    files = 0

    for e in entries:
        path = root / e["path"]
        if not path.exists():
            continue
        files += 1
        src = path.read_text(errors="replace")
        name = e["name"]
        functions = parse_functions(src)
        for v in e["vulnerabilities"]:
            risk = CATEGORY_TO_RISK.get(v["category"])
            if not risk:
                continue
            for line in v["lines"]:
                labels_seen[risk] += 1
                fn = function_at(functions, line)
                if fn is None:
                    labels_outside[risk] += 1
                else:
                    targets.add((name, fn, risk))
        for lens_name, lens in LENSES.items():
            for s in lens(name, src):
                key = (name, s.function, s.risk)
                sightings[key].add(lens_name)
                lens_hits[lens_name].add(key)

    confirmed = {k for k, lenses in sightings.items() if len(lenses) >= QUORUM_THRESHOLD}
    candidates = {k for k, lenses in sightings.items() if len(lenses) < QUORUM_THRESHOLD}
    any_lens = set(sightings)

    def row(risk):
        t = {k for k in targets if k[2] == risk}
        seen = {k for k in any_lens if k[2] == risk}
        conf = {k for k in confirmed if k[2] == risk}
        tp_any = len(t & seen)
        tp = len(t & conf)
        prec = f"{100 * tp / len(conf):.0f}%" if conf else "n/a"
        prec_any = f"{100 * tp_any / len(seen):.0f}%" if seen else "n/a"
        rec = f"{100 * tp / len(t):.0f}%" if t else "n/a"
        rec_any = f"{100 * tp_any / len(t):.0f}%" if t else "n/a"
        return risk, len(t), len(seen), tp_any, prec_any, rec_any, len(conf), tp, prec, rec

    print(f"# Benchmark — the six lenses on SmartBugs-curated\n")
    print(f"Run {date.today().isoformat()} · corpus commit `{commit}` · {files} files · quorum threshold {QUORUM_THRESHOLD} · "
          f"`python bench/run.py <corpus>`\n")
    print("Unit: a (contract, function, risk). A target is a labelled line inside a parsed function whose "
          "category maps to a risk Quorum covers. Precision counts every finding not on a target as false, "
          "including hits on files the corpus labels for some other category.\n")
    print("| risk | targets | any-lens found | true | precision | recall | **quorum confirmed** | true | **precision** | **recall** |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in RISKS:
        risk, nt, ns, tpa, pa, ra, nc, tpc, pc, rc = row(r)
        print(f"| {risk} | {nt} | {ns} | {tpa} | {pa} | {ra} | **{nc}** | {tpc} | **{pc}** | **{rc}** |")
    tp_all = len(targets & confirmed)
    tpa_all = len(targets & any_lens)
    print(f"| **all** | {len(targets)} | {len(any_lens)} | {tpa_all} | "
          f"{100 * tpa_all / len(any_lens):.0f}% | {100 * tpa_all / len(targets):.0f}% | "
          f"**{len(confirmed)}** | {tp_all} | **{100 * tp_all / len(confirmed):.0f}%** | **{100 * tp_all / len(targets):.0f}%** |")

    print("\n## Labels the benchmark could not use\n")
    print("| risk | labels | outside any parsed function |\n|---|---|---|")
    for r in RISKS:
        print(f"| {r} | {labels_seen[r]} | {labels_outside[r]} |")
    print("\nUnnamed 0.4-era fallback functions (`function () payable`) are not parsed by `FUNC`, so a label "
          "on one of them has no function to attach to and is dropped from the targets. That flatters recall.\n")

    print("## Per lens\n\n| lens | sightings | on a target |\n|---|---|---|")
    for lens_name in LENSES:
        hits = lens_hits[lens_name]
        print(f"| {lens_name} | {len(hits)} | {len(hits & targets)} |")

    print(f"\nCandidates held back by the rule (one lens only): {len(candidates)}, of which on a target: {len(candidates & targets)}.\n")

    print("## Confirmed findings that are not on a labelled target\n")
    fps = sorted(confirmed - targets)
    for name, fn, risk in fps:
        print(f"- `{name}` `{fn}` {risk} — {', '.join(sorted(sightings[(name, fn, risk)]))}")
    print("\n## Targets the rule missed\n")
    for name, fn, risk in sorted(targets - confirmed):
        seen = sorted(sightings.get((name, fn, risk), []))
        print(f"- `{name}` `{fn}` {risk} — seen by {', '.join(seen) if seen else 'no lens'}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
