"""Phase 1 of the 10-05 sweep: run hunt-and-prove over the money-holding target list.

    python prove/sweep.py [--targets prove/sweep-targets.json] [--limit N] [--finder generic]
        [--samples N] [--max-proofs K] [--out prove/sweep-report.json] [--dry]

Reads the targets Phase 0 found and runs prove/hunt.py on each at the latest block, collecting the
split the whole tool is built to publish: proven / unproven / errored, with the model cost. `--dry`
checks the environment and prints the plan and the spend WITHOUT any model call, so the paid pass is a
decision and not a surprise. A real run needs ROBINHOOD_RPC_URL set, Foundry, and a `claude` login.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prove import harness, hunt  # noqa: E402


def preflight(chains: set[str]) -> list[str]:
    """Everything a real run needs; returns a list of problems (empty = ready)."""
    problems = []
    for c in chains:
        if not (c in harness.CHAIN_ENV and __import__("os").environ.get(harness.CHAIN_ENV[c])):
            problems.append(f"{harness.CHAIN_ENV.get(c, c + '?')} not set (needed for --block latest on {c})")
    if shutil.which("forge") is None:
        problems.append("forge (Foundry) not on PATH")
    if shutil.which("claude") is None:
        problems.append("`claude` not on PATH (the finder and prover call it)")
    return problems


def run_one(t: dict, finder: str, k: int, samples: int) -> dict:
    """Hunt+prove one target, turning any crash into an 'errored' row rather than aborting the sweep."""
    chain, address = t["chain"], t["address"]
    try:
        block = hunt.resolve_block(chain, "latest")
        rep = hunt.hunt(chain, address, block, finder, k, t.get("label") or t.get("address"), samples)
        state = "proven" if rep["proved"] else "unproven"
        return {"address": address, "chain": chain, "usd": t.get("usd"), "state": state,
                "proved": rep["proved"], "found": rep["candidates_found"],
                "cost_usd": round(rep["finder_cost_usd"] + rep["prove_cost_usd"], 2),
                "proof_lines": [r.get("proof_line", "") for r in rep["results"] if r["proven"]]}
    except Exception as e:  # network, fetch_source miss, forge failure: recorded, not fatal
        return {"address": address, "chain": chain, "usd": t.get("usd"), "state": "errored",
                "error": f"{type(e).__name__}: {str(e)[:160]}", "cost_usd": 0.0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--targets", default="prove/sweep-targets.json")
    ap.add_argument("--limit", type=int, default=0, help="only the top N targets (0 = all)")
    ap.add_argument("--finder", default="generic")
    ap.add_argument("--samples", type=int, default=5)
    ap.add_argument("--max-proofs", type=int, default=3, dest="k")
    ap.add_argument("--out", default="prove/sweep-report.json")
    ap.add_argument("--dry", action="store_true", help="check env + print the plan and spend, no model call")
    a = ap.parse_args()

    data = json.loads(Path(a.targets).read_text())
    targets = data.get("targets", [])
    if a.limit:
        targets = targets[: a.limit]
    chains = {t["chain"] for t in targets}

    problems = preflight(chains)
    if a.dry:
        print(f"targets: {len(targets)} money-holding (of {data.get('verified_total','?')} verified)")
        print(f"plan: finder {a.finder} x{a.samples}, prove top {a.k} each, chains {sorted(chains)}")
        print(f"spend: finder ~${0.20*a.samples:.2f}/target; proving is a full model run per candidate (variable)")
        print("environment: " + ("READY" if not problems else "NOT READY"))
        for p in problems:
            print(f"  - {p}")
        return 0
    if problems:
        print("cannot run: " + "; ".join(problems), file=sys.stderr)
        return 1
    if not targets:
        print("no targets in the list; run prove/sweep_targets.py first", file=sys.stderr)
        return 1

    rows, t0 = [], time.time()
    for i, t in enumerate(targets, 1):
        print(f"\n===== [{i}/{len(targets)}] {t['address']} (${t.get('usd','?')}) =====", flush=True)
        rows.append(run_one(t, a.finder, a.k, a.samples))

    tally = {s: sum(1 for r in rows if r["state"] == s) for s in ("proven", "unproven", "errored")}
    report = {"generated": harness.now(), "source": a.targets, "finder": a.finder,
              "samples": a.samples, "max_proofs": a.k, "targets_run": len(rows),
              "tally": tally, "total_cost_usd": round(sum(r["cost_usd"] for r in rows), 2),
              "wall_seconds": round(time.time() - t0), "results": rows}
    Path(a.out).write_text(json.dumps(report, indent=2) + "\n")
    md = ["# Robinhood Chain sweep", "",
          f"{tally['proven']} proven, {tally['unproven']} unproven, {tally['errored']} errored "
          f"across {len(rows)} money-holding contracts. Cost ${report['total_cost_usd']}.", "",
          "| contract | $ held | result | found | proof |", "|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| `{r['address']}` | {r.get('usd','?')} | {r['state']} | {r.get('found','-')} | "
                  f"{(r.get('proof_lines') or [r.get('error','')])[0][:60]} |")
    Path(a.out).with_suffix(".md").write_text("\n".join(md) + "\n")
    print(f"\n=== sweep: {tally} — ${report['total_cost_usd']} — {a.out} ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
