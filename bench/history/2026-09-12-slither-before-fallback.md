# Baseline — Slither 0.11.4 on SmartBugs-curated

Run 2026-09-12 · corpus commit `230e649` · 143 files, 139 compiled · 71 targets · compilers: 0.4.24 ×1, 0.4.25 ×2, 0.4.26 ×135, 0.4.9 ×1 · `python bench/slither.py <corpus>`

Same unit and same harsh rule as `bench/run.py`: a (file, function, risk); every finding that is not on a labelled function counts as false. A file Slither could not compile is a miss for every target in it.

| risk | targets | **strict found** | true | **precision** | **recall** | loose found | true | precision | recall |
|---|---|---|---|---|---|---|---|---|---|
| reentrancy | 31 | **45** | 28 | **62%** | **90%** | 102 | 28 | 27% | 90% |
| unguarded-state-write | 19 | **37** | 6 | **16%** | **32%** | 37 | 6 | 16% | 32% |
| unsafe-math | 21 | **4** | 0 | **0%** | **0%** | 11 | 1 | 9% | 5% |
| **all** | 71 | **86** | 34 | **40%** | **48%** | 150 | 35 | 23% | 49% |

Strict: the detectors Slither rates High or Medium for the risk. Loose: strict plus its Low and Informational detectors, the analogue of counting any single lens.

## Files Slither could not analyse (4)

- `reentrancy_bonus.sol` — 0.4.26
- `reentrancy_cross_function.sol` — 0.4.26
- `reentrancy_insecure.sol` — 0.5.0
- `0x89c1b3807d4c67df034fffb62f3509561218d30b.sol` — 0.4.26

## Strict findings that are not on a labelled target

- `0x07f7ecb66d788ab01dc93b9b71a88401de7d0f2e.sol` `loseWager` unguarded-state-write
- `0x07f7ecb66d788ab01dc93b9b71a88401de7d0f2e.sol` `payout` unguarded-state-write
- `0x19cf8481ea15427a98ba3cdd6d9e14690011ab10.sol` `FundsTransfer` unguarded-state-write
- `0x19cf8481ea15427a98ba3cdd6d9e14690011ab10.sol` `sendTokenAw` reentrancy
- `0x3f2ef511aa6e75231e4deafc7a3d2ecab3741de2.sol` `redeem` unguarded-state-write
- `0x52d2e0f9b01101a59b38a3d05c80b7618aeed984.sol` `getTokens` unguarded-state-write
- `0x52d2e0f9b01101a59b38a3d05c80b7618aeed984.sol` `withdrawEther` unguarded-state-write
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `_bid` unguarded-state-write
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `_breedWith` reentrancy
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `_createPanda` reentrancy
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `_triggerCooldown` reentrancy
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `bidERC20` reentrancy
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `bidOnSiringAuction` reentrancy
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `breedWithAuto` reentrancy
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `giveBirth` reentrancy
- `0x70f9eddb3931491aab1aeafbc1e7f1ca2a012db4.sol` `GetHoneyFromJar` unguarded-state-write
- `0x78c2a1e91b52bca4130b6ed9edd9fbcfd4671c37.sol` `redeem` unguarded-state-write
- `0x7a4349a749e59a5736efb7826ee3496a2dfd5489.sol` `GetFreebie` unguarded-state-write
- `0x7d09edb07d23acb532a82be3da5c17d9d85806b4.sol` `loseWager` unguarded-state-write
- `0x7d09edb07d23acb532a82be3da5c17d9d85806b4.sol` `payout` unguarded-state-write
- `0x806a6bd219f162442d992bdc4ee6eba1f2c5a707.sol` `GetPie` unguarded-state-write
- `0x958a8f594101d2c0485a52319f29b2647f2ebc06.sol` `sendMessage` unguarded-state-write
- `0xb7c5c5aa4d42967efe906e1b66cb8df9cebf04f7.sol` `withdraw` reentrancy
- `0xd2018bfaa266a9ec0a1a84b061640faa009def76.sol` `Get` unguarded-state-write
- `0xdb1c55f6926e7d847ddf8678905ad871a68199d2.sol` `GetFreebie` unguarded-state-write
- `0xe09b1ab8111c2729a76f16de96bc86a7af837928.sol` `sendFunds` unguarded-state-write
- `0xe09b1ab8111c2729a76f16de96bc86a7af837928.sol` `wager` reentrancy
- `0xe4eabdca81e31d9acbc4af76b30f532b6ed7f3bf.sol` `GetFreebie` unguarded-state-write
- `0xe82f0742a71a02b9e9ffc142fdcb6eb1ed06fb87.sol` `GetFreebie` unguarded-state-write
- `0xec329ffc97d75fe03428ae155fc7793431487f63.sol` `run` reentrancy
- `0xf70d589d76eebdd7c12cc5eec99f8f6fa4233b9e.sol` `GetFreebie` unguarded-state-write
- `FibonacciBalance.sol` `fallback` unguarded-state-write
- `FindThisHash.sol` `solve` unguarded-state-write
- `ether_lotto.sol` `play` unguarded-state-write
- `governmental_survey.sol` `resetInvestment` unguarded-state-write
- `guess_the_random_number.sol` `guess` unguarded-state-write
- `king_of_the_ether_throne.sol` `claimThrone` unsafe-math
- `lotto.sol` `withdrawLeftOver` unguarded-state-write
- `lottopollo.sol` `payOut` unguarded-state-write
- `odds_and_evens.sol` `andTheWinnerIs` unguarded-state-write
- `parity_wallet_bug_1.sol` `confirm` reentrancy
- `parity_wallet_bug_1.sol` `kill` unguarded-state-write
- `parity_wallet_bug_2.sol` `confirm` reentrancy
- `roulette.sol` `fallback` unguarded-state-write
- `rubixi.sol` `collectPercentOfFees` unsafe-math
- `smart_billions.sol` `commitDividend` unsafe-math
- `smart_billions.sol` `invest` unsafe-math
- `spank_chain_payment.sol` `byzantineCloseChannel` reentrancy
- `spank_chain_payment.sol` `consensusCloseChannel` unguarded-state-write
- `spank_chain_payment.sol` `createChannel` reentrancy
- `spank_chain_payment.sol` `deposit` reentrancy
- `spank_chain_payment.sol` `joinChannel` reentrancy

