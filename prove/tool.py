"""Prove one exploit on ANY verified contract, not just a benchmark entry.

    python prove/tool.py prove <chain> <address> --block N --function <fn> \
        --attack "one sentence: what the exploit does" [--contract <name>] [--name <label>]
    python prove/tool.py check <run-dir>        # re-run a saved proof with the model gone

This is the benchmark's prove stage (prove/harness.py) pointed at a contract you choose. Give it a
chain, a verified address, the block the bug was live, and a one-line hypothesis; it fetches the
verified source (no API key, six chains), forks at that block, and has a model write a Foundry exploit
that must make the attacker's balance grow. The scaffold measures the profit, so a proof is measured,
not asserted, and the same guards apply: vm.store / vm.etch / vm.mockCall on the victim, or pranking a
non-attacker, fails the proof. `check` reproduces a saved proof with no model in the loop.

Needs Foundry and an archive RPC for the chain in its env var (ETHEREUM_RPC_URL, BASE_RPC_URL, ...).
Model calls go through `claude`; if an env API key overrides the login, run under `env -u ANTHROPIC_API_KEY`.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prove import harness                    # noqa: E402  reuse the engine, unchanged
from bench import stream                     # noqa: E402
from quorum.targets import fetch_source      # noqa: E402

RUNS = Path(os.environ.get("QUORUM_TOOL_DIR", Path.home() / ".quorum-tool"))


def build(chain: str, address: str, block: int, contract: str | None,
          function: str, attack: str, slug: str) -> Path:
    """Assemble a fork workspace: the fetched victim source and the one hypothesis, nothing else."""
    if chain not in harness.CHAIN_ENV:
        raise SystemExit(f"chain {chain!r}; one of {', '.join(sorted(harness.CHAIN_ENV))}")
    name, src = fetch_source(address, chain)
    ws = RUNS / slug
    if ws.exists():
        shutil.rmtree(ws)
    shutil.copytree(harness.SCAFFOLD, ws, symlinks=True)
    (ws / "target").mkdir()
    (ws / "target" / "victim.sol").write_text(src)
    (ws / "TASK.md").write_text(harness.TASK.format(
        chain=chain, block=block, address=address, contract=contract or name,
        function=function, attack=attack, rpc_env=harness.CHAIN_ENV[chain]))
    return ws


def prove(chain: str, address: str, block: int, contract: str | None,
          function: str, attack: str, name: str | None) -> dict:
    slug = stream.slug(name or f"{chain}-{address[:10]}")
    ws = build(chain, address, block, contract, function, attack, slug)
    print(f"workspace {ws}\nhypothesis: {(contract or address)}.{function} — {attack[:80]}")
    try:
        res = stream.claude((ws / "TASK.md").read_text(), ws, "Bash Read Write Edit Glob Grep",
                            timeout=int(os.environ.get("QUORUM_PROVE_TIMEOUT", "1800")))
        said, cost = str(res.get("result"))[:200], res.get("total_cost_usd", 0.0)
    except Exception as exc:                  # a model failure is not a proof; record it and move on
        said, cost = f"model error: {exc}", 0.0
    v = harness.verdict(ws, chain)
    record = {"chain": chain, "address": address, "block": block, "contract": contract or None,
              "function": function, "attack": attack, "proved_at": harness.now(),
              "cost_usd": round(cost, 2), "model_said": said, **v}
    (ws / "result.json").write_text(json.dumps(record, indent=1) + "\n")
    state = "PROVEN" if v["proven"] else "unproven" if v["proven"] is False else "unprovable"
    print(f"{state}: {v['reason']}  ${record['cost_usd']}\n{v.get('proof_line', '')}".rstrip())
    print(f"result: {ws / 'result.json'}" +
          (f"\nexploit: {ws / 'test' / 'Exploit.t.sol'}" if v["proven"] else ""))
    return record


def check(run_dir: str) -> dict:
    """Reproduce a saved proof from its workspace alone, the way a reader would."""
    ws = Path(run_dir)
    rec = json.loads((ws / "result.json").read_text()) if (ws / "result.json").exists() else {}
    chain = rec.get("chain")
    if not chain:
        raise SystemExit(f"no result.json with a chain in {ws}")
    v = harness.verdict(ws, chain)
    print(f"{ws.name}: {'reproduces' if v['proven'] else v['reason']}  {v.get('proof_line', '')}".rstrip())
    return v


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Prove one exploit on any verified contract by running it on a fork.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prove", help="fork at a block and prove a hypothesis on a contract you choose")
    p.add_argument("chain", choices=sorted(harness.CHAIN_ENV))
    p.add_argument("address")
    p.add_argument("--block", type=int, required=True, help="the block the bug was live at")
    p.add_argument("--function", required=True, help="the function the hypothesis targets")
    p.add_argument("--attack", required=True, help="one sentence: what the exploit does")
    p.add_argument("--contract", help="contract name (defaults to the verified name)")
    p.add_argument("--name", help="a label for the run folder")
    c = sub.add_parser("check", help="re-run a saved proof with no model, the way a reader would")
    c.add_argument("run_dir")
    a = ap.parse_args(argv)
    if a.cmd == "prove":
        prove(a.chain, a.address, a.block, a.contract, a.function, a.attack, a.name)
    else:
        check(a.run_dir)


if __name__ == "__main__":
    main()
