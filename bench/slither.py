"""Score Slither on the same corpus, the same unit and the same harsh rule as bench/run.py.

    python bench/slither.py /tmp/smartbugs-curated > bench/SLITHER.md
    python bench/slither.py /tmp/DeFiVulnLabs --labels bench/labels/defivulnlabs.json --remap forge-std/=lib/forge-std/src/ ...

Slither is the static analyser every Solidity team already runs, so it is the baseline a
two-witness number has to be read against. Each file is compiled on its own with the compiler
its pragma asks for (via solc-select's SOLC_VERSION) and only the detectors that map onto the
three risks Quorum covers are counted:

    reentrancy             strict: reentrancy-eth, reentrancy-no-eth
                           loose:  + reentrancy-benign, reentrancy-events, reentrancy-unlimited-gas
    unguarded-state-write  strict: suicidal, arbitrary-send-eth, controlled-delegatecall,
                                   unprotected-upgrade, tx-origin
    unsafe-math            strict: divide-before-multiply
                           loose:  + tautology

"Strict" is what Slither itself rates Medium or High for that risk; "loose" adds the
Low/Informational detectors, which is the analogue of counting any single lens. A file Slither
cannot compile is a miss for every target in it, which is how SmartBugs scored tools too.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run import RISKS, Key, load_corpus, pct  # noqa: E402

DETECTORS = {
    "reentrancy": (["reentrancy-eth", "reentrancy-no-eth"],
                   ["reentrancy-benign", "reentrancy-events", "reentrancy-unlimited-gas"]),
    "unguarded-state-write": (["suicidal", "arbitrary-send-eth", "controlled-delegatecall",
                               "unprotected-upgrade", "tx-origin"], []),
    "unsafe-math": (["divide-before-multiply"], ["tautology"]),
}
RISK_OF = {d: (risk, strict) for risk, (s, l) in DETECTORS.items()
           for strict, group in ((True, s), (False, l)) for d in group}
ALL_DETECTORS = ",".join(RISK_OF)


def installed_versions() -> set[str]:
    out = subprocess.run(["solc-select", "versions"], capture_output=True, text=True).stdout
    return set(re.findall(r"\d+\.\d+\.\d+", out))


def solc_for(src: str, have: set[str], fallback: str) -> str | None:
    m = re.search(r"pragma solidity\s*([^;]+);", src)
    spec = m.group(1).strip() if m else fallback
    exact = re.fullmatch(r"=?(\d+\.\d+\.\d+)", spec)
    if exact:
        return exact.group(1) if exact.group(1) in have else None
    minor = re.search(r"(\d+\.\d+)\.", spec)
    candidates = sorted((v for v in have if minor and v.startswith(minor.group(1) + ".")),
                        key=lambda v: tuple(map(int, v.split("."))))
    return candidates[-1] if candidates else None


def run_slither(path: Path, version: str, remaps: list[str]) -> dict | None:
    cmd = ["slither", str(path), "--json", "-", "--detect", ALL_DETECTORS]
    if remaps:
        cmd += ["--solc-remaps", " ".join(remaps)]
    env = {**os.environ, "SOLC_VERSION": version}
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env, cwd=path.parent)
        data = json.loads(proc.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError):
        return None
    return data if data.get("success") else None


def findings(data: dict, name: str) -> tuple[set[Key], set[Key]]:
    strict, loose = set(), set()
    for r in data["results"].get("detectors", []):
        risk, is_strict = RISK_OF.get(r["check"], (None, False))
        if not risk:
            continue
        for e in r["elements"]:
            if e["type"] == "function" and Path(e["source_mapping"]["filename_relative"]).name == name:
                (strict if is_strict else loose).add((name, e["name"], risk))
    return strict, strict | loose


def row(risk, targets, strict, loose):
    t = {k for k in targets if risk is None or k[2] == risk}
    s = {k for k in strict if risk is None or k[2] == risk}
    l = {k for k in loose if risk is None or k[2] == risk}
    tps, tpl = len(t & s), len(t & l)
    label = "**all**" if risk is None else risk
    return (f"| {label} | {len(t)} | **{len(s)}** | {tps} | **{pct(tps, len(s))}** | **{pct(tps, len(t))}** "
            f"| {len(l)} | {tpl} | {pct(tpl, len(l))} | {pct(tpl, len(t))} |")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("corpus")
    ap.add_argument("--labels")
    ap.add_argument("--remap", nargs="*", default=[], help="solc remappings, e.g. forge-std/=lib/forge-std/src/")
    ap.add_argument("--fallback-pragma", default="^0.4.24")
    args = ap.parse_args(argv)

    corpus = load_corpus(args.corpus, args.labels)
    have = installed_versions()
    strict, loose = set(), set()
    not_analysed: list[tuple[str, str]] = []
    versions = defaultdict(int)
    for name, path in corpus.files:
        version = solc_for(path.read_text(errors="replace"), have, args.fallback_pragma)
        data = run_slither(path, version, args.remap) if version else None
        if data is None:
            not_analysed.append((name, version or "no installed compiler matches the pragma"))
            continue
        versions[version] += 1
        s, l = findings(data, name)
        strict |= s
        loose |= l

    targets = corpus.targets
    slither_version = subprocess.run(["slither", "--version"], capture_output=True, text=True).stdout.strip()
    print(f"# Baseline — Slither {slither_version} on {corpus.title}\n")
    print(f"Run {date.today().isoformat()} · corpus commit `{corpus.commit}` · {len(corpus.files)} files, "
          f"{len(corpus.files) - len(not_analysed)} compiled · {len(targets)} targets · "
          f"compilers: {', '.join(f'{v} ×{n}' for v, n in sorted(versions.items()))} · `python bench/slither.py <corpus>`\n")
    print("Same unit and same harsh rule as `bench/run.py`: a (file, function, risk); every finding that is not on a "
          "labelled function counts as false. A file Slither could not compile is a miss for every target in it.\n")
    print("| risk | targets | **strict found** | true | **precision** | **recall** | loose found | true | precision | recall |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    for r in RISKS:
        print(row(r, targets, strict, loose))
    print(row(None, targets, strict, loose))
    print("\nStrict: the detectors Slither rates High or Medium for the risk. Loose: strict plus its Low and "
          "Informational detectors, the analogue of counting any single lens.\n")

    print(f"## Files Slither could not analyse ({len(not_analysed)})\n")
    for name, why in not_analysed:
        print(f"- `{name}` — {why}")
    print("\n## Strict findings that are not on a labelled target\n")
    for name, fn, risk in sorted(strict - targets):
        print(f"- `{name}` `{fn}` {risk}")
    print("\n## Targets strict Slither missed\n")
    for name, fn, risk in sorted(targets - strict):
        print(f"- `{name}` `{fn}` {risk}" + ("  (seen by a loose detector)" if (name, fn, risk) in loose else ""))


if __name__ == "__main__":
    main()
