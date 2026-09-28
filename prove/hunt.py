"""Hunt then prove, in one shot: find candidate bugs in a verified contract and settle each by running it.

    python prove/hunt.py <chain> <address> [--block <n|latest>] [--finder generic|regex-v0|v4-1pass] [--max-proofs K]

A finder reads the verified source and proposes candidate bugs (a function and a one-line attack). The
top few candidates are then handed one at a time to the prove stage, which forks at the block and tries
to write an exploit that actually pays — the same engine and guards as prove/tool.py. The output is the
split the whole tool is built around: what pays (PROVEN), and what stays an unproven candidate.

Finders differ in cost and noise (measured on the blind benchmark, bench/STREAM.md): `generic` is one
prompt and the best value, `regex-v0` is the free ten-lens baseline, `v4-1pass` is Pashov's deep reader
— highest recall but it writes many items, so hunt dedupes by (contract, function) and proves only the
top --max-proofs of them. Proving is the expensive part: each candidate is a full model run on a fork.

Needs Foundry and an archive RPC for the chain in its env var; a generic/v4 finder also calls `claude`.
Run under `env -u ANTHROPIC_API_KEY` if an env key overrides your login.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prove import harness, tool                # noqa: E402
from bench import stream                       # noqa: E402
from quorum.targets import fetch_source        # noqa: E402

TIER_ORDER = {"finding": 0, "below-threshold": 1, "lead": 2}


def resolve_block(chain: str, block: str) -> int:
    """A concrete block to fork. 'latest' asks the chain's own RPC, so live hunting needs no lookup."""
    if block != "latest":
        return int(block)
    rpc = os.environ.get(harness.CHAIN_ENV[chain])
    if not rpc:
        raise SystemExit(f"--block latest needs {harness.CHAIN_ENV[chain]} set, or pass --block <n>")
    from web3 import Web3
    return Web3(Web3.HTTPProvider(rpc)).eth.block_number


def find(finder: str, src: str, slug: str) -> tuple[list[dict], float]:
    """Run one finder over the source in an isolated workspace; return its candidates and cost."""
    iso = tool.RUNS / slug
    if iso.exists():
        shutil.rmtree(iso)
    iso.mkdir(parents=True)
    (iso / "target.sol").write_text(src)
    run, _ = stream.CONTESTANTS[finder]
    return run(iso)


def rank(found: list[dict], k: int) -> list[dict]:
    """Dedupe by (contract, function) keeping the most confident, drop empties, findings before leads."""
    best: dict[tuple[str, str], dict] = {}
    for f in found:
        fn = (f.get("function") or "").strip()
        if not fn:
            continue
        key = (f.get("contract") or "", fn)
        if key not in best or f.get("confidence", 0) > best[key].get("confidence", 0):
            best[key] = f
    ranked = sorted(best.values(), key=lambda f: (TIER_ORDER.get(f.get("tier") or "", 3), -f.get("confidence", 0)))
    return ranked[:k]


def hunt(chain: str, address: str, block: int, finder: str, k: int, name: str | None) -> dict:
    if chain not in harness.CHAIN_ENV:
        raise SystemExit(f"chain {chain!r}; one of {', '.join(sorted(harness.CHAIN_ENV))}")
    label = stream.slug(name or f"{chain}-{address[:10]}")
    cname, src = fetch_source(address, chain)
    print(f"target: {cname} {address} on {chain} @ block {block}")
    found, fcost = find(finder, src, f"{label}-hunt")
    picks = rank(found, k)
    print(f"finder {finder}: {len(found)} candidate(s), proving top {len(picks)} (${fcost:.2f})")
    tried, proven = [], []
    for i, f in enumerate(picks):
        contract, fn, attack = f.get("contract") or cname, f["function"], f.get("text", "")
        print(f"\n[{i + 1}/{len(picks)}] prove {contract}.{fn} — {attack[:70]}")
        ws = tool.assemble(chain, address, block, contract, fn, attack,
                           f"{label}-{i}-{stream.slug(fn)}", cname, src)
        rec = tool.settle(ws, chain, address, block, contract, fn, attack)
        rec["confidence"], rec["workspace"] = f.get("confidence"), str(ws)
        tried.append(rec)
        state = "PROVEN" if rec["proven"] else "unproven" if rec["proven"] is False else "unprovable"
        print(f"    -> {state}: {rec['reason']}  {rec.get('proof_line', '')}".rstrip())
        if rec["proven"]:
            proven.append(rec)
    report = {"target": {"chain": chain, "address": address, "block": block, "name": cname},
              "finder": finder, "finder_cost_usd": round(fcost, 2), "candidates_found": len(found),
              "proved": len(proven), "prove_cost_usd": round(sum(r["cost_usd"] for r in tried), 2),
              "hunted_at": harness.now(), "results": tried}
    out = tool.RUNS / f"{label}-report.json"
    out.write_text(json.dumps(report, indent=1) + "\n")
    print(f"\n=== {cname}: {len(proven)} proven of {len(picks)} tried, {len(found)} found. report: {out} ===")
    for r in proven:
        print(f"  PROVEN {r['contract'] or cname}.{r['function']}  {r.get('proof_line', '')}")
    return report


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Hunt candidate bugs in a verified contract and prove each on a fork.")
    ap.add_argument("chain", choices=sorted(harness.CHAIN_ENV))
    ap.add_argument("address")
    ap.add_argument("--block", default="latest", help="block to fork; 'latest' asks the RPC (default)")
    ap.add_argument("--finder", default="generic", choices=sorted(stream.CONTESTANTS),
                    help="who proposes candidates (default generic: the best value on the benchmark)")
    ap.add_argument("--max-proofs", type=int, default=3, dest="k", help="how many top candidates to prove")
    ap.add_argument("--name", help="a label for the run folder")
    a = ap.parse_args(argv)
    hunt(a.chain, a.address, resolve_block(a.chain, a.block), a.finder, a.k, a.name)


if __name__ == "__main__":
    main()
