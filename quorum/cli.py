"""Quorum command line.

    quorum fetch 0x...          pull a verified Base contract into targets/
    quorum run                  run the swarm over targets/
    quorum run --no-memory      the deletion test: same swarm, memory removed
    quorum recall               what the swarm knows before it reads any code
    quorum retire <key>         a human overrules a finding, permanently
    quorum attest               burn the fee, publish confirmed findings to Robinhood Chain
    quorum verify <tx>          check a claim, its evidence in memory, and its fee burn
    quorum reveal <key>         disclose the pattern behind a paid claim
    quorum import <tx>          learn a revealed pattern, only if its claim fee was burned
    quorum status               memory tier report
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone

from .memory import DEFAULT_DB, QUORUM_THRESHOLD, NoMemory, SwarmMemory
from .swarm import run_swarm
from .targets import load_targets, save

DIM, BOLD, GREEN, YELLOW, RED, RESET = "\033[2m", "\033[1m", "\033[32m", "\033[33m", "\033[31m", "\033[0m"


def _memory(args) -> SwarmMemory:
    return NoMemory() if args.no_memory else SwarmMemory(args.db)


def cmd_fetch(args) -> int:
    for address in args.addresses:
        path = save(address)
        print(f"{GREEN}saved{RESET} {path.name}  ({path.stat().st_size} bytes)  {DIM}{address}{RESET}")
    return 0


def cmd_run(args) -> int:
    memory = _memory(args)
    as_json = getattr(args, "json", False)
    targets = load_targets(args.targets)
    if not targets:
        print(f"{RED}no targets{RESET}. Run: quorum fetch 0x<address>")
        return 1

    if not as_json:
        banner = "MEMORY ON" if memory.enabled else "MEMORY REMOVED (ablation)"
        colour = GREEN if memory.enabled else RED
        print(f"\n{BOLD}quorum{RESET} {colour}[{banner}]{RESET}  quorum threshold: {args.threshold}")

    if memory.enabled and not as_json:
        patterns = memory.confirmed_patterns()
        print(f"{DIM}recalled before reading any code: {len(patterns)} confirmed pattern(s){RESET}")

    report = run_swarm(memory, targets, threshold=args.threshold, fresh_claims=args.reclaim,
                       agent_id=getattr(args, "agent_id", None))

    if as_json:
        print(json.dumps({"agent": getattr(args, "agent_id", None), "scanned": report.scanned,
                          "skipped": report.duplicate_work, "confirmed": len(report.promoted),
                          "recalled": len(report.recalled), "candidates": len(report.candidates)}))
        return 0

    for f in report.recalled:
        print(f"  {GREEN}RECALLED{RESET}  {f['contract']}:{f['function']} {DIM}{f['risk']}{RESET}"
              f"  first confirmed on {f.get('first_confirmed_on')}  {DIM}(1 sighting was enough){RESET}")
    for f in report.promoted:
        print(f"  {GREEN}QUORUM{RESET}    {f['contract']}:{f['function']} {DIM}{f['risk']}{RESET}"
              f"  corroborated by {', '.join(f['seen_by'])}")
    for f in report.candidates:
        print(f"  {YELLOW}candidate{RESET} {f['contract']}:{f['function']} {DIM}{f['risk']}"
              f"  only {', '.join(f['seen_by'])} — held back{RESET}")
    for f in report.suppressed:
        print(f"  {DIM}suppressed {f['contract']}:{f['function']} {f['risk']} — retired earlier: {f['reason']}{RESET}")

    print(f"\n{report.summary()}")
    if not memory.enabled:
        print(f"{RED}nothing was confirmed, recalled or suppressed: without memory the swarm "
              f"cannot corroborate, recognise or forget.{RESET}")
    return 0


def cmd_swarm(args) -> int:
    """Run N agent processes against one memory. They coordinate only by claiming."""
    SwarmMemory(args.db)  # create the database before the workers race for it
    print(f"\n{BOLD}{args.workers} agent processes, one memory, no message bus{RESET}")

    started = time.time()
    procs = [
        subprocess.Popen(
            [sys.executable, "-m", "quorum.cli", "--db", args.db, "run", "--json",
             "--agent-id", f"agent-{i + 1}"] + (["--reclaim"] if args.reclaim and i == 0 else []),
            stdout=subprocess.PIPE, text=True,
        )
        for i in range(args.workers)
    ]
    rows = []
    for proc in procs:
        out, _ = proc.communicate()
        for line in out.strip().splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    total_scanned = sum(r["scanned"] for r in rows)
    total_skipped = sum(r["skipped"] for r in rows)
    total_recalled = sum(r["recalled"] for r in rows)
    total_confirmed = sum(r["confirmed"] for r in rows)
    for r in sorted(rows, key=lambda x: x["agent"] or ""):
        print(f"  {r['agent']:9} scanned {r['scanned']:3}  stood down on {r['skipped']:3} "
              f"units a peer had already claimed")
    print(f"\n  {BOLD}{total_scanned} units scanned in total, {total_skipped} skipped, "
          f"in {time.time() - started:.1f}s{RESET}")
    if total_recalled or total_confirmed:
        print(f"  {GREEN}{total_confirmed} confirmed by quorum, {total_recalled} recognised "
              f"from an earlier session{RESET}")
    print(f"  {DIM}no agent sent a message to any other agent. The HOT tier decided "
          f"who did what.{RESET}")
    return 0


def cmd_recall(args) -> int:
    memory = SwarmMemory(args.db)
    if args.since:
        fresh = memory.learned_since(args.since)
        print(f"\n{BOLD}learned since {args.since}{RESET}")
        for p in fresh:
            print(f"  {p['risk']:22} {p['signature']}  {DIM}confirmed {p.get('confirmed_at')}{RESET}")
        if not fresh:
            print(f"  {DIM}nothing new{RESET}")
        print(f"\n{BOLD}journal entries in that window{RESET}")
        for e in memory.events(limit=20, since=args.since):
            print(f"  {DIM}{e.get('ts','')}  {str(e.get('acted'))[:80]}{RESET}")
        return 0
    patterns = memory.confirmed_patterns()
    print(f"\n{BOLD}what the swarm knows{RESET}  {DIM}{args.db}{RESET}")
    print(f"\n{BOLD}confirmed patterns (REFERENCE tier){RESET}")
    for p in patterns:
        print(f"  {p['risk']:22} {DIM}{p['signature']}{RESET}")
        print(f"    first confirmed on {BOLD}{p.get('first_confirmed_on')}{RESET}"
              f" by {', '.join(p.get('confirmed_by', []))}")
        again = p.get("recognised_on") or []
        if again:
            print(f"    {GREEN}recognised since on{RESET} {', '.join(again)}"
                  f"  {DIM}(1 sighting each, no quorum needed){RESET}")
    if not patterns:
        print(f"  {DIM}none yet{RESET}")

    print(f"\n{BOLD}findings (WARM tier){RESET}")
    for f in memory.findings():
        mark = f"{GREEN}confirmed{RESET}" if f.get("status") == "confirmed" else f"{YELLOW}candidate{RESET}"
        tx = f.get("attested_tx")
        print(f"  {mark}  {f['key']}  seen by {', '.join(f.get('seen_by', []))}"
              + (f"  {DIM}claim:{tx[:14]}...{RESET}" if tx else ""))

    print(f"\n{BOLD}recent journal (COLD tier){RESET}")
    for e in memory.events(limit=6):
        print(f"  {DIM}{e.get('ts','')}  {str(e.get('acted'))[:88]}{RESET}")
    return 0


def cmd_retire(args) -> int:
    memory = SwarmMemory(args.db)
    if memory.retire(args.key, args.reason):
        print(f"{GREEN}retired{RESET} {args.key} — no later session will report this shape again")
        return 0
    print(f"{RED}no such finding{RESET}: {args.key}")
    return 1


def cmd_attest(args) -> int:
    from . import chain

    memory = SwarmMemory(args.db)
    confirmed = memory.findings(status="confirmed")
    pending = [f for f in confirmed if not f.get("attested_tx")]
    if not confirmed:
        print("nothing to attest: the swarm has not confirmed anything yet")
        return 0
    if not pending:
        print(f"nothing to attest: all {len(confirmed)} confirmed finding(s) already have an on-chain claim")
        return 0

    fee = chain.CLAIM_FEE // 10**chain.TOKEN_DECIMALS
    held = chain.token_balance() / 10**chain.TOKEN_DECIMALS
    print(f"signer {chain.address()}  {chain.balance_wei()/1e18:.6f} ETH on {chain.chain_name()}  {held:,.0f} QUORUM on Robinhood Chain")
    print(f"each claim burns {fee:,} QUORUM before it is written. Scanning is free; publishing is not.")
    for f in pending[: args.limit]:
        earlier_burn = f.get("fee_burn_tx")  # a fee already paid by an attempt whose claim never landed

        def record(burn, f=f):
            """Save the burn the moment it is final, so a failed claim cannot lose it."""
            memory.client.set_entity("finding", f["key"], {**f, "fee_burn_tx": burn["tx"]})
            memory.log(evaluated={"key": f["key"]}, acted={"burned": burn["tx"]}, forward={"fee": fee})

        try:
            result = chain.attest(f, dry_run=args.dry_run, burn_tx=earlier_burn, on_burn=record)
        except RuntimeError as exc:
            print(f"  {RED}not published{RESET} {f['key']}: {exc}")
            saved = (memory.get_finding(f["key"]) or {}).get("fee_burn_tx")
            if saved:
                print(f"  {YELLOW}the fee burn is saved{RESET} ({saved[:14]}...). Run attest again and it is reused, not burned twice.")
            return 1
        if args.dry_run:
            cost = f"would reuse burn {earlier_burn[:14]}..." if earlier_burn else f"would burn {fee:,} QUORUM"
            print(f"  {YELLOW}dry run{RESET} {f['key']}  digest {result['digest'][:18]}...  {cost}")
            continue
        burn = result["burn"]
        memory.client.set_entity("finding", f["key"], {**f, "attested_tx": result["tx"], "fee_burn_tx": burn["tx"]})
        memory.log(evaluated={"key": f["key"]}, acted={"attested": result["tx"], "burned": burn["tx"]},
                   forward={"block": result["block"], "fee": fee})
        label = "reusing the fee burned earlier" if burn.get("reused") else f"burned {fee:,} QUORUM"
        print(f"  {GREEN}{label}{RESET}\n    {burn['url']}")
        print(f"  {GREEN}claimed on {chain.chain_name()}{RESET} {f['key']}\n    {result['url']}")
    return 0


def cmd_verify(args) -> int:
    """Re-derive a published claim from memory and check it against the chain.

    This is the join between the two halves of the product: the claim on chain is
    only meaningful if the evidence behind it is still in memory and still hashes
    to the same digest. The claim is looked up on Robinhood Chain first, then on
    Base, where the first claim was written.
    """
    from . import chain

    memory = SwarmMemory(args.db)
    claim = chain.read_claim(args.tx)
    stamp = datetime.fromtimestamp(claim["timestamp"], tz=timezone.utc).isoformat(timespec="seconds")

    print(f"\n{BOLD}claim on {claim['chain']}{RESET}  block {claim['block']}  {stamp}")
    print(f"  published by {claim['from']}")
    print(f"  digest       {claim['digest']}")

    if claim.get("burn_tx"):
        burn = chain.read_burn(claim["burn_tx"])
        amount = burn["amount"] / 10**chain.TOKEN_DECIMALS
        same_signer = burn["from"].lower() == claim["from"].lower()
        if burn["valid"] and same_signer:
            print(f"  {GREEN}fee burned{RESET}   {amount:,.0f} QUORUM on Robinhood Chain, block {burn['block']}, by the same signer")
        else:
            print(f"  {RED}fee check failed{RESET}  burn tx is not a valid {burn['required'] // 10**chain.TOKEN_DECIMALS:,} QUORUM burn by the claim's signer")
            return 1
    else:
        print(f"  {DIM}v1 claim: published before the fee existed, no burn to check{RESET}")

    for finding in memory.findings():
        if chain.claim_digest(finding).hex().lstrip("0x") == claim["digest"].lstrip("0x"):
            print(f"\n  {GREEN}the evidence for this claim is still in memory{RESET}")
            print(f"    {finding['key']}")
            print(f"    corroborated by {', '.join(finding.get('seen_by', []))}"
                  f"  {DIM}({finding.get('confirmed_via', 'quorum')}){RESET}")
            print(f"    evidence: {DIM}{finding.get('evidence','')[:78]}{RESET}")
            print(f"\n  {GREEN}digest recomputed from memory matches the chain{RESET}")
            return 0

    print(f"\n  {RED}no finding in this memory reproduces that digest{RESET}")
    return 1


def cmd_reveal(args) -> int:
    """Disclose the pattern behind a paid claim so other swarms can import it."""
    from . import chain

    memory = SwarmMemory(args.db)
    f = memory.get_finding(args.key)
    if not f or not f.get("attested_tx"):
        print(f"{RED}no claimed finding{RESET} {args.key}: attest it first")
        return 1
    result = chain.reveal({**f, "key": args.key})
    memory.client.set_entity("finding", args.key, {**f, "revealed_tx": result["tx"]})
    memory.log(evaluated={"key": args.key}, acted={"revealed": result["tx"]}, forward={"claim_tx": f["attested_tx"]})
    print(f"  {GREEN}revealed on {chain.chain_name()}{RESET} {args.key}\n    {result['url']}")
    return 0


def cmd_import(args) -> int:
    """Learn a pattern from someone else's reveal. Only paid, matching claims are learned."""
    from . import chain

    r = chain.read_reveal(args.tx)
    fields = r["fields"]
    print(f"\n{BOLD}reveal{RESET} {fields['risk']}  {fields['signature']}  by {r['revealed_by']}")
    required = (r["burn"] or {}).get("required", chain.CLAIM_FEE) // 10**chain.TOKEN_DECIMALS
    checks = [("digest matches the claim", r["digest_matches"]), ("revealed by the claim's signer", r["same_signer"]),
              (f"claim fee of {required:,} QUORUM burned", r["fee_paid"])]
    for label, ok in checks:
        print(f"  {GREEN if ok else RED}{'ok ' if ok else 'no '}{RESET} {label}")
    if not all(ok for _, ok in checks):
        print(f"\n  {RED}not imported{RESET}: a pattern nobody paid to publish is not evidence")
        return 1
    memory = SwarmMemory(args.db)
    if memory.import_pattern(fields, r["claim_tx"], r["claim"]["burn_tx"]):
        print(f"\n  {GREEN}imported into REFERENCE{RESET}: the swarm will recognise this idiom on sight")
    else:
        print(f"\n  {DIM}already known{RESET}")
    return 0


