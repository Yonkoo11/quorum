# bench

Every `.md` in this folder is generated. Do not edit them; re-run them.

```
git clone --depth 1 https://github.com/smartbugs/smartbugs-curated /tmp/smartbugs-curated
git clone --depth 1 https://github.com/SunWeb3Sec/DeFiVulnLabs /tmp/DeFiVulnLabs && git -C /tmp/DeFiVulnLabs submodule update --init --recursive --depth 1

.venv/bin/python bench/run.py /tmp/smartbugs-curated                                              > bench/BENCHMARK.md
.venv/bin/python bench/run.py /tmp/DeFiVulnLabs --labels bench/labels/defivulnlabs.json           > bench/HELDOUT.md

# the baseline needs Slither and solc-select (pip install slither-analyzer solc-select; solc-select install 0.4.26 0.4.25 0.4.24 0.4.9 0.7.6 0.8.18 0.8.35)
.venv/bin/python bench/slither.py /tmp/smartbugs-curated                                          > bench/SLITHER.md
.venv/bin/python bench/slither.py /tmp/DeFiVulnLabs --labels bench/labels/defivulnlabs.json --fallback-pragma "^0.8.18" \
    --remap forge-std/=/tmp/DeFiVulnLabs/lib/forge-std/src/ ds-test/=/tmp/DeFiVulnLabs/lib/forge-std/lib/ds-test/src/ @openzeppelin/=/tmp/DeFiVulnLabs/lib/openzeppelin-contracts/ \
                                                                                                  > bench/SLITHER-HELDOUT.md
```

## What it measures

The unit of comparison is the function, because that is what a Quorum finding names. A target is a
labelled function whose bug maps to one of the three risks Quorum's lens pairs cover:

| corpus bug | Quorum risk |
|---|---|
| reentrancy | reentrancy |
| access control | unguarded-state-write |
| arithmetic (overflow, precision) | unsafe-math |

Every finding that is not on a labelled function is counted as false, including hits on attack
contracts, test harnesses, remediated twins and files the corpus labels for some other bug. Some of
those are probably real; the harsh count is the one published. Memory recall between contracts is
switched off so the result does not depend on file order. The rule itself is the swarm's own: two
distinct lenses on one key.

Two corpora:

- **SmartBugs-curated** (143 files, 2017-era 0.4 Solidity, line-level labels shipped with the
  corpus, 73 usable targets). Five lens changes were made after looking at this corpus, so its
  numbers are tuned.
- **DeFiVulnLabs** (57 files, modern ^0.8 Foundry tests, one bug per file). Labels were written
  by hand at function level in [`labels/defivulnlabs.json`](labels/defivulnlabs.json) before the
  lenses were run on it, and no lens has been adjusted against it. The later lens changes were
  made after looking at SmartBugs and the Base production targets only; the held-out run is
  repeated after each one and every version is kept in [history/](history/). Ten targets, so read
  its percentages as counts.

`slither.py` scores Slither 0.11.4 with the same unit and the same harsh rule, using only the
detectors that map onto the three risks (the mapping is at the top of the file). "Strict" is the
detectors Slither rates High or Medium for the risk; "loose" adds Low and Informational, the
analogue of counting any single lens.

## The numbers, 2026-09-13

| | SmartBugs-curated (73 targets) | | DeFiVulnLabs, held out (10 targets) | |
|---|---|---|---|---|
| | recall | precision | recall | precision |
| lenses, any single lens | 78% | 12% | 50% | 5% |
| **lenses, two-witness rule** | **63%** | **51%** | **50%** | **62%** |
| Slither, strict | 48% | 41% | 40% | 20% |
| Slither, loose | 49% | 24% | 40% | 7% |

Per risk, two-witness against Slither strict (recall / precision):

| risk | two-witness, SmartBugs | Slither, SmartBugs | two-witness, held out | Slither, held out |
|---|---|---|---|---|
| reentrancy | 94% / 69% | 90% / 62% | 2 of 4, 67% | 2 of 4, 40% |
| unguarded-state-write | 5% / 100% | 33% / 19% | 1 of 2, 100% | 1 of 2, 8% |
| unsafe-math | 76% / 33% | 0% | 2 of 4, 50% | 1 of 4, 50% |

Files: [BENCHMARK.md](BENCHMARK.md), [HELDOUT.md](HELDOUT.md), [SLITHER.md](SLITHER.md),
[SLITHER-HELDOUT.md](SLITHER-HELDOUT.md).

## History of the lenses on SmartBugs-curated, corpus commit `230e649`

