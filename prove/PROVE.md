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

## First results (2026-09-27, the nine in-sample hacks)

| hack | hypothesis (v4) | verdict | what execution showed |
|---|---|---|---|
| UnistreetLaunchpad | `launch` takes every earlier launch's LP (conf 95) | **PROVEN** | attacker, an ordinary EOA, drains an earlier launch's position; +0.00721 WETH, reproduces to the wei on two independent archive nodes; no faked state, no role impersonated |
| Vault4626 | `redeem` pays the whole idle balance to one redeemer (conf 90) | **unproven** | at the block, available idle USDC is exactly zero (offset by pending referral fees), and a fresh depositor never enters the vulnerable branch; the conf-90 finding does not survive execution |

Two results, opposite directions, and that is the point. A confidence-90 finding from the strongest
hunter available did not survive a fork; a proof of a real hack was produced blind from a one-line
hypothesis and reproduces for anyone with Foundry and an archive endpoint. Neither the score nor the
reviewer's read decided it. The exploit did.

## What proving needs that labelling does not

The recall corpus fetches the **implementation** source (where the bug is written). A proof must hit
the **proxy** the users funded (where the state is). The first Vault4626 run failed on an empty
implementation address until the proxy was supplied; `fork-blocks.json` carries the proxy per hack,
and stream intake records both.

## Setup

`scaffold/lib/forge-std` is a local `forge install foundry-rs/forge-std` (a symlink here on the dev
machine). Endpoints come from `<CHAIN>_RPC_URL`; free archive nodes serve Ethereum, Base and Polygon
at these blocks, BNB Chain does not, so ORB reads as unprovable rather than failed.
