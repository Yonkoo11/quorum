Status: draft (not filed) — Arbitrum Open House Singapore Online Buildathon
Submission deadline: 2026-10-04 15:59 UTC. Results: 2026-10-12 06:00 UTC.

<!-- Draft of the submission content. Form fields are behind login; map these sections to the
     actual fields once registered. Prize paid on Arbitrum One: provide the winner wallet address. -->

# Quorum — a bug report you cannot fake

**Pitch (<=5 words):** Proven exploits as on-chain claims.

**Tagline (<=12 words):** Quorum publishes a smart-contract bug only after running the exploit that drains it.

**Audience:** EVM protocol teams (starting on Robinhood Chain) and the researchers who disclose to them. Today a "finding" is a PDF claim; the team cannot tell a real exploit from a confident guess, and the researcher cannot prove priority. Quorum settles both.

## The problem

Most security findings are assertions. A scanner flags a line, a report asserts impact, and a team spends days deciding whether it is real. Across 16 recent audit contests, most of what gets reported never costs anyone a cent. The signal is buried in confident prose.

## What Quorum does

Quorum hunts EVM contracts, then writes a Foundry exploit on a mainnet fork and keeps the finding only if the exploit measurably moves the attacker's balance. A finding is a claim until an exploit settles it. Each settled proof becomes a paid on-chain claim: a record of "this address knew this digest at this time," written on Robinhood Chain in the same transaction that burns the fee, so a record cannot exist without its own cost.

- Four real 2026 hacks reproduced to the wei on a fork: Unistreet (0.0072 WETH), Sandbox (1,000,000 SAND), Squid (712 USDC), and GaslessReservoir (0.836 WETH), the last proven with the answer withheld from the model.
- It publishes its own miss rate: recall on 143 known-bug contracts, measured over eleven runs, and the row where Slither still beats it stays on the page.

## Live on Robinhood Chain (Arbitrum Orbit)

- **ClaimRegistry** (verified): `0xDeA0792cEc959CE6893C24dEeFc6FE9B047a3Ea3` on Robinhood Chain (chain id 4663).
- **QUORUM token:** `0xa6452Fd7134218f62056a304eaf501F8714A26b9`. The fee is 100,000 QUORUM per claim, pulled from the claimant and burned in the same transaction.
- **Claims are live through the registry** (deployed 2026-09-18, block 66593107, verified source): a claim is recorded on-chain at block 66594959 (tx `0x2f22250d…ffc3d`), the fee pulled and burned in the same transaction. (An earlier self-addressed claim from 2026-09-12 predates the registry contract.)
- Robinhood Chain is an Ethereum L2 built with Arbitrum Orbit (chain id 4663), so the deployment qualifies and sits in the reserved Robinhood-Chain slot.

## Also live on Arbitrum One (the reserved Arbitrum slot)

The same claim layer is deployed on Arbitrum One, with a real claim recorded and the fee burned on-chain, so the mechanism is live end-to-end on both chains:

- **ClaimRegistry (Arbitrum One):** `0xd2cad31A080b0daE98d9d6427e500B50bCb92774`
- **QUORUM token (Arbitrum One):** `0xf35bE6FFEBF91AcC27A78696cf912595C6b08AAA`
- First claim recorded at block 26102746; the 100,000 QUORUM fee was burned (token supply 1,000,000 to 900,000, registry holds zero). The Arbitrum QUORUM is a fresh deployment of the same fee token; the live market is on Robinhood Chain.

## Submission form answers (ready to paste)

**Core smart contract address(es):**
```
Robinhood Chain: 0xDeA0792cEc959CE6893C24dEeFc6FE9B047a3Ea3 — ClaimRegistry (mainnet, chain 4663)
Arbitrum One: 0xd2cad31A080b0daE98d9d6427e500B50bCb92774 — ClaimRegistry
```

**Token contract address(es):**
```
Robinhood Chain: 0xa6452Fd7134218f62056a304eaf501F8714A26b9 — QUORUM (mainnet, chain 4663)
Arbitrum One: 0xf35bE6FFEBF91AcC27A78696cf912595C6b08AAA — QUORUM
```

**Factory contracts:** none. The registry is a single contract; it does not create pools, vaults, or child contracts.

**Which parts were built during the Buildathon (2026-09-13 to 2026-10-04):** The repo's first commit is 2026-09-10, days before the window opened, as a memory + lenses experiment. Essentially everything that defines Quorum today was built inside the window (129 commits): the prove engine (a finding is kept only if its generated exploit runs and pays on a fork), the four wei-exact proofs, the blind benchmark, the on-chain `ClaimRegistry` + fee-burn claim layer, the Robinhood Chain and Arbitrum One deployments, and the prove-first site. The commit history is public and dated.

**Prize wallet (Arbitrum One):** [your public address]

## Mapped to the judging criteria

**1. Smart-contract quality.** `ClaimRegistry` is deliberately small: one fee, one claim, one invariant. A record is written only if at least the fee arrived and every token the registry held was burned, checked by balance before and after, so the fee can never be skipped and a stuck balance can never accrue. Verified source on both chains, 18 Foundry tests plus a fuzz test and an invariant (19 green). Slither and Aderyn were run on it; both flag a reentrancy pattern on `claim`, and both are false positives (explicit guard, mark-before-call ordering, one external function, and a test that exercises the re-entrant path). We leave the flags and the reasoning on the record rather than reporting "zero findings" (`contracts/STATIC-ANALYSIS.md`). For a security product, the contract is held to the standard the product sells.

**2. Product-market fit.** The user is a protocol team that needs to know a finding is real before it spends a week on it, and a researcher who needs to prove what they knew and when. The strongest signal to date: Socket/Bungee, a cross-chain bridge, confirmed that a latent defect Quorum independently flagged in its RFQ vault contract deployed on Robinhood Chain is real and not currently reachable, and that a fix is scheduled. Demand is early and we say so; this is the first protocol engagement, not the hundredth.

**3. Innovation.** Three things together are new: disclosure gated on a running exploit (publish only what drains on a fork), publishing the method's own miss rate rather than only its hits, and using an on-chain claim as the settlement layer so a proof is a record anyone can check.

## What happens after the deadline

Prizes here are development-milestone-tied, and Quorum already runs past the deadline:

- **By 2026-10-05:** run hunt-and-prove across every verified Arbitrum-chain contract (Robinhood Chain and Arbitrum One) holding more than $10k and publish the counts, proven and not.
- **By 2026-10-12:** follow up the four open disclosures from 2026-09-18 and the Socket/Bungee acknowledgment, and record any protocol that asks for a proof of its own contract.
- **By 2026-10-31:** the honest kill test. If no Arbitrum-chain team has asked for a proof of its own contract and the hunt has proven nothing on deployed contracts, the focus stops and the post-mortem is published.

## Links

- Repo (MIT): https://github.com/Yonkoo11/quorum
- The proofs: https://github.com/Yonkoo11/quorum/tree/main/prove/proofs
- Live site: https://runquorum.site
- Telegram: https://t.me/runQuorumchat

## Tech

Python hunt-and-prove engine; Foundry for the exploits and for `ClaimRegistry`; `web3.py` against Robinhood Chain for the token, fee burn, and claims. Verified source pulled from Blockscout/Sourcify across five chains, no API key.
