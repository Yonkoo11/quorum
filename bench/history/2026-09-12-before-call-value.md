# Benchmark — the six lenses on SmartBugs-curated

Run 2026-09-12 · corpus commit `230e649` · 143 files · quorum threshold 2 · `python bench/run.py <corpus>`

Unit: a (contract, function, risk). A target is a labelled line inside a parsed function whose category maps to a risk Quorum covers. Precision counts every finding not on a target as false, including hits on files the corpus labels for some other category.

| risk | targets | any-lens found | true | precision | recall | **quorum confirmed** | true | **precision** | **recall** |
|---|---|---|---|---|---|---|---|---|---|
| reentrancy | 31 | 115 | 1 | 1% | 3% | **11** | 0 | **0%** | **0%** |
| unguarded-state-write | 19 | 146 | 6 | 4% | 32% | **2** | 1 | **50%** | **5%** |
| unsafe-math | 21 | 5 | 0 | 0% | 0% | **0** | 0 | **n/a** | **0%** |
| **all** | 71 | 266 | 7 | 3% | 10% | **13** | 1 | **8%** | **1%** |

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
| callorder-lens | 31 | 0 |
| guard-lens | 95 | 1 |
| modifier-lens | 142 | 6 |
| sender-lens | 6 | 1 |
| unchecked-lens | 0 | 0 |
| precision-lens | 5 | 0 |

Candidates held back by the rule (one lens only): 253, of which on a target: 6.

## Confirmed findings that are not on a labelled target

- `0x663e4229142a27f00bafb5d087e1e730648314c3.sol` `ClockAuction` unguarded-state-write — modifier-lens, sender-lens
- `0x89c1b3807d4c67df034fffb62f3509561218d30b.sol` `deliver` reentrancy — callorder-lens, guard-lens
- `crypto_roulette.sol` `play` reentrancy — callorder-lens, guard-lens
- `eth_tx_order_dependence_minimal.sol` `setReward` reentrancy — callorder-lens, guard-lens
- `etheraffle.sol` `buyTickets` reentrancy — callorder-lens, guard-lens
- `etheraffle.sol` `endRaffle` reentrancy — callorder-lens, guard-lens
- `lotto.sol` `sendToWinner` reentrancy — callorder-lens, guard-lens
- `smart_billions.sol` `coldStore` reentrancy — callorder-lens, guard-lens
- `smart_billions.sol` `invest` reentrancy — callorder-lens, guard-lens
- `wallet_02_refund_nosub.sol` `withdraw` reentrancy — callorder-lens, guard-lens
- `wallet_03_wrong_constructor.sol` `withdraw` reentrancy — callorder-lens, guard-lens
- `wallet_04_confused_sign.sol` `withdraw` reentrancy — callorder-lens, guard-lens

## Targets the rule missed

- `0x01f8c4e3fa3edeb29e514cba738d87ce8c091d3f.sol` `Collect` reentrancy — seen by no lens
- `0x23a91059fdc9579a9fbd0edc5f2ea0bfdb70deb4.sol` `CashOut` reentrancy — seen by no lens
- `0x4320e6f8c05b27ab4707cd1f6d5ce6f3e4b3a5a1.sol` `Collect` reentrancy — seen by no lens
- `0x4e73b32ed6c35f570686b89848e5f39f20ecc106.sol` `Collect` reentrancy — seen by no lens
- `0x561eac93c92360949ab1f1403323e6db345cbf31.sol` `Collect` reentrancy — seen by no lens
- `0x627fa62ccbb1c1b04ffaecd72a53e37fc0e17839.sol` `WithdrawToHolder` reentrancy — seen by no lens
- `0x7541b76cb60f4c60af330c208b0623b7f54bf615.sol` `Collect` reentrancy — seen by no lens
- `0x7a8721a9d64c74da899424c1b52acbf58ddc9782.sol` `CashOut` reentrancy — seen by no lens
- `0x7b368c4e805c3870b6c49a3f1f49f69af8662cf3.sol` `Collect` reentrancy — seen by no lens
- `0x8c7777c45481dba411450c228cb692ac3d550344.sol` `CashOut` reentrancy — seen by no lens
- `0x93c32845fae42c83a70e5f06214c8433665c2ab5.sol` `Collect` reentrancy — seen by no lens
- `0x941d225236464a25eb18076df7da6a91d0f95e9e.sol` `CashOut` reentrancy — seen by no lens
- `0x96edbe868531bd23a6c05e9d0c424ea64fb1b78b.sol` `Collect` reentrancy — seen by no lens
- `0xaae1f51cf3339f18b6d3f3bdc75a5facd744b0b8.sol` `Collect` reentrancy — seen by no lens
- `0xb5e1b1ee15c6fa0e48fce100125569d430f1bd12.sol` `CashOut` reentrancy — seen by no lens
- `0xb93430ce38ac4a6bb47fb1fc085ea669353fd89e.sol` `CashOut` reentrancy — seen by no lens
- `0xbaf51e761510c1a11bf48dd87c0307ac8a8c8a4f.sol` `CashOut` reentrancy — seen by no lens
- `0xbe4041d55db380c5ae9d4a9b9703f1ed4e7e3888.sol` `Collect` reentrancy — seen by no lens
- `0xcead721ef5b11f1a7b530171aab69b16c5e66b6e.sol` `Collect` reentrancy — seen by no lens
- `0xf015c35649c82f5467c9c74b7f28ee67665aad68.sol` `Collect` reentrancy — seen by no lens
- `BECToken.sol` `batchTransfer` unsafe-math — seen by no lens
- `FibonacciBalance.sol` `withdraw` unguarded-state-write — seen by no lens
- `arbitrary_location_write_simple.sol` `PopBonusCode` unguarded-state-write — seen by no lens
- `etherbank.sol` `withdrawBalance` reentrancy — seen by no lens
- `etherstore.sol` `withdrawFunds` reentrancy — seen by no lens
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
- `reentrance.sol` `withdraw` reentrancy — seen by no lens
- `reentrancy_bonus.sol` `getFirstWithdrawalBonus` reentrancy — seen by no lens
- `reentrancy_cross_function.sol` `withdrawBalance` reentrancy — seen by no lens
- `reentrancy_dao.sol` `withdrawAll` reentrancy — seen by no lens
- `reentrancy_insecure.sol` `withdrawBalance` reentrancy — seen by no lens
- `reentrancy_simple.sol` `withdrawBalance` reentrancy — seen by no lens
- `rubixi.sol` `DynamicPyramid` unguarded-state-write — seen by no lens
- `simple_dao.sol` `withdraw` reentrancy — seen by no lens
- `simple_suicide.sol` `sudicideAnyone` unguarded-state-write — seen by no lens
- `spank_chain_payment.sol` `LCOpenTimeout` reentrancy — seen by guard-lens
- `timelock.sol` `increaseLockTime` unsafe-math — seen by no lens
- `token.sol` `transfer` unsafe-math — seen by no lens
- `tokensalechallenge.sol` `buy` unsafe-math — seen by no lens
- `tokensalechallenge.sol` `sell` unsafe-math — seen by no lens
- `wallet_02_refund_nosub.sol` `refund` unguarded-state-write — seen by no lens
- `wallet_03_wrong_constructor.sol` `initWallet` unguarded-state-write — seen by modifier-lens
- `wallet_04_confused_sign.sol` `withdraw` unguarded-state-write — seen by modifier-lens
