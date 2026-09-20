# Benchmark — the 9 lenses on SmartBugs-curated

Run 2026-09-20 · corpus commit `230e649` · 143 files scanned · 73 targets · quorum threshold 2 · `python bench/run.py <corpus>`

Unit: a (file, function, risk). A target is a labelled function whose bug maps to a risk Quorum covers. Precision counts every finding not on a target as false, including hits on files the corpus labels for some other bug.

| risk | targets | any-lens found | true | precision | recall | **quorum confirmed** | true | **precision** | **recall** |
|---|---|---|---|---|---|---|---|---|---|
| reentrancy | 31 | 91 | 28 | 31% | 90% | **39** | 28 | **72%** | **90%** |
| unguarded-state-write | 21 | 216 | 9 | 4% | 43% | **5** | 2 | **40%** | **10%** |
| unsafe-math | 21 | 172 | 21 | 12% | 100% | **49** | 17 | **35%** | **81%** |
| accounting-mismatch | 0 | 34 | 0 | 0% | n/a | **4** | 0 | **0%** | **n/a** |
| **all** | 73 | 513 | 58 | 11% | 79% | **97** | 47 | **48%** | **64%** |

## Per lens

| lens | sightings | on a target |
|---|---|---|
| callorder-lens | 39 | 28 |
| guard-lens | 91 | 28 |
| modifier-lens | 208 | 9 |
| sender-lens | 7 | 1 |
| consistency-lens | 6 | 1 |
| wrap-lens | 172 | 21 |
| bound-lens | 49 | 17 |
| ledger-lens | 7 | 0 |
| payout-lens | 31 | 0 |

Candidates held back by the rule (one lens only): 416, of which on a target: 11.

## Confirmed findings that are not on a labelled target

- `0x07f7ecb66d788ab01dc93b9b71a88401de7d0f2e.sol` `donate` reentrancy — callorder-lens, guard-lens
- `0x07f7ecb66d788ab01dc93b9b71a88401de7d0f2e.sol` `donateToWhale` unsafe-math — bound-lens, wrap-lens
- `0x07f7ecb66d788ab01dc93b9b71a88401de7d0f2e.sol` `loseWager` unsafe-math — bound-lens, wrap-lens
- `0x07f7ecb66d788ab01dc93b9b71a88401de7d0f2e.sol` `play` reentrancy — callorder-lens, guard-lens
- `0x19cf8481ea15427a98ba3cdd6d9e14690011ab10.sol` `createDaoPOLSKAtokens` unsafe-math — bound-lens, wrap-lens
- `0x19cf8481ea15427a98ba3cdd6d9e14690011ab10.sol` `refundTRA` unsafe-math — bound-lens, wrap-lens
- `0x19cf8481ea15427a98ba3cdd6d9e14690011ab10.sol` `setBonusCreationRate` unsafe-math — bound-lens, wrap-lens
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `_triggerCooldown` unsafe-math — bound-lens, wrap-lens
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `bidERC20` unguarded-state-write — consistency-lens, modifier-lens
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `withdrawBalance` unsafe-math — bound-lens, wrap-lens
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `withdrawERC20Balance` accounting-mismatch — ledger-lens, payout-lens
- `0x7d09edb07d23acb532a82be3da5c17d9d85806b4.sol` `donate` reentrancy — callorder-lens, guard-lens
- `0x7d09edb07d23acb532a82be3da5c17d9d85806b4.sol` `donateToWhale` unsafe-math — bound-lens, wrap-lens
- `0x7d09edb07d23acb532a82be3da5c17d9d85806b4.sol` `loseWager` unsafe-math — bound-lens, wrap-lens
- `0x7d09edb07d23acb532a82be3da5c17d9d85806b4.sol` `play` reentrancy — callorder-lens, guard-lens
- `0x89c1b3807d4c67df034fffb62f3509561218d30b.sol` `cancel` reentrancy — callorder-lens, guard-lens
- `0x89c1b3807d4c67df034fffb62f3509561218d30b.sol` `request` reentrancy — callorder-lens, guard-lens
- `0x89c1b3807d4c67df034fffb62f3509561218d30b.sol` `reset` unsafe-math — bound-lens, wrap-lens
- `0xb11b2fed6c9354f7aa2f658d3b4d7b31d8a13b77.sol` `withdraw` accounting-mismatch — ledger-lens, payout-lens
- `0xb7c5c5aa4d42967efe906e1b66cb8df9cebf04f7.sol` `withdraw` reentrancy — callorder-lens, guard-lens
- `0xbaa3de6504690efb064420d89e871c27065cdd52.sol` `withdraw` accounting-mismatch — ledger-lens, payout-lens
- `0xbebbfe5b549f5db6e6c78ca97cac19d1fb03082c.sol` `withdraw` accounting-mismatch — ledger-lens, payout-lens
- `0xe09b1ab8111c2729a76f16de96bc86a7af837928.sol` `play` unsafe-math — bound-lens, wrap-lens
- `0xe09b1ab8111c2729a76f16de96bc86a7af837928.sol` `sendRefund` unsafe-math — bound-lens, wrap-lens
- `0xe09b1ab8111c2729a76f16de96bc86a7af837928.sol` `wager` reentrancy — callorder-lens, guard-lens
- `0xe09b1ab8111c2729a76f16de96bc86a7af837928.sol` `wager` unsafe-math — bound-lens, wrap-lens
- `0xec329ffc97d75fe03428ae155fc7793431487f63.sol` `fill` unsafe-math — bound-lens, wrap-lens
- `BECToken.sol` `BecToken` unsafe-math — bound-lens, wrap-lens
- `blackjack.sol` `hit` unsafe-math — bound-lens, wrap-lens
- `blackjack.sol` `stand` unsafe-math — bound-lens, wrap-lens
- `crypto_roulette.sol` `shuffle` unsafe-math — bound-lens, wrap-lens
- `etheraffle.sol` `buyTickets` unsafe-math — bound-lens, wrap-lens
- `etheraffle.sol` `getRefund` unsafe-math — bound-lens, wrap-lens
- `etherpot_lotto.sol` `fallback` unsafe-math — bound-lens, wrap-lens
- `guess_the_random_number.sol` `GuessTheRandomNumberChallenge` unsafe-math — bound-lens, wrap-lens
- `lucky_doubler.sol` `join` unsafe-math — bound-lens, wrap-lens
- `odds_and_evens.sol` `andTheWinnerIs` unsafe-math — bound-lens, wrap-lens
- `parity_wallet_bug_1.sol` `confirm` reentrancy — callorder-lens, guard-lens
- `parity_wallet_bug_1.sol` `initDaylimit` unguarded-state-write — consistency-lens, modifier-lens
- `parity_wallet_bug_1.sol` `initMultiowned` unguarded-state-write — consistency-lens, modifier-lens
- `parity_wallet_bug_1.sol` `initMultiowned` unsafe-math — bound-lens, wrap-lens
- `parity_wallet_bug_2.sol` `confirm` reentrancy — callorder-lens, guard-lens
- `parity_wallet_bug_2.sol` `initMultiowned` unsafe-math — bound-lens, wrap-lens
- `rubixi.sol` `addPayout` unsafe-math — bound-lens, wrap-lens
- `smart_billions.sol` `commitDividend` unsafe-math — bound-lens, wrap-lens
- `smart_billions.sol` `disinvest` unsafe-math — bound-lens, wrap-lens
- `smart_billions.sol` `invest` unsafe-math — bound-lens, wrap-lens
- `smart_billions.sol` `pay` unsafe-math — bound-lens, wrap-lens
- `smart_billions.sol` `playSystem` unsafe-math — bound-lens, wrap-lens
- `spank_chain_payment.sol` `byzantineCloseChannel` reentrancy — callorder-lens, guard-lens

