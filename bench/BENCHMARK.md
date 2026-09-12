# Benchmark — the six lenses on SmartBugs-curated

Run 2026-09-12 · corpus commit `230e649` · 143 files · quorum threshold 2 · `python bench/run.py <corpus>`

Unit: a (contract, function, risk). A target is a labelled line inside a parsed function whose category maps to a risk Quorum covers. Precision counts every finding not on a target as false, including hits on files the corpus labels for some other category.

| risk | targets | any-lens found | true | precision | recall | **quorum confirmed** | true | **precision** | **recall** |
|---|---|---|---|---|---|---|---|---|---|
| reentrancy | 31 | 200 | 29 | 14% | 94% | **54** | 21 | **39%** | **68%** |
| unguarded-state-write | 19 | 206 | 8 | 4% | 42% | **3** | 1 | **33%** | **5%** |
| unsafe-math | 21 | 5 | 0 | 0% | 0% | **0** | 0 | **n/a** | **0%** |
| **all** | 71 | 411 | 37 | 9% | 52% | **57** | 22 | **39%** | **31%** |

## Labels the benchmark could not use

| risk | labels | outside any parsed function |
|---|---|---|
| reentrancy | 32 | 0 |
| unguarded-state-write | 24 | 2 |
| unsafe-math | 23 | 0 |

Unnamed 0.4-era fallback functions (`function () payable`) are not parsed by `FUNC`, so a label on one of them has no function to attach to and is dropped from the targets. That flatters recall.

## Per lens

| lens | sightings | on a target |
|---|---|---|
| callorder-lens | 65 | 21 |
| guard-lens | 189 | 29 |
| modifier-lens | 199 | 8 |
| sender-lens | 10 | 1 |
| unchecked-lens | 0 | 0 |
| precision-lens | 5 | 0 |

Candidates held back by the rule (one lens only): 354, of which on a target: 15.

## Confirmed findings that are not on a labelled target

- `0x19cf8481ea15427a98ba3cdd6d9e14690011ab10.sol` `transfer` reentrancy — callorder-lens, guard-lens
- `0x19cf8481ea15427a98ba3cdd6d9e14690011ab10.sol` `transferFrom` reentrancy — callorder-lens, guard-lens
- `0x39cfd754c85023648bf003bea2dd498c5612abfa.sol` `WithdrawToHolder` reentrancy — callorder-lens, guard-lens
- `0x3a0e9acd953ffc0dd18d63603488846a6b8b2b01.sol` `WithdrawToHolder` reentrancy — callorder-lens, guard-lens
- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `ClockAuction` unguarded-state-write — modifier-lens, sender-lens
- `0x89c1b3807d4c67df034fffb62f3509561218d30b.sol` `cancel` reentrancy — callorder-lens, guard-lens
- `0x89c1b3807d4c67df034fffb62f3509561218d30b.sol` `deliver` reentrancy — callorder-lens, guard-lens
- `0x89c1b3807d4c67df034fffb62f3509561218d30b.sol` `request` reentrancy — callorder-lens, guard-lens
- `0x8fd1e427396ddb511533cf9abdbebd0a7e08da35.sol` `WithdrawToHolder` reentrancy — callorder-lens, guard-lens
- `0x958a8f594101d2c0485a52319f29b2647f2ebc06.sol` `Marriage` unguarded-state-write — modifier-lens, sender-lens
- `0xb7c5c5aa4d42967efe906e1b66cb8df9cebf04f7.sol` `withdraw` reentrancy — callorder-lens, guard-lens
- `0xe09b1ab8111c2729a76f16de96bc86a7af837928.sol` `wager` reentrancy — callorder-lens, guard-lens
- `0xec329ffc97d75fe03428ae155fc7793431487f63.sol` `run` reentrancy — callorder-lens, guard-lens
- `auction.sol` `bid` reentrancy — callorder-lens, guard-lens
- `crypto_roulette.sol` `play` reentrancy — callorder-lens, guard-lens
- `eth_tx_order_dependence_minimal.sol` `claimReward` reentrancy — callorder-lens, guard-lens
- `eth_tx_order_dependence_minimal.sol` `setReward` reentrancy — callorder-lens, guard-lens
- `ether_lotto.sol` `play` reentrancy — callorder-lens, guard-lens
- `etheraffle.sol` `buyTickets` reentrancy — callorder-lens, guard-lens
- `etheraffle.sol` `endRaffle` reentrancy — callorder-lens, guard-lens
- `etherpot_lotto.sol` `cash` reentrancy — callorder-lens, guard-lens
- `governmental_survey.sol` `resetInvestment` reentrancy — callorder-lens, guard-lens
- `king_of_the_ether_throne.sol` `claimThrone` reentrancy — callorder-lens, guard-lens
- `list_dos.sol` `lendGovernmentMoney` reentrancy — callorder-lens, guard-lens
- `lotto.sol` `sendToWinner` reentrancy — callorder-lens, guard-lens
- `parity_wallet_bug_1.sol` `execute` reentrancy — callorder-lens, guard-lens
- `parity_wallet_bug_2.sol` `execute` reentrancy — callorder-lens, guard-lens
- `rubixi.sol` `collectAllFees` reentrancy — callorder-lens, guard-lens
- `rubixi.sol` `collectFeesInEther` reentrancy — callorder-lens, guard-lens
- `rubixi.sol` `collectPercentOfFees` reentrancy — callorder-lens, guard-lens
- `smart_billions.sol` `coldStore` reentrancy — callorder-lens, guard-lens
- `smart_billions.sol` `invest` reentrancy — callorder-lens, guard-lens
- `wallet_02_refund_nosub.sol` `withdraw` reentrancy — callorder-lens, guard-lens
- `wallet_03_wrong_constructor.sol` `withdraw` reentrancy — callorder-lens, guard-lens
- `wallet_04_confused_sign.sol` `withdraw` reentrancy — callorder-lens, guard-lens

