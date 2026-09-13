# Benchmark — the six lenses on SmartBugs-curated

Run 2026-09-13 · corpus commit `230e649` · 143 files scanned · 73 targets · quorum threshold 2 · `python bench/run.py <corpus>`

Unit: a (file, function, risk). A target is a labelled function whose bug maps to a risk Quorum covers. Precision counts every finding not on a target as false, including hits on files the corpus labels for some other bug.

| risk | targets | any-lens found | true | precision | recall | **quorum confirmed** | true | **precision** | **recall** |
|---|---|---|---|---|---|---|---|---|---|
| reentrancy | 31 | 205 | 29 | 14% | 94% | **63** | 28 | **44%** | **90%** |
| unguarded-state-write | 21 | 210 | 8 | 4% | 38% | **3** | 1 | **33%** | **5%** |
| unsafe-math | 21 | 176 | 20 | 11% | 95% | **60** | 16 | **27%** | **76%** |
| **all** | 73 | 591 | 57 | 10% | 78% | **126** | 45 | **36%** | **62%** |

## Per lens

| lens | sightings | on a target |
|---|---|---|
| callorder-lens | 74 | 28 |
| guard-lens | 194 | 29 |
| modifier-lens | 203 | 8 |
| sender-lens | 10 | 1 |
| wrap-lens | 176 | 20 |
| bound-lens | 60 | 16 |

Candidates held back by the rule (one lens only): 465, of which on a target: 12.

## Confirmed findings that are not on a labelled target