def cmd_status(args) -> int:
    memory = SwarmMemory(args.db)
    for k, v in memory.status().items():
        print(f"  {k:12} {v}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="quorum", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=DEFAULT_DB, help="Sibyl Memory database path")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("fetch", help="download verified Base contract source")
    p.add_argument("addresses", nargs="+")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("run", help="run the swarm")
    p.add_argument("--no-memory", action="store_true", help="deletion test: run with memory removed")
    p.add_argument("--reclaim", action="store_true", help="release work claims before running")
    p.add_argument("--threshold", type=int, default=QUORUM_THRESHOLD)
    p.add_argument("--targets", nargs="*")
    p.add_argument("--json", action="store_true", help="machine-readable summary")
    p.add_argument("--agent-id", dest="agent_id", help="identity this agent claims work under")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("swarm", help="run N agent processes against one memory")
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--reclaim", action="store_true", help="release work claims before running")
    p.set_defaults(func=cmd_swarm, no_memory=False)

    p = sub.add_parser("recall", help="show what memory holds")
    p.add_argument("--since", help="ISO timestamp: only what the swarm learned after this point")
    p.set_defaults(func=cmd_recall, no_memory=False)

    p = sub.add_parser("retire", help="permanently retire a finding")
    p.add_argument("key")
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_retire, no_memory=False)

    p = sub.add_parser("attest", help="publish confirmed findings to Robinhood Chain")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=3)
    p.set_defaults(func=cmd_attest, no_memory=False)

    p = sub.add_parser("verify", help="check a published claim against memory")
    p.add_argument("tx")
    p.set_defaults(func=cmd_verify, no_memory=False)

    p = sub.add_parser("reveal", help="disclose the pattern behind a paid claim")
    p.add_argument("key", help="finding key, e.g. VulnerableVault.sol:withdraw:reentrancy")
    p.set_defaults(func=cmd_reveal, no_memory=False)

    p = sub.add_parser("import", help="learn a revealed pattern whose claim fee was burned")
    p.add_argument("tx", help="reveal transaction hash")
    p.set_defaults(func=cmd_import, no_memory=False)

    p = sub.add_parser("status", help="memory tier report")
    p.set_defaults(func=cmd_status, no_memory=False)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
