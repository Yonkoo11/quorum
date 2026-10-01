"""The prove stage: a hypothesis becomes a finding only when its exploit runs on a fork and pays.

    python prove/harness.py prove <entry_id> [--contestant v4-1pass] [--item N]
    python prove/harness.py check <entry_id>          # re-run the saved PoC, independent of the model

A hunter (v4, the generic pass, a person) says a function is exploitable. That is a hypothesis. This
stage hands a model a Foundry workspace forked at the block the bug was live, the victim's address,
and the one hypothesis, and asks it to write an exploit that makes the attacker's balance grow. The
scaffold measures that growth itself (`prove/scaffold/src/ForkPoCBase.sol`), so the proof is the
measured profit, not anything the exploit asserts.

Two things a "proof" must not be, both checked here and not by the model:
  - faked state: `vm.store`, `vm.etch`, `vm.mockCall` on the victim rewrite the chain the fork gave
    us. The written exploit is scanned for them and a hit fails the proof.
  - a lucky reader: `check` re-runs the saved PoC in a clean workspace with the model gone, so a
    published proof is one anyone can reproduce with only Foundry and an archive endpoint.

Model calls go through `claude` with web tools off. If an env API key overrides the login, run under
`env -u ANTHROPIC_API_KEY`. Endpoints come from <CHAIN>_RPC_URL in the environment; a chain with no
archive endpoint set is reported as unprovable rather than failed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from bench import stream  # noqa: E402

HERE = Path(__file__).parent
SCAFFOLD = HERE / "scaffold"
PROOFS = HERE / "proofs"
WORK = Path.home() / ".quorum-stream" / "prove"
FORK_BLOCK = HERE / "fork-blocks.json"     # entry id -> {chain, block}, read from the proof of concept
CHAIN_ENV = {"ethereum": "ETHEREUM_RPC_URL", "base": "BASE_RPC_URL", "bsc": "BSC_RPC_URL",
             "polygon": "POLYGON_RPC_URL", "arbitrum": "ARBITRUM_RPC_URL", "optimism": "OPTIMISM_RPC_URL",
             "robinhood": "ROBINHOOD_RPC_URL"}
# Cheatcodes that rewrite the fork's state. A hit in the exploit fails the proof: a drain must move
# funds the fork already holds, not ones the exploit invented.
FORBIDDEN = re.compile(r"vm\.(store|etch|mockCall|mockCallRevert)\b")
# deal()/vm.deal mint a balance from nothing; hoax()/startHoax() mint ETH and prank in one call. The
# scaffold already funds the attacker's gas (in forkAt, before the snapshot) and working capital must
# come from a real on-chain flash-loan pool, so any of these in the exploit would fabricate the very
# balance this stage measures. Rejected.
MINTS_BALANCE = re.compile(r"\b(?:vm\.)?deal\s*\(|\b(?:start)?[Hh]oax\s*\(")
# The exploit must run as the unprivileged attacker. Impersonating anyone else (the owner, a keeper)
# and then routing funds to `attacker` would be a false proof, so only `attacker` may be pranked. This
# also catches changePrank; hoax/startHoax (which prank too) are rejected as balance mints above.
PRANK = re.compile(r"(?:vm\.(?:start)?[Pp]rank|changePrank)\s*\(\s*([^,)]+)")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fork_of(entry_id: str) -> dict | None:
    """Where and when to fork. Stream hacks carry chain/block/proxy from intake; the dev set, labelled
    before intake existed, is pinned in fork-blocks.json. The ledger wins when it has the fields."""
    entry = next((e for e in stream.load()["entries"] if e["id"] == entry_id), None)
    if entry and entry.get("chain") in CHAIN_ENV and entry.get("block"):
        return {"chain": entry["chain"], "block": entry["block"],
                "address": entry.get("proxy") or entry.get("address")}
    return json.loads(FORK_BLOCK.read_text()).get(entry_id) if FORK_BLOCK.exists() else None


def hypothesis(entry: dict, contestant: str, item: int | None) -> dict:
    pred = json.loads((stream.PREDICTIONS / contestant / f"{stream.slug(entry['id'])}.json").read_text())
    findings = pred["findings"]
    if item is not None:
        return findings[item]
    label = entry["label"]                      # dev set only: aim at the labelled entry point
    fn = label["entry_points"][0].split(".")[-1]
    return next((f for f in findings if f["function"] == fn), findings[0])


def workspace(entry: dict, fork: dict, hyp: dict) -> Path:
    ws = WORK / stream.slug(entry["id"])
    if ws.exists():
        shutil.rmtree(ws)
    shutil.copytree(SCAFFOLD, ws, symlinks=True)
    (ws / "target").mkdir()
    src = Path.home() / ".quorum-stream" / "work" / "src" / f"{stream.slug(entry['id'])}.sol"
    if not src.exists():                        # dev set lives under the bench work dir
        src = Path(os.environ.get("QUORUM_DEV_SRC", "")) / f"{stream.slug(entry['id'])}.sol"
    shutil.copy(src, ws / "target" / "victim.sol")
    # The ledger address is the implementation (where the source is); the exploit must hit the proxy
    # the users actually funded (where the state is). fork["address"] carries the proxy when they differ.
    (ws / "TASK.md").write_text(TASK.format(
        chain=fork["chain"], block=fork["block"], address=fork.get("address") or entry.get("address", "see victim.sol"),
        contract=hyp.get("contract") or entry["name"], function=hyp["function"], attack=hyp["text"],
        rpc_env=CHAIN_ENV[fork["chain"]]))
    return ws


TASK = """# Prove one exploit on a fork