## Targets the rule missed

- `0x7541b76cb60f4c60af330c208b0623b7f54bf615.sol` `Collect` reentrancy — seen by guard-lens
- `0x7b368c4e805c3870b6c49a3f1f49f69af8662cf3.sol` `Collect` reentrancy — seen by guard-lens
- `0x93c32845fae42c83a70e5f06214c8433665c2ab5.sol` `Collect` reentrancy — seen by guard-lens
- `0x96edbe868531bd23a6c05e9d0c424ea64fb1b78b.sol` `Collect` reentrancy — seen by guard-lens
- `0xbe4041d55db380c5ae9d4a9b9703f1ed4e7e3888.sol` `Collect` reentrancy — seen by guard-lens
- `0xcead721ef5b11f1a7b530171aab69b16c5e66b6e.sol` `Collect` reentrancy — seen by guard-lens
- `0xf015c35649c82f5467c9c74b7f28ee67665aad68.sol` `Collect` reentrancy — seen by guard-lens
- `BECToken.sol` `batchTransfer` unsafe-math — seen by no lens
- `FibonacciBalance.sol` `withdraw` unguarded-state-write — seen by modifier-lens
- `arbitrary_location_write_simple.sol` `PopBonusCode` unguarded-state-write — seen by no lens
- `incorrect_constructor_name1.sol` `IamMissing` unguarded-state-write — seen by modifier-lens
- `incorrect_constructor_name2.sol` `missing` unguarded-state-write — seen by modifier-lens
- `incorrect_constructor_name3.sol` `Constructor` unguarded-state-write — seen by modifier-lens
- `insecure_transfer.sol` `transfer` unsafe-math — seen by no lens
- `integer_overflow_1.sol` `add` unsafe-math — seen by no lens
- `integer_overflow_add.sol` `run` unsafe-math — seen by no lens
- `integer_overflow_benign_1.sol` `run` unsafe-math — seen by no lens
- `integer_overflow_mapping_sym_1.sol` `init` unsafe-math — seen by no lens
- `integer_overflow_minimal.sol` `run` unsafe-math — seen by no lens
- `integer_overflow_mul.sol` `run` unsafe-math — seen by no lens
- `integer_overflow_multitx_multifunc_feasible.sol` `run` unsafe-math — seen by no lens
- `integer_overflow_multitx_onefunc_feasible.sol` `run` unsafe-math — seen by no lens
- `mapping_write.sol` `set` unguarded-state-write — seen by no lens
- `modifier_reentrancy.sol` `airDrop` reentrancy — seen by no lens
- `multiowned_vulnerable.sol` `newOwner` unguarded-state-write — seen by no lens
- `mycontract.sol` `sendTo` unguarded-state-write — seen by no lens
- `overflow_simple_add.sol` `add` unsafe-math — seen by no lens
- `overflow_single_tx.sol` `overflowaddtostate` unsafe-math — seen by no lens
- `overflow_single_tx.sol` `overflowlocalonly` unsafe-math — seen by no lens
- `overflow_single_tx.sol` `overflowmulocalonly` unsafe-math — seen by no lens
- `overflow_single_tx.sol` `overflowmultostate` unsafe-math — seen by no lens
- `overflow_single_tx.sol` `underflowlocalonly` unsafe-math — seen by no lens
- `overflow_single_tx.sol` `underflowtostate` unsafe-math — seen by no lens
- `parity_wallet_bug_1.sol` `initWallet` unguarded-state-write — seen by no lens
- `parity_wallet_bug_2.sol` `initWallet` unguarded-state-write — seen by no lens
- `parity_wallet_bug_2.sol` `kill` unguarded-state-write — seen by no lens
- `phishable.sol` `withdrawAll` unguarded-state-write — seen by no lens
- `proxy.sol` `forward` unguarded-state-write — seen by no lens
- `reentrancy_bonus.sol` `getFirstWithdrawalBonus` reentrancy — seen by no lens
- `rubixi.sol` `DynamicPyramid` unguarded-state-write — seen by modifier-lens
- `simple_suicide.sol` `sudicideAnyone` unguarded-state-write — seen by no lens
- `spank_chain_payment.sol` `LCOpenTimeout` reentrancy — seen by guard-lens
- `timelock.sol` `increaseLockTime` unsafe-math — seen by no lens
- `token.sol` `transfer` unsafe-math — seen by no lens
- `tokensalechallenge.sol` `buy` unsafe-math — seen by no lens
- `tokensalechallenge.sol` `sell` unsafe-math — seen by no lens
- `wallet_02_refund_nosub.sol` `refund` unguarded-state-write — seen by no lens
- `wallet_03_wrong_constructor.sol` `initWallet` unguarded-state-write — seen by modifier-lens
- `wallet_04_confused_sign.sol` `withdraw` unguarded-state-write — seen by modifier-lens
