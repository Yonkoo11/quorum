"""Build a scan corpus from the 2026 hacks whose shape these lenses read for.

    python3 bench/fetch_hacks.py /tmp/hacks-2026
    python bench/run.py /tmp/hacks-2026 --labels bench/labels/hacks-recall.json > bench/HACKS-RECALL.md

Every other corpus here is somebody else's test suite. This one is the code that actually lost
money in 2026: for each hack in labels/hacks-2026.json whose root-cause note names a contract with
readable source, the verified source of that contract is downloaded and labelled with the function
the note blames. Proxies are not fetched; the address in the labels is the implementation or facet
that holds the logic, because scanning a proxy would score a miss on code the bug is not in.

A hack is skipped when its source cannot be read, and the script says which and why rather than
quietly shrinking the corpus. Those skips are the ceiling on any recall number taken from it.
"""

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from quorum import targets  # noqa: E402

LABELS = pathlib.Path(__file__).parent / "labels" / "hacks-2026.json"
OUT_LABELS = pathlib.Path(__file__).parent / "labels" / "hacks-recall.json"
RISK = {"access-control": "unguarded-state-write", "reentrancy": "reentrancy",
        "arithmetic": "unsafe-math", "accounting-mismatch": "accounting-mismatch"}


def main(workdir: str):
    root = pathlib.Path(workdir)
    src = root / "src"
    src.mkdir(parents=True, exist_ok=True)
    hacks = [h for h in json.loads(LABELS.read_text())["hacks"] if h.get("quorum_shape")]

    labels, skipped = [], []
    for h in hacks:
        if h.get("source") != "verified" or not h.get("address"):
            skipped.append((h["file"], h.get("source") or "no address"))
            continue
        try:
            name, code = targets.fetch_source(h["address"], h["chain"], timeout=60)
        except Exception as exc:                      # an explorer that answers differently today
            skipped.append((h["file"], str(exc)[-60:]))
            continue
        path = src / f"{name}.sol"
        path.write_text(code)
        if h.get("function"):
            labels.append({"path": f"src/{path.name}", "function": h["function"],
                           "risk": RISK[h["category"]],
                           "why": f"{h['file']}: {h['why']}"})
        else:
            skipped.append((h["file"], "fetched, but the note pins no single function"))

    OUT_LABELS.write_text(json.dumps({
        "corpus": "2026 hacks, verified victim source",
        "source": "https://github.com/SunWeb3Sec/DeFiHackLabs",
        "scan": "src/*.sol",
        "how_labelled": (
            "Derived by bench/fetch_hacks.py from bench/labels/hacks-2026.json, which classifies the "
            "53 hacks of 2026 that DeFiHackLabs reproduces with a root-cause note. Each label names "
            "the function that note blames, in the implementation or facet that holds it rather than "
            "the proxy in front of it. Only hacks whose victim source can actually be read are here; "
            "the rest are listed as skipped by the same script and are the ceiling on any recall "
            "number taken from this corpus."),
        "labels": sorted(labels, key=lambda x: x["path"]),
    }, indent=2) + "\n")

    print(f"fetched {len(labels)} labelled contract(s) into {src}")
    for f, why in skipped:
        print(f"  skipped {f}: {why}")
    print(f"{len(labels)} labelled, {len(skipped)} skipped, {len(hacks)} shaped hacks in total")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/hacks-2026")