The file `target/victim.sol` is the deployed source of `{contract}` at `{address}` on {chain}.
A hypothesis says this is exploitable:

> **{contract}.{function}** — {attack}

Write `test/Exploit.t.sol`: a Foundry test that inherits `ForkPoCBase` (in `src/`), forks with
`forkAt("{chain}", {block})` in `setUp`, and proves the exploit by calling `proveEthProfit(this.attack)`
or `proveTokenProfit(<token>, this.attack)`, where `attack()` is an `external` function you write that
performs the exploit as `attacker`. The scaffold measures the attacker's profit and prints `[PROOF]`
only if it grew, so you do not assert profit yourself.

Finding the victim (do this before deciding it is unprovable):
- The money may not sit in `{contract}` itself. If `{contract}` custodies nothing, the drain lands on a
  THIRD PARTY that trusts it — a Safe that enabled it as a module, a vault or solver that granted it a
  token allowance, a user with an open request, a pool it prices from. On the fork that victim exists
  with its real balances and approvals; your job includes finding it and targeting it.
- The fork has the whole chain at that block, so discover the victim on-chain. `cast` is available and
  the RPC is in the env var `{rpc_env}`. Useful moves: `cast logs` for the contract's own events
  (who registered, deposited, approved, opened a request), `cast call` to read allowances/balances,
  `cast storage` to read a slot you can justify. You may also scan events inside the test with `vm`.
- Once you have a concrete victim address with real state, target it. Draining a real victim's real
  funds to `attacker` is a valid proof; inventing the victim's state is not.

Rules:
- The attack must run as `attacker`, an unprivileged address. Do not `vm.prank` the owner or any role.
- The scaffold already funds the attacker's gas. Get any working capital from a real on-chain
  flash-loan pool. Do NOT use `deal` or `vm.deal` to hand the attacker a balance, and do NOT use
  `vm.store`, `vm.etch` or `vm.mockCall` — each fabricates the balance or state this stage measures
  and fails the proof.
- Run it yourself: `forge test --match-path test/Exploit.t.sol -vv`. Iterate until it passes with a
  `[PROOF]` line. If after honest effort — including looking for a real victim on-chain — the exploit
  does not pay (the hypothesis is wrong, or the state genuinely is not on this fork), write
  `test/Exploit.t.sol` with a top comment `// UNPROVEN: <reason>` and stop. Do not fake a pass.
