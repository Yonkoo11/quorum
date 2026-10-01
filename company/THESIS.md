# Quorum — company thesis

Status: draft
Started: 2026-10-01

> Method and the D0-D5 ladder: ~/.claude/skills/company-thesis/SKILL.md
> Lines starting with ">" are guidance and are ignored by company-check.sh.
> A block counts as filled when it has one line that is not a quote, not blank, not TODO.

## 1. Who exactly

- Who: teams shipping contracts that hold money on Robinhood Chain (chain 4663): launchpad factories, pools, vaults, dividend and staking contracts. Contactable through their public repos (issue trackers) and X accounts.
- How many: 121 public repos match "robinhood chain" solidity created since 2026-07-01, and 1,536 repos mention Robinhood Chain (GitHub search API, run 2026-10-01). Deployed-contract count not measured: the explorer refused scripted search.
- What they do today: ship without a review, or ask a permission scanner (KAY9, kay9.io). On 2026-09-18 Quorum read public Robinhood Chain repos and found four real bugs, including a factory whose sell path pays ETH without taking the tokens (anyone could empty it) and a vault whose reward pool can be re-entered and drained (ai/DISCLOSURE-robinhood.md).
- What it costs them: the funds in the contract. Chain TVL is near $1.5B (SpendNode, 2026-09-29). Context: buyers lost $18.43M to one rug syndicate (TechFlow), a different problem already served by TrustSwap, Bubblemaps and KAY9; Quorum does not compete there.
- The gap: no product on Robinhood Chain publishes exploit findings proven by execution on a fork, with the tool's own blind error rate next to them.

## 2. Demand evidence

Level: D1

> D0 asserted · D1 a stranger's words in public · D2 a named requester · D3 a conversation
> D4 a commitment without money · D5 money or use.
> One line per piece of evidence, newest first:
>   - D2 2026-09-16 <who asked and for what> — <link or person + date>
> The stated Level must be backed by an evidence line at that level.

- D1 2026-10-01 Immunefi rejects reports with "no PoC or an incomplete PoC if it is required by the project's bug bounty program": the market's own bar is a proof, not a flag — https://immunefi.com/rules/
- D1 2026-10-01 two strangers are building security tooling for Robinhood Chain in this same event: WHITEHAT ("AI-native DeFi security research network on Robinhood Chain", created 2026-09-14) and Tripwire (signed launch-risk forecasts) — https://github.com/TehWhitehat/whitehat , https://github.com/cavemancoop/tripwire-launch-auditor-public
- D1 2026-09-29 context only (buyer losses, served by others): "GoPlus tracing over $9M in losses" — https://www.spendnode.io/blog/robinhood-chain-memecoin-rug-factories-9m-september-2026/
- No D2 or D3 yet: none of the four maintainers told about bugs on 2026-09-18 has replied.

## 3. Distribution

> Channels ranked, then the ones that have actually been used. A channel is not distribution
> until a message has left:
>   - Sent: 2026-09-16 <where> — <link> — <what came back, including "no reply yet">

Ranked:
1. Maintainers of Robinhood Chain repos holding money: a public issue with the bug and the fix, then the proof once a deployed address exists.
2. The Arbitrum Open House Discord and Robinhood Chain builder channels: proven findings posted as they land.
3. Launch teams who want a proof their contract cannot be drained before they list it, paid per claim in USDG.
4. t.me/runQuorumchat (Quorum's own channel, diary posts since 2026-09-17).

- Sent: 2026-09-18 GitHub issue, Damirogly/robinhood-marian-vault — https://github.com/Damirogly/robinhood-marian-vault/issues/1 — no reply yet (0 comments on 2026-10-01)
- Sent: 2026-09-18 GitHub issue, robyn-os/robyn-os — https://github.com/robyn-os/robyn-os/issues/1 — no reply yet (0 comments on 2026-10-01)
- Sent: 2026-09-18 GitHub issue, aashu91/robinhood-evm-mcp — https://github.com/aashu91/robinhood-evm-mcp/issues/24 — no reply yet (0 comments on 2026-10-01)
- Sent: 2026-09-18 GitHub issue, maxence81/Aura-Protocol — https://github.com/maxence81/Aura-Protocol/issues/1 — no reply yet (0 comments on 2026-10-01)

## 4. Why this team, why now

Quorum already proves exploits by running them on a fork (four real 2026 hacks reproduced to the wei) and already records paid claims on Robinhood Chain (first paid claim at block 60762176, 2026-09-12). The rug wave on Robinhood Chain peaked July to September 2026, so the problem and the chain are both this quarter's.

## 5. After the deadline

- 2026-10-05 run hunt-and-prove on every verified Robinhood Chain contract holding more than $10k and publish the counts, proven and unproven
- 2026-10-12 follow up on the four 2026-09-18 issues; record replies here
- 2026-10-31 decide: keep going if one team has asked for a proof of its own contract, else write the post-mortem

## 6. Kill test

If by 2026-10-31 no Robinhood Chain team has asked for a proof of its own contract and the hunt proves nothing on deployed contracts, stop the Robinhood Chain focus.