## Targets strict Slither missed

- `BECToken.sol` `batchTransfer` unsafe-math
- `arbitrary_location_write_simple.sol` `PopBonusCode` unguarded-state-write
- `incorrect_constructor_name1.sol` `IamMissing` unguarded-state-write
- `incorrect_constructor_name2.sol` `missing` unguarded-state-write
- `incorrect_constructor_name3.sol` `Constructor` unguarded-state-write
- `insecure_transfer.sol` `transfer` unsafe-math
- `integer_overflow_1.sol` `add` unsafe-math
- `integer_overflow_add.sol` `run` unsafe-math
- `integer_overflow_benign_1.sol` `run` unsafe-math
- `integer_overflow_mapping_sym_1.sol` `init` unsafe-math
- `integer_overflow_minimal.sol` `run` unsafe-math
- `integer_overflow_mul.sol` `run` unsafe-math
- `integer_overflow_multitx_multifunc_feasible.sol` `run` unsafe-math
- `integer_overflow_multitx_onefunc_feasible.sol` `run` unsafe-math
- `mapping_write.sol` `set` unguarded-state-write
- `multiowned_vulnerable.sol` `newOwner` unguarded-state-write
- `overflow_simple_add.sol` `add` unsafe-math
- `overflow_single_tx.sol` `overflowaddtostate` unsafe-math
- `overflow_single_tx.sol` `overflowlocalonly` unsafe-math
- `overflow_single_tx.sol` `overflowmulocalonly` unsafe-math
- `overflow_single_tx.sol` `overflowmultostate` unsafe-math
- `overflow_single_tx.sol` `underflowlocalonly` unsafe-math
- `overflow_single_tx.sol` `underflowtostate` unsafe-math
- `parity_wallet_bug_1.sol` `initWallet` unguarded-state-write
- `parity_wallet_bug_2.sol` `initWallet` unguarded-state-write
- `reentrancy_bonus.sol` `getFirstWithdrawalBonus` reentrancy
- `reentrancy_cross_function.sol` `withdrawBalance` reentrancy
- `reentrancy_insecure.sol` `withdrawBalance` reentrancy
- `rubixi.sol` `DynamicPyramid` unguarded-state-write
- `timelock.sol` `increaseLockTime` unsafe-math
- `token.sol` `transfer` unsafe-math  (seen by a loose detector)
- `tokensalechallenge.sol` `buy` unsafe-math
- `tokensalechallenge.sol` `sell` unsafe-math
- `unprotected0.sol` `changeOwner` unguarded-state-write
- `wallet_02_refund_nosub.sol` `refund` unguarded-state-write
- `wallet_03_wrong_constructor.sol` `initWallet` unguarded-state-write
- `wallet_04_confused_sign.sol` `withdraw` unguarded-state-write
