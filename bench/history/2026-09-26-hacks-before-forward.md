# The lenses against code that actually lost money in 2026

Every other corpus here is somebody's test suite or a set of audit findings. This one is the
deployed source of contracts that were drained in 2026, taken from the hacks in
[`HACKS-2026.md`](HACKS-2026.md) whose root-cause note names a contract whose source can still be
read, labelled with the function that note blames.

It is the least flattering measurement in this repository, and it is the one worth having.

```
python3 bench/fetch_hacks.py /tmp/hacks-2026
python  bench/run.py /tmp/hacks-2026 --labels bench/labels/hacks-recall.json
```

The prose in this file is hand-written. The second command prints the table below to stdout; it
does not overwrite this file.

## What could be measured at all

Of the 23 hacks of 2026 whose shape these lenses read for, **9 could be scanned**. The other 14
are the ceiling on anything claimed here, and none of that is fixable by writing more code:

| why it could not be scanned | hacks |
|---|---|
| the victim contract is unverified, which the proof of concept's own header says | 6 |
| no verified source served for it at all | 6 |
| the chain is not one the fetcher reads (Citrea) | 1 |
| fetched, but the note pins the bug to no single function (ReflexerGEB) | 1 |

Six of those say *unverified* in the reproducer's own notes. A source reader cannot read a
contract nobody published. That is a permanent limit on this kind of tool, not a to-do.

## The result

Run 2026-09-25 · 10 files scanned · 9 targets · quorum threshold 2

| risk | targets | any-lens found | true | precision | recall | **quorum confirmed** | true | **precision** | **recall** |
|---|---|---|---|---|---|---|---|---|---|
| reentrancy | 1 | 16 | 1 | 6% | 100% | **4** | 1 | **25%** | **100%** |
| unguarded-state-write | 5 | 32 | 2 | 6% | 40% | **3** | 0 | **0%** | **0%** |
| unsafe-math | 0 | 27 | 0 | 0% | n/a | **1** | 0 | **0%** | **n/a** |
| accounting-mismatch | 3 | 13 | 0 | 0% | 0% | **0** | 0 | **n/a** | **0%** |
| **all** | 9 | 88 | 3 | 3% | 33% | **8** | 1 | **12%** | **11%** |

**One of nine.** The two-witness rule confirmed the labelled bug in one hack: ORB, where
`ORBCore.addPoolAndSell` refunds BNB to the caller before the rest of its state work, and
callorder-lens and guard-lens both said so. Every other labelled bug was missed, and the rule also
produced seven confirmations that are not the bug, so precision is 12%.

### The part the table hides

The scoring unit is (file, function, risk), so a finding on the right function under the wrong risk
counts as a miss *and* as a false positive. That happened twice:

- `LaunchpadFactoryAuto.launch` — the bug is that `launch()` is permissionless and forwards the
  caller's calldata verbatim. Quorum confirmed `launch`, as **reentrancy**.
- `OFTSand.approveAndCall` — the bug is that the guard only checks the first word of calldata.
  Quorum confirmed `approveAndCall`, as **reentrancy**.

So **the lenses named the exact vulnerable function in 3 of 9, and got the risk right in 1 of 9.**
Somebody triaging the output would have been reading the right code in three cases. Both numbers
are published because the 3 is the one that flatters and the 1 is the one the harsh rule gives, and
quoting only the first would be the kind of claim this repository exists to refuse.

It is also not an accident that both mistakes point the same way. An external call sitting in a
function whose guard is wrong looks like reentrancy to a line reader, because the call is visible
and the missing check is not. The three access-control lenses saw `launch` and `approveAndCall`
(modifier-lens sighted both, listed under the misses) but never got a second witness for that risk,
so the rule published the reading two lenses agreed on rather than the correct one.

### Where it is blind

`accounting-mismatch` scored 0 of 3 and no lens sighted any of the three targets. All three are the
shape the pair was built for and none of them is line-local:

- `Vault4626.totalAssets` values idle non-asset WETH that `redeem` later hands out. Two functions.
- `Royal1155LDA.safeBatchTransferFrom` credits per-tier bookkeeping for zero-amount items.
- `InvestmentManagerFacet.getTotalAssetBalance` reads a raw token balance with no per-class split.

[`ACCOUNTING.md`](ACCOUNTING.md) records that the pair had no recall number because no corpus
labelled that bug. It has one now and it is 0 of 3.

## What this does and does not say

**It does not say Quorum catches 11% of hacks.** It says that on nine real 2026 hacks whose source
can be read and whose shape these lenses read for, it confirmed the labelled bug once. The nine are
a small and self-selecting sample: they are the ones somebody reproduced, whose victim published
source, and whose note pins a single function.

**It does not transfer to the 43% in [`HACKS-2026.md`](HACKS-2026.md).** That figure is how many
2026 hacks are the *shape* these lenses read for, an upper bound on what could ever be caught. This
file is what happens when the code is actually put in front of them. The gap between 43% and 11% is
the honest distance between a tool's scope and its reach.

**The corpus is not pinned the way the others are.** It is fetched live from explorers, so a
contract that stops being served changes what can be scanned. `fetch_hacks.py` prints every skip and
why, so a shrinking corpus is visible rather than silent, but this is weaker than a commit hash and
should be read that way.
