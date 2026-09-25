"""Count the 2026 hack classification from bench/labels/hacks-2026.json.

The table in HACKS-2026.md is printed by this script rather than typed, so the published number
and the per-file labels cannot drift apart. Run it with no arguments:

    python bench/hacks.py

Add --check to compare the labels against a clone of DeFiHackLabs, which verifies that every
labelled file exists and that no file carrying a root-cause note was left out:

    python bench/hacks.py --check /tmp/dhl
"""

import json
import pathlib
import sys

LABELS = pathlib.Path(__file__).parent / "labels" / "hacks-2026.json"


def load():
    return json.loads(LABELS.read_text())


def table(hacks):
    """The category table, most hacks first, ties broken by name so the order is stable."""
    cats = {}
    for h in hacks:
        total, shaped = cats.get(h["category"], (0, 0))
        cats[h["category"]] = (total + 1, shaped + bool(h["quorum_shape"]))
    rows = sorted(cats.items(), key=lambda kv: (-kv[1][0], kv[0]))

    out = ["| category | hacks | a shape Quorum reads for |", "|---|---|---|"]
    for name, (total, shaped) in rows:
        out.append(f"| {name} | {total} | {'**%d**' % shaped if shaped else '0'} |")
    n = len(hacks)
    shaped = sum(bool(h["quorum_shape"]) for h in hacks)
    out.append(f"| **total** | **{n}** | **{shaped}** |")
    return "\n".join(out), n, shaped


def check(root, hacks):
    """Every labelled file exists, and every file with a root-cause note is labelled."""
    tests = pathlib.Path(root) / "src" / "test"
    labelled = {h["file"] for h in hacks}
    missing = sorted(f for f in labelled if not (tests / f).exists())

    found = set()
    for path in sorted(tests.glob("2026-*/*.sol")):
        if "root cause" in path.read_text(errors="ignore").lower():
            found.add(str(path.relative_to(tests)))
    unlabelled = sorted(found - labelled)

    for f in missing:
        print(f"missing from the clone: {f}")
    for f in unlabelled:
        print(f"has a root-cause note but no label: {f}")
    print(f"{len(labelled)} labelled, {len(found)} with a note, "
          f"{len(missing)} missing, {len(unlabelled)} unlabelled")
    return not missing and not unlabelled


def main():
    hacks = load()["hacks"]
    if "--check" in sys.argv:
        sys.exit(0 if check(sys.argv[sys.argv.index("--check") + 1], hacks) else 1)

    md, n, shaped = table(hacks)
    print(md)
    print()
    print(f"{shaped} of {n}, about {round(100 * shaped / n)}%, are one of the four shapes "
          f"Quorum reads for.")


if __name__ == "__main__":
    main()
