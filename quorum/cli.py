"""Quorum command line.

    quorum fetch 0x...          pull a verified Base contract into targets/
    quorum run                  run the swarm over targets/
    quorum run --no-memory      the deletion test: same swarm, memory removed
    quorum recall               what the swarm knows before it reads any code
    quorum retire <key>         a human overrules a finding, permanently
    quorum attest               publish confirmed findings to Base
    quorum status               memory tier report
"""

from __future__ import annotations

import argparse
import sys

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
    targets = load_targets(args.targets)
    if not targets:
        print(f"{RED}no targets{RESET}. Run: quorum fetch 0x<address>")
        return 1

    banner = "MEMORY ON" if memory.enabled else "MEMORY REMOVED (ablation)"
    colour = GREEN if memory.enabled else RED
    print(f"\n{BOLD}quorum{RESET} {colour}[{banner}]{RESET}  quorum threshold: {args.threshold}")

    if memory.enabled:
        patterns = memory.confirmed_patterns()
        print(f"{DIM}recalled before reading any code: {len(patterns)} confirmed pattern(s){RESET}")

    report = run_swarm(memory, targets, threshold=args.threshold, fresh_claims=args.reclaim)

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


def cmd_recall(args) -> int:
    memory = SwarmMemory(args.db)
    patterns = memory.confirmed_patterns()
    print(f"\n{BOLD}what the swarm knows{RESET}  {DIM}{args.db}{RESET}")
    print(f"\n{BOLD}confirmed patterns (REFERENCE tier){RESET}")
    for p in patterns:
        print(f"  {p['signature']}  {p['risk']:22} first confirmed on {p.get('first_confirmed_on')}"
              f"  by {', '.join(p.get('confirmed_by', []))}")
    if not patterns:
        print(f"  {DIM}none yet{RESET}")

    print(f"\n{BOLD}findings (WARM tier){RESET}")
    for f in memory.findings():
        mark = f"{GREEN}confirmed{RESET}" if f.get("status") == "confirmed" else f"{YELLOW}candidate{RESET}"
        tx = f.get("attested_tx")
        print(f"  {mark}  {f['key']}  seen by {', '.join(f.get('seen_by', []))}"
              + (f"  {DIM}base:{tx[:14]}...{RESET}" if tx else ""))

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

    print(f"signer {chain.address()}  balance {chain.balance_wei()/1e18:.6f} ETH")
    for f in pending[: args.limit]:
        result = chain.attest(f, dry_run=args.dry_run)
        if args.dry_run:
            print(f"  {YELLOW}dry run{RESET} {f['key']}  digest {result['digest'][:18]}...")
            continue
        memory.client.set_entity("finding", f["key"], {**f, "attested_tx": result["tx"]})
        memory.log(evaluated={"key": f["key"]}, acted={"attested": result["tx"]}, forward={"block": result["block"]})
        print(f"  {GREEN}claimed on Base{RESET} {f['key']}\n    {result['url']}")
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
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("recall", help="show what memory holds")
    p.set_defaults(func=cmd_recall, no_memory=False)

    p = sub.add_parser("retire", help="permanently retire a finding")
    p.add_argument("key")
    p.add_argument("--reason", required=True)
    p.set_defaults(func=cmd_retire, no_memory=False)

    p = sub.add_parser("attest", help="publish confirmed findings to Base")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int, default=3)
    p.set_defaults(func=cmd_attest, no_memory=False)

    p = sub.add_parser("status", help="memory tier report")
    p.set_defaults(func=cmd_status, no_memory=False)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
