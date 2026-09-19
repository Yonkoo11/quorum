# Benchmark — the 8 lenses on DeFiVulnLabs

Run 2026-09-19 · corpus commit `f61f6ee` · 57 files scanned · 10 targets · quorum threshold 2 · `python bench/run.py <corpus> --labels bench/labels/defivulnlabs.json`

Unit: a (file, function, risk). A target is a labelled function whose bug maps to a risk Quorum covers. Precision counts every finding not on a target as false, including hits on files the corpus labels for some other bug.

| risk | targets | any-lens found | true | precision | recall | **quorum confirmed** | true | **precision** | **recall** |
|---|---|---|---|---|---|---|---|---|---|
| reentrancy | 4 | 43 | 2 | 5% | 50% | **3** | 2 | **67%** | **50%** |
| unguarded-state-write | 2 | 51 | 1 | 2% | 50% | **1** | 1 | **100%** | **50%** |
| unsafe-math | 4 | 19 | 2 | 11% | 50% | **4** | 2 | **50%** | **50%** |
| accounting-mismatch | 0 | 9 | 0 | 0% | n/a | **0** | 0 | **n/a** | **n/a** |
| **all** | 10 | 122 | 5 | 4% | 50% | **8** | 5 | **62%** | **50%** |

## Per lens

| lens | sightings | on a target |
|---|---|---|
| callorder-lens | 3 | 2 |
| guard-lens | 43 | 2 |
| modifier-lens | 51 | 1 |
| sender-lens | 1 | 1 |
| wrap-lens | 6 | 2 |
| bound-lens | 17 | 2 |
| ledger-lens | 0 | 0 |
| payout-lens | 9 | 0 |

Candidates held back by the rule (one lens only): 114, of which on a target: 0.

## Confirmed findings that are not on a labelled target

- `DOS.sol` `claimThrone` reentrancy — callorder-lens, guard-lens
- `Invariant.sol` `withdrawMoney` unsafe-math — bound-lens, wrap-lens
- `self-transfer.sol` `transfer` unsafe-math — bound-lens, wrap-lens

## Targets the rule missed

- `Divmultiply.sol` `price` unsafe-math — seen by no lens
- `Precision-loss.sol` `getCurrentReward` unsafe-math — seen by no lens
- `ReadOnlyReentrancy.sol` `getReward` reentrancy — seen by no lens
- `Unprotected-callback.sol` `mint` reentrancy — seen by no lens
- `txorigin.sol` `transfer` unguarded-state-write — seen by no lens