- `0x07f7ecb66d788ab01dc93b9b71a88401de7d0f2e.sol` `donateToWhale` unsafe-math — bound-lens, wrap-lens
- `0x07f7ecb66d788ab01dc93b9b71a88401de7d0f2e.sol` `loseWager` unsafe-math — bound-lens, wrap-lens
- `0x19cf8481ea15427a98ba3cdd6d9e14690011ab10.sol` `createDaoPOLSKAtokens` unsafe-math — bound-lens, wrap-lens
- `0x19cf8481ea15427a98ba3cdd6d9e14690011ab10.sol` `refundTRA` unsafe-math — bound-lens, wrap-lens
- `0x19cf8481ea15427a98ba3cdd6d9e14690011ab10.sol` `setBonusCreationRate` unsafe-math — bound-lens, wrap-lens
- `0x19cf8481ea15427a98ba3cdd6d9e14690011ab10.sol` `transfer` reentrancy — callorder-lens, guard-lens
- `0x19cf8481ea15427a98ba3cdd6d9e14690011ab10.sol` `transfer` unsafe-math — bound-lens, wrap-lens
- `0x19cf8481ea15427a98ba3cdd6d9e14690011ab10.sol` `transferFrom` reentrancy — callorder-lens, guard-lens
- `0x19cf8481ea15427a98ba3cdd6d9e14690011ab10.sol` `transferFrom` unsafe-math — bound-lens, wrap-lens
- `0x39cfd754c85023648bf003bea2dd498c5612abfa.sol` `WithdrawToHolder` reentrancy — callorder-lens, guard-lens
- `0x3a0e9acd953ffc0dd18d63603488846a6b8b2b01.sol` `WithdrawToHolder` reentrancy — callorder-lens, guard-lens
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `ClockAuction` unguarded-state-write — modifier-lens, sender-lens
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `_triggerCooldown` unsafe-math — bound-lens, wrap-lens
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `withdrawBalance` unsafe-math — bound-lens, wrap-lens
- `0x7d09edb07d23acb532a82be3da5c17d9d85806b4.sol` `donateToWhale` unsafe-math — bound-lens, wrap-lens
- `0x7d09edb07d23acb532a82be3da5c17d9d85806b4.sol` `loseWager` unsafe-math — bound-lens, wrap-lens
- `0x89c1b3807d4c67df034fffb62f3509561218d30b.sol` `cancel` reentrancy — callorder-lens, guard-lens
- `0x89c1b3807d4c67df034fffb62f3509561218d30b.sol` `deliver` reentrancy — callorder-lens, guard-lens
- `0x89c1b3807d4c67df034fffb62f3509561218d30b.sol` `deliver` unsafe-math — bound-lens, wrap-lens
- `0x89c1b3807d4c67df034fffb62f3509561218d30b.sol` `request` reentrancy — callorder-lens, guard-lens
- `0x89c1b3807d4c67df034fffb62f3509561218d30b.sol` `reset` unsafe-math — bound-lens, wrap-lens
- `0x8fd1e427396ddb511533cf9abdbebd0a7e08da35.sol` `WithdrawToHolder` reentrancy — callorder-lens, guard-lens
- `0x958a8f594101d2c0485a52319f29b2647f2ebc06.sol` `Marriage` unguarded-state-write — modifier-lens, sender-lens
- `0xb7c5c5aa4d42967efe906e1b66cb8df9cebf04f7.sol` `withdraw` reentrancy — callorder-lens, guard-lens
- `0xe09b1ab8111c2729a76f16de96bc86a7af837928.sol` `play` unsafe-math — bound-lens, wrap-lens
- `0xe09b1ab8111c2729a76f16de96bc86a7af837928.sol` `sendRefund` unsafe-math — bound-lens, wrap-lens
- `0xe09b1ab8111c2729a76f16de96bc86a7af837928.sol` `wager` reentrancy — callorder-lens, guard-lens
- `0xe09b1ab8111c2729a76f16de96bc86a7af837928.sol` `wager` unsafe-math — bound-lens, wrap-lens
- `0xec329ffc97d75fe03428ae155fc7793431487f63.sol` `fill` unsafe-math — bound-lens, wrap-lens
- `0xec329ffc97d75fe03428ae155fc7793431487f63.sol` `run` reentrancy — callorder-lens, guard-lens
- `BECToken.sol` `BecToken` unsafe-math — bound-lens, wrap-lens
- `auction.sol` `bid` reentrancy — callorder-lens, guard-lens
- `blackjack.sol` `hit` unsafe-math — bound-lens, wrap-lens
- `blackjack.sol` `stand` unsafe-math — bound-lens, wrap-lens
- `crypto_roulette.sol` `play` reentrancy — callorder-lens, guard-lens
- `crypto_roulette.sol` `shuffle` unsafe-math — bound-lens, wrap-lens
- `eth_tx_order_dependence_minimal.sol` `claimReward` reentrancy — callorder-lens, guard-lens
- `eth_tx_order_dependence_minimal.sol` `setReward` reentrancy — callorder-lens, guard-lens
- `ether_lotto.sol` `play` reentrancy — callorder-lens, guard-lens
- `etheraffle.sol` `buyTickets` reentrancy — callorder-lens, guard-lens
- `etheraffle.sol` `buyTickets` unsafe-math — bound-lens, wrap-lens
- `etheraffle.sol` `endRaffle` reentrancy — callorder-lens, guard-lens
- `etheraffle.sol` `getRefund` unsafe-math — bound-lens, wrap-lens
- `etherpot_lotto.sol` `calculateWinner` unsafe-math — bound-lens, wrap-lens
- `etherpot_lotto.sol` `cash` reentrancy — callorder-lens, guard-lens
- `etherpot_lotto.sol` `fallback` reentrancy — callorder-lens, guard-lens
- `etherpot_lotto.sol` `fallback` unsafe-math — bound-lens, wrap-lens
- `governmental_survey.sol` `resetInvestment` reentrancy — callorder-lens, guard-lens
- `guess_the_random_number.sol` `GuessTheRandomNumberChallenge` unsafe-math — bound-lens, wrap-lens
- `king_of_the_ether_throne.sol` `claimThrone` reentrancy — callorder-lens, guard-lens
- `list_dos.sol` `lendGovernmentMoney` reentrancy — callorder-lens, guard-lens
- `lotto.sol` `sendToWinner` reentrancy — callorder-lens, guard-lens
- `lucky_doubler.sol` `join` unsafe-math — bound-lens, wrap-lens
- `lucky_doubler.sol` `rand` unsafe-math — bound-lens, wrap-lens
- `odds_and_evens.sol` `andTheWinnerIs` unsafe-math — bound-lens, wrap-lens
- `parity_wallet_bug_1.sol` `execute` reentrancy — callorder-lens, guard-lens
- `parity_wallet_bug_1.sol` `initMultiowned` unsafe-math — bound-lens, wrap-lens
- `parity_wallet_bug_2.sol` `execute` reentrancy — callorder-lens, guard-lens
- `parity_wallet_bug_2.sol` `initMultiowned` unsafe-math — bound-lens, wrap-lens
- `rubixi.sol` `addPayout` unsafe-math — bound-lens, wrap-lens
- `rubixi.sol` `collectAllFees` reentrancy — callorder-lens, guard-lens
- `rubixi.sol` `collectFeesInEther` reentrancy — callorder-lens, guard-lens
- `rubixi.sol` `collectPercentOfFees` reentrancy — callorder-lens, guard-lens
- `rubixi.sol` `numberOfParticipantsWaitingForPayout` unsafe-math — bound-lens, wrap-lens
- `smart_billions.sol` `coldStore` reentrancy — callorder-lens, guard-lens
- `smart_billions.sol` `commitDividend` unsafe-math — bound-lens, wrap-lens
- `smart_billions.sol` `disinvest` unsafe-math — bound-lens, wrap-lens
- `smart_billions.sol` `dividendsBlocks` unsafe-math — bound-lens, wrap-lens
- `smart_billions.sol` `getHash` unsafe-math — bound-lens, wrap-lens
- `smart_billions.sol` `invest` reentrancy — callorder-lens, guard-lens
- `smart_billions.sol` `invest` unsafe-math — bound-lens, wrap-lens
- `smart_billions.sol` `pay` unsafe-math — bound-lens, wrap-lens
- `smart_billions.sol` `playSystem` unsafe-math — bound-lens, wrap-lens
- `spank_chain_payment.sol` `byzantineCloseChannel` reentrancy — callorder-lens, guard-lens
- `spank_chain_payment.sol` `createChannel` unsafe-math — bound-lens, wrap-lens
- `spank_chain_payment.sol` `deposit` unsafe-math — bound-lens, wrap-lens
- `spank_chain_payment.sol` `joinChannel` unsafe-math — bound-lens, wrap-lens
- `timelock.sol` `deposit` unsafe-math — bound-lens, wrap-lens
- `wallet_02_refund_nosub.sol` `withdraw` reentrancy — callorder-lens, guard-lens
- `wallet_03_wrong_constructor.sol` `withdraw` reentrancy — callorder-lens, guard-lens
- `wallet_04_confused_sign.sol` `withdraw` reentrancy — callorder-lens, guard-lens