| run | change | overall recall | overall precision | reentrancy recall | reentrancy precision |
|---|---|---|---|---|---|
| [2026-09-12 first](history/2026-09-12-before-call-value.md) | as shipped for the hackathon | 1% | 8% | 0% | 0% |
| 2026-09-12 second | `EXTERNAL_CALL` learns the pre-0.5 idiom `.call.value(x)()`, which 29 of the 32 reentrancy files use | 23% | 43% | 48% | 43% |
| [2026-09-12 third](history/2026-09-12-before-fallback-and-alias.md) | a function with no visibility keyword counts as callable, which is what it was before 0.5 | 31% | 39% | 68% | 39% |
| [2026-09-12 fourth](history/2026-09-13-before-wrap-bound.md) | unnamed 0.4 fallback functions are parsed, so two labels on them become targets (71 → 73); `callorder-lens` follows a storage alias (`var acc = Acc[msg.sender]`) | 40% | 44% | 90% | 44% |
| [2026-09-13 fifth](history/2026-09-13-before-precision.md) | the arithmetic pair rebuilt as two readings of one bug: `wrap-lens` (the compiler lets it wrap) and `bound-lens` (nothing bounds the operands). The first cut scored 81% / 19% on arithmetic and confirmed WETH9's `deposit` on the production targets, so operands the chain itself bounds (`msg.value`, `block.number`, small constants) now count as bounded | 62% | 36% | 90% | 44% |
| [2026-09-13 sixth](BENCHMARK.md) | 2300-gas `transfer`/`send` no longer count as external calls (token `transfer(to, amt)` still does); comments stripped before brace matching; evidence lines counted from the brace; `constant` is read-only; 0.4 constructors skipped by the access pair; `delete` is a state write; chain-bounded operands matched as dotted names and `==` accepted as a bound. False positives 81 → 45, true positives 45 → 46 | 63% | 51% | 94% | 69% |

All six changes were made after looking at this corpus, so every row after the first is a tuned
number. The held-out run above is the untuned one. It did not move for the third and fourth
changes; the fifth moved it from 30% / 60% to 40% / 44%, because the old arithmetic pair
could not confirm anything there and the new one confirms four; the sixth moved it to 50% / 62%
(one more true positive, two fewer false).

## What the numbers say

- The two-witness rule is a precision filter and it costs recall, on both corpora. SmartBugs
  reentrancy: the lenses alone reach 94% recall at 27% precision; the rule gives 69% precision at
  the same 94% recall. Arithmetic: 95% at 12% alone, 76% at 33% with the rule. Held out: any lens
  5% precision, the rule 62%.
- The sixth run changed the comparison with Slither. Until then Slither was more precise on
  reentrancy (62% against 44%); the difference was one rule Slither has always applied, that a
  2300-gas `transfer`/`send` cannot re-enter. With the same rule the two-witness pair finds 29 of
  31 at 69% against Slither's 28 at 62%. Slither still finds far more access-control bugs on this
  corpus (33% against 5%) and follows calls and storage, which the lenses do not: a call inside a
  modifier, a write reached through an internal call, and a guard in the caller are all invisible
  to them.
- On the modern corpus the rule is the more precise of the two (62% against 20%) at higher recall
  (5 of 10 against 4), on ten targets. Slither's precision there is spent on `arbitrary-send-eth`
  and `suicidal` firing inside attack contracts and test harnesses, which the harsh rule counts
  against it exactly as it counts the lenses' hits on the same files.
- Slither has no detector for a public setter with no owner check. `Visibility.sol:changeOwner`
  is the one target the lenses confirmed that Slither missed.
- The first arithmetic pair was one lens for `unchecked` blocks and one for division before
  multiplication: two different bugs, so the two could never corroborate each other, and the pair
  scored 0% on both corpora. **A pair must be two readings of one bug.** The rebuilt pair reads
  storage arithmetic that can wrap from the compiler's side (`wrap-lens`: a pre-0.8 pragma or an
  `unchecked` block) and from the code's side (`bound-lens`: no `require`, `assert` or `if` with a
  comparison on the operands before the write). Checked arithmetic with no guard is a candidate;
  unchecked arithmetic behind a guard is a candidate; only both together confirm. 76% recall at
  33% precision on 2017 code, where Slither has no overflow detector at all. Division before
  multiplication is no longer covered by any lens; `Divmultiply.sol` and `Precision-loss.sol` are
  now honest misses.
- What the arithmetic pair still misses: `BECToken.sol:batchTransfer` computes `cnt * _value`
  into a local before the SafeMath call; `token.sol:transfer` is guarded by a check that is itself
  wrong (`balances[msg.sender] - _value >= 0` is always true on unsigned); `Overflow2.sol:_transfer`
  is guarded in the caller, not in the function. Of the 32 arithmetic false positives left, most are a local temporary or a value
  derived one step from a bounded one; following that one step is the next lens change.
- Access control at 5% on SmartBugs: the corpus's shapes are arbitrary storage writes and
  misnamed constructors. The pair looks for a missing modifier on a privileged write. Different bug.
- The fourth run fixed the two things the third exposed. Unnamed 0.4 fallback functions are
  parsed now, so the two labels on them count as targets (both access control, both still
  missed). The storage alias `var acc = Acc[msg.sender]; acc.balance -= x` is followed by
  `callorder-lens`, which is where the reentrancy recall came from: 21 → 28 true on the same 63
  confirmed.
- Quorum keys a finding by file, function and risk, not by contract. In DeFiVulnLabs a vulnerable
  contract and its remediated twin often share a file and a function name, so they share a key.
  The labels file records where that happens.
