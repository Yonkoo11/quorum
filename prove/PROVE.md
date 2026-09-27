# The prove stage: a hypothesis is a finding only when its exploit runs and pays

A hunter (Pashov v4, a model, a person) says a function is exploitable. That is a claim. This stage
settles it by execution: a model is handed a Foundry workspace forked at the block the bug was live,
the victim's deployed address, and the one hypothesis, and writes an exploit. The scaffold
([`scaffold/src/ForkPoCBase.sol`](scaffold/src/ForkPoCBase.sol)) measures the attacker's real balance
change and prints `[PROOF]` only when it grew, so the proof is the measured profit, not anything the
exploit asserts. The harness then re-runs the saved PoC with no model in the loop and rejects it if
it rewrites the chain (`vm.store/etch/mockCall`) or impersonates anyone but the attacker.

```
python prove/harness.py prove <hack> --item <n>   # model writes + iterates the exploit
python prove/harness.py check <hack>              # reproduce from the saved .t.sol, model gone
```

## Results on the nine in-sample hacks (2026-09-27)

Each row is v4's own hypothesis, run through the prove stage. Blocks are the exploit's parent block;
addresses are the funded proxy, not the implementation the source was read from.

| hack | chain | verdict | what execution showed |
|---|---|---|---|
| UnistreetLaunchpad | ethereum | **PROVEN** | attacker (an EOA) drains an earlier launch's LP; +0.0072 WETH; reproduces to the wei on two archive nodes |
| SandboxOFT | base | **PROVEN** | attacker becomes the OApp delegate and mints 1,000,000 SAND; reproduces; **overturns a blind reviewer who had called this route false** |
| RoyalRoyalties | polygon | reachable, no profit | the zero-amount owner-rewrite bug executes exactly as labelled, but Royal1155LDA has no payout path and the marketplace/royalty contracts are `address(0)` at the block, so nothing pays on a bare fork |
| NewMarketTrading (Squid) | ethereum | reachable, no profit | the forged-payload source-check bypass executes, but the express model makes the attacker front the same token the safe receives (break-even); a real drain needs the specific victim Safe's standing allowances, which a bare fork of the module does not carry |
| Vault4626 (redeem) | base | unproven | v4's confidence-90 redeem finding: available idle is exactly zero at the block, and a fresh depositor never enters the vulnerable branch |
| Reddio | ethereum | unproven | no attacker profit reached from the double-count hypothesis on the fork |
| Startale | ethereum | unprovable on a historical fork | the re-init guard is a transient-storage flag set only inside the original deploy transaction; a later-block fork cannot reproduce that without `vm.store`, which is banned. The attacker call reverts at the guard |
| EtherFiAtomicQueue | ethereum | not settled | the model hit the 30-minute cap before writing an exploit; needs a longer run |
| ORB | bsc | unprovable | no free BNB Chain archive endpoint; needs a paid key |

**Two clean drains proven blind, and the rest sorted honestly.** The prove stage separates three
things a score and a reader cannot: a bug that pays (Unistreet, Sandbox), a real bug that needs
state a bare fork lacks to monetize (Royal, Squid), and a finding that does not survive at all
(Vault4626's conf-90, Reddio). Two blind reviewers earlier rated both Royal and Squid REAL-LOSS;
execution shows they are real but do not pay as isolated forks. One rated Sandbox false; execution
shows it pays. That gap is the number Quorum publishes and nobody else does.

Known limits this surfaced: a historical fork cannot carry same-transaction transient state
(Startale) or a particular victim's pre-existing allowances (Squid) without more setup than the bare
victim contract; those are provable with extra scaffolding, not with `vm.store`.

## What proving needs that labelling does not

The recall corpus fetches the **implementation** source (where the bug is written). A proof must hit
the **proxy** the users funded (where the state is). The first Vault4626 run failed on an empty
implementation address until the proxy was supplied; `fork-blocks.json` carries the proxy per hack,
and stream intake records both.

## Setup

`scaffold/lib/forge-std` is a local `forge install foundry-rs/forge-std` (a symlink here on the dev
machine). Endpoints come from `<CHAIN>_RPC_URL`; free archive nodes serve Ethereum, Base and Polygon
at these blocks, BNB Chain does not, so ORB reads as unprovable rather than failed.
