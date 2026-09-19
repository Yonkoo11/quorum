"""Measure the eight lenses against findings from recent public audit contests.

    python bench/modern.py <workdir> --labels bench/labels/modern-c4.json > bench/MODERN.md

The corpus is many repositories, one per contest, each checked out at exactly the commit its
report links to. A target is a High or Medium finding whose bug is one of the four shapes Quorum's
lens pairs look for, named by (contest, file, function, risk). The labels were written from the
reports and the source alone, before any lens was run, and every finding in every report was
classified, including the ones that are not Quorum shapes: that count is the first number this
file reports, because it bounds what the tool could ever find here.

Scoring is the same harsh rule as the other corpora: a confirmation that does not name a labelled
function counts false, even though these repositories contain far more code than the audit scope
and an audit publishes only what it found. The unit is the function, and the rule is the swarm's
own, two distinct lenses on one key, with memory recall deliberately unused.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench.run import Corpus, RISKS, pct, row  # noqa: E402
from quorum.agents import LENSES  # noqa: E402
from quorum.memory import QUORUM_THRESHOLD  # noqa: E402

# Dependencies, tests and build output are not the audited code and are not scanned.
SKIP_DIR = ("/lib/", "/node_modules/", "/test/", "/tests/", "/script/", "/scripts/", "/mocks/", "/mock/",
            "/forge-std/", "/openzeppelin", "/.git/", "/out/", "/cache/", "/artifacts/", "/fixtures/",
            "/testing/", "/harness/", "/echidna/", "/deprecated/", "/testdata/", "/templates/", "/examples/",
            "/dependencies/", "/vendor/", "/interfaces/")
SKIP_NAME = re.compile(r"(\.t\.sol|\.s\.sol|\.flat\.sol|-flatten\.sol|Test\w*\.sol|\w*Tests?\.sol|Mock\w*\.sol|"
                       r"\w*Mocks?\.sol|\w*Harness\.sol|I[A-Z]\w*\.sol)$")


def load(work: Path, labels_path: Path) -> tuple[Corpus, list[dict]]:
    findings = json.loads(labels_path.read_text())["findings"]
    contests = sorted({f["contest"] for f in findings})
    files: list[tuple[str, Path]] = []
    for contest in contests:
        root = work / "repos" / contest
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.sol")):
            rel = str(p.relative_to(root))
            if any(s in ("/" + rel.lower() + "/") for s in SKIP_DIR) or SKIP_NAME.search(p.name):
                continue
            files.append((f"{contest}/{rel}", p))
    corpus = Corpus(f"{len(contests)} recent audit contests", "per contest", files)
    for f in findings:
        if not f.get("risk"):
            continue
        corpus.labels_seen[f["risk"]] += 1
        name = f"{f['contest']}/{f['path']}"
        if not any(n == name for n, _ in files):
            corpus.labels_outside[f["risk"]] += 1
            continue
        corpus.targets.add((name, f["function"], f["risk"]))
    return corpus, findings


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("work", help="directory holding repos/<contest>")
    ap.add_argument("--labels", required=True)
    args = ap.parse_args(argv)
    corpus, findings = load(Path(args.work), Path(args.labels))

    sightings: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    lens_hits: dict[str, set] = defaultdict(set)
    for name, path in corpus.files:
        src = path.read_text(errors="replace")
        for lens_name, lens in LENSES.items():
            for s in lens(name, src):
                key = (name, s.function, s.risk)
                sightings[key].add(lens_name)
                lens_hits[lens_name].add(key)

    confirmed = {k for k, l in sightings.items() if len(l) >= QUORUM_THRESHOLD}
    candidates = {k for k, l in sightings.items() if len(l) < QUORUM_THRESHOLD}
    any_lens = set(sightings)
    targets = corpus.targets
    contests = sorted({f["contest"] for f in findings})
    shaped = [f for f in findings if f.get("risk")]
    cats = Counter(f.get("not_quorum_category") or "unclassified" for f in findings if not f.get("risk"))

    print(f"# The {len(LENSES)} lenses on recent audit contests\n")
    print(f"Run {date.today().isoformat()} · {len(contests)} contests, each at the commit its published report links · "
          f"{len(corpus.files):,} Solidity files scanned · quorum threshold {QUORUM_THRESHOLD} · "
          f"`python bench/modern.py <workdir> --labels {args.labels}`\n")

    print("## What share of modern findings is this tool even looking for\n")
    print(f"| | count |\n|---|---|")
    print(f"| High and Medium findings read and classified | {len(findings)} |")
    print(f"| of those, High | {sum(1 for f in findings if (f.get('severity') or '').lower() == 'high')} |")
    print(f"| in one of the four shapes Quorum's lenses look for | {len(shaped)} |")
    print(f"| not a shape Quorum looks for | {len(findings) - len(shaped)} |")
    print(f"| could not be tied to a file and function at that commit | {sum(1 for f in findings if f.get('locatable') is False)} |")
    print(f"\nThe four risks account for **{pct(len(shaped), len(findings))}** of what these audits reported at High "
          f"and Medium. Everything else was: " + ", ".join(f"{c} {n}" for c, n in cats.most_common()) + ".\n")
    print("That number is the ceiling on this tool's usefulness against a modern audit, before asking whether it "
          "finds the ones it is looking for. It is a line-reading scanner for four bug shapes, not an auditor.\n")

    print("## Of the shapes it does look for\n")
    print("| risk | targets | any-lens found | true | precision | recall | **quorum confirmed** | true | **precision** | **recall** |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in RISKS:
        print(row(r, targets, any_lens, confirmed))
    print(row(None, targets, any_lens, confirmed))
    if sum(corpus.labels_outside.values()):
        print(f"\n{sum(corpus.labels_outside.values())} labelled target(s) sit in a file the scan skips "
              f"(a dependency, a test, an interface) and are dropped from the table.")

    print("\n## Every labelled target, and what the lenses did with it\n")
    for name, fn, risk in sorted(targets):
        seen = sorted(sightings.get((name, fn, risk), []))
        verdict = "CONFIRMED" if (name, fn, risk) in confirmed else ("candidate" if seen else "missed")
        print(f"- `{name}` `{fn}` {risk} — {verdict}" + (f", seen by {', '.join(seen)}" if seen else ", seen by no lens"))

    print("\n## Per lens\n\n| lens | sightings | on a target |\n|---|---|---|")
    for lens_name in LENSES:
        print(f"| {lens_name} | {len(lens_hits[lens_name]):,} | {len(lens_hits[lens_name] & targets)} |")
    print(f"\nCandidates held back by the rule (one lens only): {len(candidates):,}. "
          f"Confirmations that name no labelled finding: {len(confirmed - targets):,}.\n")

    print("## Contests\n\n| contest | findings | Quorum-shaped | files scanned | confirmations |\n|---|---|---|---|---|")
    for c in contests:
        fs = [f for f in findings if f["contest"] == c]
        n_files = sum(1 for n, _ in corpus.files if n.startswith(c + "/"))
        n_conf = sum(1 for k in confirmed if k[0].startswith(c + "/"))
        print(f"| {c} | {len(fs)} | {sum(1 for f in fs if f.get('risk'))} | {n_files} | {n_conf} |")


if __name__ == "__main__":
    main()
