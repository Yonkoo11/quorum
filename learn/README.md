# Learn: real hacks, proven

Two kinds of thing live here, under one rule.

**Proven-hack cards** explain one real 2026 hack in plain English, each backed by an exploit that
**runs**: a Foundry test in [`../prove/proofs/`](../prove/proofs) that forks the chain at the block the
bug was live and drains the contract for real. The number in the card is the number that test prints.
We do not describe an attack we cannot reproduce.

**Defensive-habit guides** cover the operational ways people lose funds — approvals, phishing, blind
signing — that are not bugs in anyone's code and that our scanner does not catch. We say so plainly on
each one, tie it to a real documented risk, and end in an action you can take.

That is the whole rule of this section, and it is the same rule the rest of Quorum lives under:

> **We show, we do not assert. If we can't prove it on a fork, it isn't here.**

Most "scam awareness" content is generic and unfalsifiable. These cards are the opposite: pick any
one, run the test yourself, watch the money move.

## Cards

- [A launchpad let anyone drain everyone else's liquidity](unistreet-launch-drain.md) — Unistreet, Aug 2026
- [A token let anyone mint a million tokens to themselves](sandbox-delegate-mint.md) — Sandbox OFT, Aug 2026

### Defensive habits (protect yourself)

- [The approval that keeps draining you](protect-approvals.md) — token approvals, and how to revoke them

## How to read the proof yourself

```bash
# one free archive endpoint, no key, no wallet
export ETHEREUM_RPC_URL=https://eth.drpc.org
cd prove/scaffold && forge test --match-path ../proofs/UnistreetLaunchpad.t.sol -vv
```

You will see the attacker's balance before and after, and a `[PROOF]` line with what they gained.
