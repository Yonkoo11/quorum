# Quorum demo — script (prove-engine rebuild, 2026-10-02)

Target ~100s, Security archetype. Narration ~135 wpm. Every number and line is real.
Replaces the v0.1.0 (lens/memory) cut. Narration is second person, tied to what is on screen.

---

## Scene 1 — HOOK (~10s)
**On screen:** "Prove it. Or drop it." Then four lines fade in: Unistreet 0.0072 WETH ·
Sandbox 1,000,000 SAND · Squid 712 USDC · GaslessReservoir 0.836 WETH.
**Narration:**
> Most security findings are a confident guess. Quorum publishes only the ones it can prove, by
> running the exploit until the money actually moves.

## Scene 2 — CONTRAST (~12s)
**On screen:** left: "a scanner flags a line" (greyed). right: "Quorum writes the exploit on a fork"
(accent). The right side runs; the left just asserts.
**Narration:**
> A scanner flags a line and a report asserts impact. Quorum writes a Foundry exploit on a mainnet
> fork, and keeps the finding only if the attacker's balance goes up.

## Scene 3 — THE PROVE LOOP (terminal, ~30s)
**On screen:** real terminal. The hunt finds a candidate, the harness writes the exploit, the fork
runs, the drain prints to the wei. (Recorded from `prove/` on one of the four — Squid, 712 USDC,
or GaslessReservoir proven blind.)
**Narration:**
> Here it takes a real 2026 hack, finds the entry on-chain, and drains it on a fork. Seven hundred
> and twelve USDC, moved. Four hacks reproduced this way, each to the wei, one of them with the
> answer withheld from the model.

## Scene 4 — THE HONESTY METRIC (~15s)
**On screen:** recall line 1% to 64% across eleven runs; a small table where Slither still wins one
row, left on the page.
**Narration:**
> It also publishes how often it is wrong. Recall on 143 known-bug contracts, measured over eleven
> runs. The one row where Slither still beats it stays on the page.

## Scene 5 — THE ON-CHAIN CLAIM (~18s)
**On screen:** the ClaimRegistry. A claim lands: the 100,000 QUORUM fee is burned, the digest
recorded, in one transaction. Two chain badges light: Robinhood Chain, Arbitrum One.
**Narration:**
> A proof is not a PDF. Each one settles as a paid on-chain claim: the registry burns the fee and
> records the digest in a single transaction, so a record cannot exist without its own cost. Live on
> Robinhood Chain and Arbitrum One.

## Scene 6 — CLOSE (~10s)
**On screen:** "Prove it. Or drop it." · runquorum.site · Live on Robinhood Chain and Arbitrum One ·
Arbitrum Open House Singapore.
**Narration:**
> Quorum. Prove it, or drop it. Live at runquorum dot site.

---

## Real content this script shows (verified)
- Four proofs to the wei: Unistreet 0.0072 WETH, Sandbox 1,000,000 SAND, Squid 712 USDC,
  GaslessReservoir 0.836 WETH (blind). Source: `prove/proofs/`.
- Recall 1% to 64% over 11 runs; reentrancy precision 72% (two-agree) vs Slither 62%; Slither wins
  access-control. Source: `bench/`.
- On-chain claim, fee burned: RH ClaimRegistry 0xDeA0…3Ea3 (claim at block 66594959); Arbitrum One
  ClaimRegistry 0xd2cad31…2774 + QUORUM 0xf35b…8AAA (claim verified 2026-10-02, supply 1,000,000→900,000).

## Word count
~160 words over ~95s of narration (hook + 5 scenes), inside the 135–150 wpm band with room for the
terminal beat to breathe.
