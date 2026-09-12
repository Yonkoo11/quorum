"""Measure the six lenses and the quorum rule against a labelled corpus.

    python bench/run.py /tmp/smartbugs-curated > bench/BENCHMARK.md
    python bench/run.py /tmp/DeFiVulnLabs --labels bench/labels/defivulnlabs.json > bench/HELDOUT.md

Two corpus shapes are understood. SmartBugs-curated ships `vulnerabilities.json`, which labels
vulnerable LINES per file with one category per label; a label counts as a target when its line
falls inside a parsed function and its category maps to a risk Quorum covers. A hand-written
labels file (see `bench/labels/`) names the function and the risk directly and says which files
to scan.

Quorum reports (contract, function, risk), so the unit of comparison is the function. A finding
is a hit when it names a labelled function with its risk. Every other finding on the corpus is
counted as a false positive, which is the harsh reading: a corpus labels one bug per file, so
some of those may be real, unlabelled bugs. The number is still the one to publish.

The rule reproduced here is the swarm's own: a key is confirmed when two distinct lenses report
it (QUORUM_THRESHOLD). Memory recall between contracts is deliberately not used, so the result
does not depend on the order the files are read.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
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
Key = tuple[str, str, str]  # (file name, function, risk)


@dataclass
class Corpus:
    title: str
    commit: str
    files: list[tuple[str, Path]]                  # every file that is scanned
    targets: set[Key] = field(default_factory=set)
    labels_seen: Counter = field(default_factory=Counter)
    labels_outside: Counter = field(default_factory=Counter)


def function_at(functions, line):
    for fn in functions:
        end = fn.start_line + (fn.header + fn.body).count("\n")
        if fn.start_line <= line <= end:
            return fn.name
    return None


def _commit(root: Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def load_smartbugs(root: Path) -> Corpus:
    corpus = Corpus("SmartBugs-curated", _commit(root), [])
    for e in json.loads((root / "vulnerabilities.json").read_text()):
        path = root / e["path"]
        if not path.exists():
            continue
        corpus.files.append((e["name"], path))
        functions = parse_functions(path.read_text(errors="replace"))
        for v in e["vulnerabilities"]:
            risk = CATEGORY_TO_RISK.get(v["category"])
            if not risk:
                continue
            for line in v["lines"]:
                corpus.labels_seen[risk] += 1
                fn = function_at(functions, line)
                if fn is None:
                    corpus.labels_outside[risk] += 1
                else:
                    corpus.targets.add((e["name"], fn, risk))
    return corpus


def load_labels(root: Path, labels_path: Path) -> Corpus:
    spec = json.loads(labels_path.read_text())
    files = sorted(root.glob(spec["scan"]))
    corpus = Corpus(spec["corpus"], _commit(root), [(p.name, p) for p in files])
    for label in spec["labels"]:
        path = root / label["path"]
        corpus.labels_seen[label["risk"]] += 1
        if not path.exists():
            corpus.labels_outside[label["risk"]] += 1
            continue
        corpus.targets.add((path.name, label["function"], label["risk"]))
    return corpus


def load_corpus(root: str, labels: str | None) -> Corpus:
    return load_labels(Path(root), Path(labels)) if labels else load_smartbugs(Path(root))


def scan(corpus: Corpus):
    sightings: dict[Key, set[str]] = defaultdict(set)
    lens_hits: dict[str, set[Key]] = defaultdict(set)
    for name, path in corpus.files:
        src = path.read_text(errors="replace")
        for lens_name, lens in LENSES.items():
            for s in lens(name, src):
                key = (name, s.function, s.risk)
                sightings[key].add(lens_name)
                lens_hits[lens_name].add(key)
    return sightings, lens_hits


def pct(num: int, den: int) -> str:
    return f"{100 * num / den:.0f}%" if den else "n/a"


def row(risk: str | None, targets: set[Key], any_lens: set[Key], confirmed: set[Key]) -> str:
    t = {k for k in targets if risk is None or k[2] == risk}
    seen = {k for k in any_lens if risk is None or k[2] == risk}
    conf = {k for k in confirmed if risk is None or k[2] == risk}
    tp_any, tp = len(t & seen), len(t & conf)
    label = f"**{risk or 'all'}**" if risk is None else risk
    return (f"| {label} | {len(t)} | {len(seen)} | {tp_any} | {pct(tp_any, len(seen))} | {pct(tp_any, len(t))} "
            f"| **{len(conf)}** | {tp} | **{pct(tp, len(conf))}** | **{pct(tp, len(t))}** |")


def report(corpus: Corpus, sightings, lens_hits, command: str) -> None:
    confirmed = {k for k, lenses in sightings.items() if len(lenses) >= QUORUM_THRESHOLD}
    candidates = {k for k, lenses in sightings.items() if len(lenses) < QUORUM_THRESHOLD}
    any_lens = set(sightings)
    targets = corpus.targets

    print(f"# Benchmark — the six lenses on {corpus.title}\n")
    print(f"Run {date.today().isoformat()} · corpus commit `{corpus.commit}` · {len(corpus.files)} files scanned · "
          f"{len(targets)} targets · quorum threshold {QUORUM_THRESHOLD} · `{command}`\n")
    print("Unit: a (file, function, risk). A target is a labelled function whose bug maps to a risk Quorum "
          "covers. Precision counts every finding not on a target as false, including hits on files the "
          "corpus labels for some other bug.\n")
    print("| risk | targets | any-lens found | true | precision | recall | **quorum confirmed** | true | **precision** | **recall** |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in RISKS:
        print(row(r, targets, any_lens, confirmed))
    print(row(None, targets, any_lens, confirmed))

    if sum(corpus.labels_outside.values()):
        print("\n## Labels the benchmark could not use\n")
        print("| risk | labels | outside any parsed function |\n|---|---|---|")
        for r in RISKS:
            print(f"| {r} | {corpus.labels_seen[r]} | {corpus.labels_outside[r]} |")
        print("\nA label whose line is not inside a function `FUNC` can parse has no function to attach to and "
              "is dropped from the targets. That flatters recall.")

    print("\n## Per lens\n\n| lens | sightings | on a target |\n|---|---|---|")
    for lens_name in LENSES:
        hits = lens_hits[lens_name]
        print(f"| {lens_name} | {len(hits)} | {len(hits & targets)} |")
    print(f"\nCandidates held back by the rule (one lens only): {len(candidates)}, of which on a target: "
          f"{len(candidates & targets)}.\n")

    print("## Confirmed findings that are not on a labelled target\n")
    for name, fn, risk in sorted(confirmed - targets):
        print(f"- `{name}` `{fn}` {risk} — {', '.join(sorted(sightings[(name, fn, risk)]))}")
    print("\n## Targets the rule missed\n")
    for name, fn, risk in sorted(targets - confirmed):
        seen = sorted(sightings.get((name, fn, risk), []))
        print(f"- `{name}` `{fn}` {risk} — seen by {', '.join(seen) if seen else 'no lens'}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("corpus", help="corpus checkout")
    ap.add_argument("--labels", help="hand-written labels file; without it the SmartBugs layout is assumed")
    args = ap.parse_args(argv)
    corpus = load_corpus(args.corpus, args.labels)
    sightings, lens_hits = scan(corpus)
    command = "python bench/run.py <corpus>" + (f" --labels {args.labels}" if args.labels else "")
    report(corpus, sightings, lens_hits, command)


if __name__ == "__main__":
    main()
