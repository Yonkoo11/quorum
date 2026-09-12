# Baseline — Slither 0.11.4 on DeFiVulnLabs

Run 2026-09-12 · corpus commit `f61f6ee` · 57 files, 54 compiled · 10 targets · compilers: 0.7.6 ×3, 0.8.18 ×2, 0.8.35 ×49 · `python bench/slither.py <corpus>`

Same unit and same harsh rule as `bench/run.py`: a (file, function, risk); every finding that is not on a labelled function counts as false. A file Slither could not compile is a miss for every target in it.

| risk | targets | **strict found** | true | **precision** | **recall** | loose found | true | precision | recall |
|---|---|---|---|---|---|---|---|---|---|
| reentrancy | 4 | **5** | 2 | **40%** | **50%** | 42 | 2 | 5% | 50% |
| unguarded-state-write | 2 | **13** | 1 | **8%** | **50%** | 13 | 1 | 8% | 50% |
| unsafe-math | 4 | **2** | 1 | **50%** | **25%** | 2 | 1 | 50% | 25% |
| **all** | 10 | **20** | 4 | **20%** | **40%** | 57 | 4 | 7% | 40% |

Strict: the detectors Slither rates High or Medium for the risk. Loose: strict plus its Low and Informational detectors, the analogue of counting any single lens.

## Files Slither could not analyse (3)

- `Dirtybytes.sol` — no installed compiler matches the pragma
- `NFTMint_exposedMetadata.sol` — 0.8.35
- `ReadOnlyReentrancy.sol` — 0.8.18

## Strict findings that are not on a labelled target

- `DOS.sol` `claimThrone` reentrancy
- `Delegatecall.sol` `fallback` unguarded-state-write
- `Immunefi_ch1.sol` `safeMint` reentrancy
- `Randomness.sol` `guess` unguarded-state-write
- `Reentrancy.sol` `Attack` unguarded-state-write
- `Selfdestruct.sol` `dos` unguarded-state-write
- `Selfdestruct2.sol` `attack` unguarded-state-write
- `Storage-collision.sol` `testcollision` unguarded-state-write
- `Uninitialized_variables.sol` `_upgradeToAndCall` unguarded-state-write
- `Uninitialized_variables.sol` `attack` unguarded-state-write
- `Uninitialized_variables.sol` `constructor` unguarded-state-write
- `Uninitialized_variables.sol` `initialize` unguarded-state-write
- `Uninitialized_variables.sol` `upgradeToAndCall` unguarded-state-write
- `first-deposit.sol` `deposit` reentrancy
- `first-deposit.sol` `tokenToShares` unsafe-math
- `gas-price.sol` `_nativeTransferExec` unguarded-state-write

## Targets strict Slither missed

- `Overflow.sol` `increaseLockTime` unsafe-math
- `Overflow2.sol` `_transfer` unsafe-math
- `Precision-loss.sol` `getCurrentReward` unsafe-math
- `ReadOnlyReentrancy.sol` `getReward` reentrancy
- `Unprotected-callback.sol` `mint` reentrancy
- `Visibility.sol` `changeOwner` unguarded-state-write
