# Learn: real hacks, proven

Every card here explains one real 2026 hack in plain English, and every card is backed by an exploit
that **runs**. We do not describe an attack we cannot reproduce. Each card links a Foundry test in
[`../prove/proofs/`](../prove/proofs) that forks the chain at the block the bug was live and drains the
contract for real; the number in the card is the number that test prints.

That is the whole rule of this section, and it is the same rule the rest of Quorum lives under:

> **We show, we do not assert. If we can't prove it on a fork, it isn't here.**

Most "scam awareness" content is generic and unfalsifiable. These cards are the opposite: pick any
one, run the test yourself, watch the money move.

## Cards

- [A launchpad let anyone drain everyone else's liquidity](unistreet-launch-drain.md) — Unistreet, Aug 2026
- [A token let anyone mint a million tokens to themselves](sandbox-delegate-mint.md) — Sandbox OFT, Aug 2026

## How to read the proof yourself

```bash
# one free archive endpoint, no key, no wallet
export ETHEREUM_RPC_URL=https://eth.drpc.org
cd prove/scaffold && forge test --match-path ../proofs/UnistreetLaunchpad.t.sol -vv
```

You will see the attacker's balance before and after, and a `[PROOF]` line with what they gained.