Report in your final message: PROVEN or UNPROVEN, and one sentence why."""


def run_forge(ws: Path, chain: str) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    rpc = os.environ.get(CHAIN_ENV[chain], "")
    env[CHAIN_ENV[chain]] = rpc
    return subprocess.run(["forge", "test", "--match-path", "test/Exploit.t.sol", "-vv"],
                          cwd=ws, capture_output=True, text=True, env=env, timeout=1200)


def verdict(ws: Path, chain: str) -> dict:
    """Re-run the saved exploit with no model in the loop, and judge it by the scaffold's own output."""
    exploit = ws / "test" / "Exploit.t.sol"
    if not exploit.exists():
        return {"proven": False, "reason": "no Exploit.t.sol written"}
    body = exploit.read_text()
    if body.lstrip().startswith("// UNPROVEN") or "UNPROVEN:" in body.split("\n")[0:1]:
        return {"proven": False, "reason": "hunter marked it unproven", "unproven_note": body.splitlines()[0]}
    forbidden = FORBIDDEN.findall(body)
    if forbidden:
        return {"proven": False, "reason": f"fabricates state: vm.{forbidden[0]} on the fork"}
    if MINTS_BALANCE.search(body):
        return {"proven": False, "reason": "mints a balance with deal(): profit must come from the fork, not a cheat"}
    impostor = next((who.strip() for who in PRANK.findall(body) if who.strip() != "attacker"), None)
    if impostor:
        return {"proven": False, "reason": f"impersonates a non-attacker address: prank({impostor})"}
    if not os.environ.get(CHAIN_ENV[chain]):
        return {"proven": None, "reason": f"no archive endpoint: set {CHAIN_ENV[chain]}"}
    out = run_forge(ws, chain)
    log = out.stdout + out.stderr
    passed = "[PROOF] attacker gained" in log and re.search(r"Suite result: ok", log) is not None
    return {"proven": bool(passed), "reason": "measured profit" if passed else "no [PROOF] in a passing run",
            "proof_line": next((l.strip() for l in log.splitlines() if "[PROOF]" in l), ""),
            "forge_tail": "\n".join(log.splitlines()[-12:])}


def prove(entry_id: str, contestant: str, item: int | None) -> None:
    entry = next(e for e in stream.load()["entries"] if e["id"] == entry_id)
    fork = fork_of(entry_id)
    if not fork:
        print(f"no fork block recorded for {entry_id}")
        return
    hyp = hypothesis(entry, contestant, item)
    ws = workspace(entry, fork, hyp)
    print(f"workspace {ws}\nhypothesis: {hyp.get('contract')}.{hyp['function']} — {hyp['text'][:80]}")
    tools = "Bash Read Write Edit Glob Grep"
    try:
        res = stream.claude((ws / "TASK.md").read_text(), ws, tools,
                            timeout=int(os.environ.get("QUORUM_PROVE_TIMEOUT", "1800")))
        said = str(res.get("result"))[:200]
        cost = res.get("total_cost_usd", 0.0)
    except Exception as exc:
        said, cost = f"model error: {exc}", 0.0
    v = verdict(ws, fork["chain"])
    record = {"entry": entry_id, "contestant": contestant, "item": item, "hypothesis": hyp,
              "chain": fork["chain"], "block": fork["block"], "proved_at": now(),
              "cost_usd": round(cost, 2), "model_said": said, **v}
    PROOFS.mkdir(parents=True, exist_ok=True)
    (PROOFS / f"{stream.slug(entry_id)}.json").write_text(json.dumps(record, indent=1) + "\n")
    if v["proven"]:
        shutil.copy(ws / "test" / "Exploit.t.sol", PROOFS / f"{stream.slug(entry_id)}.t.sol")
    print(f"{'PROVEN' if v['proven'] else 'unproven' if v['proven'] is False else 'unprovable'}: "
          f"{v['reason']}  ${record['cost_usd']}\n{v.get('proof_line','')}")


def check(entry_id: str) -> None:
    """Reproduce a saved proof from its .t.sol alone, the way a reader would."""
    entry = next(e for e in stream.load()["entries"] if e["id"] == entry_id)
    fork = fork_of(entry_id)
    saved = PROOFS / f"{stream.slug(entry_id)}.t.sol"
    if not saved.exists() or not fork:
        print(f"no saved proof or fork block for {entry_id}")
        return
    ws = workspace(entry, fork, {"function": "?", "text": "re-check", "contract": entry["name"]})
    shutil.copy(saved, ws / "test" / "Exploit.t.sol")
    v = verdict(ws, fork["chain"])
    print(f"{entry_id}: {'reproduces' if v['proven'] else v['reason']}  {v.get('proof_line','')}")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Prove a hypothesis by running its exploit on a fork.")
    ap.add_argument("command", choices=["prove", "check"])
    ap.add_argument("entry_id")
    ap.add_argument("--contestant", default="v4-1pass")
    ap.add_argument("--item", type=int, default=None)
    a = ap.parse_args(argv)
    if a.command == "prove":
        prove(a.entry_id, a.contestant, a.item)
    else:
        check(a.entry_id)


if __name__ == "__main__":
    main()