## Targets the rule missed

- `BECToken.sol` `batchTransfer` unsafe-math — seen by no lens
- `FibonacciBalance.sol` `fallback` unguarded-state-write — seen by no lens
- `FibonacciBalance.sol` `withdraw` unguarded-state-write — seen by modifier-lens
- `arbitrary_location_write_simple.sol` `PopBonusCode` unguarded-state-write — seen by no lens
- `incorrect_constructor_name1.sol` `IamMissing` unguarded-state-write — seen by modifier-lens
- `incorrect_constructor_name2.sol` `missing` unguarded-state-write — seen by modifier-lens
- `incorrect_constructor_name3.sol` `Constructor` unguarded-state-write — seen by modifier-lens
- `insecure_transfer.sol` `transfer` unsafe-math — seen by wrap-lens
- `integer_overflow_1.sol` `add` unsafe-math — seen by wrap-lens
- `mapping_write.sol` `set` unguarded-state-write — seen by no lens
- `modifier_reentrancy.sol` `airDrop` reentrancy — seen by no lens
- `multiowned_vulnerable.sol` `newOwner` unguarded-state-write — seen by no lens
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
- `spank_chain_payment.sol` `LCOpenTimeout` reentrancy — seen by guard-lens
- `token.sol` `transfer` unsafe-math — seen by wrap-lens
- `tokensalechallenge.sol` `sell` unsafe-math — seen by wrap-lens
- `wallet_02_refund_nosub.sol` `refund` unguarded-state-write — seen by no lens
- `wallet_03_wrong_constructor.sol` `initWallet` unguarded-state-write — seen by modifier-lens
- `wallet_04_confused_sign.sol` `withdraw` unguarded-state-write — seen by modifier-lens
