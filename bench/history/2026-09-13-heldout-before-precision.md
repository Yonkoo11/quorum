# Benchmark — the six lenses on DeFiVulnLabs

Run 2026-09-13 · corpus commit `f61f6ee` · 57 files scanned · 10 targets · quorum threshold 2 · `python bench/run.py <corpus> --labels bench/labels/defivulnlabs.json`

Unit: a (file, function, risk). A target is a labelled function whose bug maps to a risk Quorum covers. Precision counts every finding not on a target as false, including hits on files the corpus labels for some other bug.

| risk | targets | any-lens found | true | precision | recall | **quorum confirmed** | true | **precision** | **recall** |
|---|---|---|---|---|---|---|---|---|---|
| reentrancy | 4 | 60 | 2 | 3% | 50% | **4** | 2 | **50%** | **50%** |
| unguarded-state-write | 2 | 37 | 1 | 3% | 50% | **1** | 1 | **100%** | **50%** |
| unsafe-math | 4 | 18 | 2 | 11% | 50% | **4** | 1 | **25%** | **25%** |
| **all** | 10 | 115 | 5 | 4% | 50% | **9** | 4 | **44%** | **40%** |

## Per lens

| lens | sightings | on a target |
|---|---|---|
| callorder-lens | 4 | 2 |
| guard-lens | 60 | 2 |
| modifier-lens | 37 | 1 |
| sender-lens | 1 | 1 |
| wrap-lens | 7 | 2 |
| bound-lens | 15 | 1 |

Candidates held back by the rule (one lens only): 106, of which on a target: 1.

## Confirmed findings that are not on a labelled target

- `DOS.sol` `claimThrone` reentrancy — callorder-lens, guard-lens
- `Invariant.sol` `withdrawMoney` unsafe-math — bound-lens, wrap-lens
- `Overflow.sol` `deposit` unsafe-math — bound-lens, wrap-lens
- `self-transfer.sol` `testSelfTransfer` reentrancy — callorder-lens, guard-lens
- `self-transfer.sol` `transfer` unsafe-math — bound-lens, wrap-lens

## Targets the rule missed

- `Divmultiply.sol` `price` unsafe-math — seen by no lens
- `Overflow2.sol` `_transfer` unsafe-math — seen by wrap-lens
- `Precision-loss.sol` `getCurrentReward` unsafe-math — seen by no lens
- `ReadOnlyReentrancy.sol` `getReward` reentrancy — seen by no lens
- `Unprotected-callback.sol` `mint` reentrancy — seen by no lens
- `txorigin.sol` `transfer` unguarded-state-write — seen by no lens
