# bench

`BENCHMARK.md` is generated. Do not edit it; re-run it.

```
git clone --depth 1 https://github.com/smartbugs/smartbugs-curated /tmp/smartbugs-curated
.venv/bin/python bench/run.py /tmp/smartbugs-curated > bench/BENCHMARK.md
```

## What it measures

SmartBugs-curated labels vulnerable lines in 143 Solidity files, one category per label. Three of
its categories map onto the three risks Quorum's lens pairs cover:

| corpus category | Quorum risk |
|---|---|
| reentrancy | reentrancy |
| access_control | unguarded-state-write |
| arithmetic | unsafe-math |

The unit of comparison is the function, because that is what a Quorum finding names. Every
confirmed finding that is not on a labelled function is counted as false, including hits on files
the corpus labels for some other category. Some of those are probably real; the harsh count is
the one published.

Memory recall between contracts is switched off in the benchmark so the result does not depend on
file order. The rule itself is the swarm's own: two distinct lenses on one key.

## History, same corpus, same commit `230e649`

| run | change | overall recall | overall precision | reentrancy recall | reentrancy precision |
|---|---|---|---|---|---|
| [2026-09-12 first](history/2026-09-12-before-call-value.md) | as shipped for the hackathon | 1% | 8% | 0% | 0% |
| 2026-09-12 second | `EXTERNAL_CALL` learns the pre-0.5 idiom `.call.value(x)()`, which 29 of the 32 reentrancy files use | 23% | 43% | 48% | 43% |
| [2026-09-12 third](BENCHMARK.md) | a function with no visibility keyword counts as callable, which is what it was before 0.5 | 31% | 39% | 68% | 39% |

Both fixes were made after looking at this corpus, so the third row is a tuned number, not a
held-out one. A run on a corpus the lenses were never adjusted against is the next measurement.

## What the numbers say

- The two-witness rule is a precision filter and it costs recall. On reentrancy the lenses alone
  reach 94% recall at 14% precision; the rule gives 39% precision at 68% recall. That is the
  product's claim, now with a number on it.
- `unchecked-lens` fires zero times: the corpus predates `unchecked` blocks. `precision-lens` finds
  division-before-multiplication, which the corpus does not label. So 0% on arithmetic measures a
  mismatch of shapes, not a failed lens, and also says the pair does not cover overflow at all.
- Access control at 5% recall: the corpus's shapes are arbitrary storage writes and misnamed
  constructors. The pair looks for a missing modifier on a privileged write. Different bug.
- The largest remaining reentrancy miss is a storage alias (`var acc = Acc[msg.sender]` then
  `acc.balance -= x`): `callorder-lens` cannot see that the write touches storage.
