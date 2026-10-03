# Quorum pitch video — script (founder pitch, 2026-10-03)

Target ~90s. Role: technical founder to a grant reviewer. Distinct from the demo (which shows the
mechanism). The pitch makes the case: problem -> solution -> traction -> why it's new -> market + ask.
Brian voice (edge-tts en-US-BrianNeural), GAP mode. Every number verified real this session.

---

## P1 PROBLEM (~12s)
> Every week, a report says a smart contract has a critical bug. Usually, no one can tell if it is real. A finding is just a claim until someone runs it.

## P2 SOLUTION (~12s)
> Quorum only publishes a bug it can prove. It writes the exploit, runs it on a mainnet fork, and keeps the finding only if the attacker's balance goes up.

## P3 TRACTION (~18s)
> It has drained four real 2026 hacks to the wei, one with the answer withheld from the model. A cross-chain bridge confirmed a latent defect Quorum flagged on Robinhood Chain, with a fix scheduled. And it publishes its own miss rate: sixty-four percent recall, including the one row where Slither still wins.

## P4 WHY IT IS NEW (~15s)
> Three things are new together: disclosure gated on a running exploit, a tool that publishes how often it is wrong, and a proof that settles on-chain. Each proof burns a fee and records its digest in one transaction, so a record carries its own cost.

## P5 MARKET + ASK (~18s)
> It is built for protocol teams shipping money on Arbitrum and Robinhood Chain, and the researchers who disclose to them. Live on both chains today. Next, Quorum hunts and proves across every verified Arbitrum contract holding real money, and if nothing proves, it says so. Prove it, or drop it. Runquorum dot site.

---

## Real content verified (this session)
- Four proofs to the wei: Unistreet +0.0072 WETH, Sandbox +1,000,000 SAND, Squid +712 USDC, GaslessReservoir +0.836 WETH (blind). prove/proofs/*.json, bench/STREAM.md.
- 64% recall / 143 contracts / 11 runs; reentrancy 72% vs Slither 62%; Slither wins access-control. bench/BENCHMARK.md, bench/README.md:143, docs/index.html chart.
- Socket/Bungee (cross-chain bridge) confirmed a latent defect in its RFQ vault on Robinhood Chain, fix scheduled. ai/FINDING-rfq-vault-executor.md (private disclosure).
- On-chain claim: RH ClaimRegistry 0xDeA0..3Ea3, Arbitrum One ClaimRegistry 0xd2ca..2774, 100,000 QUORUM burned per claim. CLAUDE.md Verified Facts.
- Roadmap: hunt-and-prove across verified Arbitrum-chain contracts >$10k; kill test if nothing proves. SUBMISSION.md.