## Targets the rule missed

- `0x627fa62ccbb1c1b04ffaecd72a53e37fc0e17839.sol` `WithdrawToHolder` reentrancy — seen by no lens
- `FibonacciBalance.sol` `fallback` unguarded-state-write — seen by no lens
- `FibonacciBalance.sol` `withdraw` unguarded-state-write — seen by modifier-lens
- `arbitrary_location_write_simple.sol` `PopBonusCode` unguarded-state-write — seen by no lens
- `incorrect_constructor_name1.sol` `IamMissing` unguarded-state-write — seen by modifier-lens
- `incorrect_constructor_name2.sol` `missing` unguarded-state-write — seen by modifier-lens
- `incorrect_constructor_name3.sol` `Constructor` unguarded-state-write — seen by modifier-lens
- `insecure_transfer.sol` `transfer` unsafe-math — seen by wrap-lens
- `mapping_write.sol` `set` unguarded-state-write — seen by no lens
- `modifier_reentrancy.sol` `airDrop` reentrancy — seen by no lens
- `mycontract.sol` `sendTo` unguarded-state-write — seen by no lens
- `parity_wallet_bug_1.sol` `fallback` unguarded-state-write — seen by no lens
- `parity_wallet_bug_1.sol` `initWallet` unguarded-state-write — seen by no lens
- `parity_wallet_bug_2.sol` `initWallet` unguarded-state-write — seen by no lens
- `parity_wallet_bug_2.sol` `kill` unguarded-state-write — seen by no lens
- `phishable.sol` `withdrawAll` unguarded-state-write — seen by no lens
- `proxy.sol` `forward` unguarded-state-write — seen by no lens
- `reentrancy_bonus.sol` `getFirstWithdrawalBonus` reentrancy — seen by no lens
- `rubixi.sol` `DynamicPyramid` unguarded-state-write — seen by modifier-lens
- `simple_suicide.sol` `sudicideAnyone` unguarded-state-write — seen by no lens
- `token.sol` `transfer` unsafe-math — seen by wrap-lens
- `tokensalechallenge.sol` `buy` unsafe-math — seen by wrap-lens
- `tokensalechallenge.sol` `sell` unsafe-math — seen by wrap-lens
- `wallet_02_refund_nosub.sol` `refund` unguarded-state-write — seen by no lens
- `wallet_03_wrong_constructor.sol` `initWallet` unguarded-state-write — seen by modifier-lens
- `wallet_04_confused_sign.sol` `withdraw` unguarded-state-write — seen by modifier-lens
