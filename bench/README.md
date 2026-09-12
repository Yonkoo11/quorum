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
  corpus, 71 usable targets). Two lens fixes were made after looking at this corpus, so its
  numbers are tuned.
- **DeFiVulnLabs** (57 files, modern ^0.8 Foundry tests, one bug per file). Labels were written
  by hand at function level in [`labels/defivulnlabs.json`](labels/defivulnlabs.json) before the
  lenses were run on it, and no lens has been changed after looking at it. Ten targets, so read
  its percentages as counts.

`slither.py` scores Slither 0.11.4 with the same unit and the same harsh rule, using only the
detectors that map onto the three risks (the mapping is at the top of the file). "Strict" is the
detectors Slither rates High or Medium for the risk; "loose" adds Low and Informational, the
analogue of counting any single lens.

## The numbers, 2026-09-12

| | SmartBugs-curated (71 targets) | | DeFiVulnLabs, held out (10 targets) | |
|---|---|---|---|---|
| | recall | precision | recall | precision |
| lenses, any single lens | 52% | 9% | 40% | 4% |
| **lenses, two-witness rule** | **31%** | **39%** | **30%** | **60%** |
| Slither, strict | 48% | 40% | 40% | 20% |
| Slither, loose | 49% | 23% | 40% | 7% |

Per risk, two-witness against Slither strict (recall / precision):

| risk | two-witness, SmartBugs | Slither, SmartBugs | two-witness, held out | Slither, held out |
|---|---|---|---|---|
| reentrancy | 68% / 39% | 90% / 62% | 2 of 4, 50% | 2 of 4, 40% |
| unguarded-state-write | 5% / 33% | 32% / 16% | 1 of 2, 100% | 1 of 2, 8% |
| unsafe-math | 0% | 0% | 0 of 4 | 1 of 4, 50% |

Files: [BENCHMARK.md](BENCHMARK.md), [HELDOUT.md](HELDOUT.md), [SLITHER.md](SLITHER.md),
[SLITHER-HELDOUT.md](SLITHER-HELDOUT.md).

## History of the lenses on SmartBugs-curated, corpus commit `230e649`

| run | change | overall recall | overall precision | reentrancy recall | reentrancy precision |
|---|---|---|---|---|---|
| [2026-09-12 first](history/2026-09-12-before-call-value.md) | as shipped for the hackathon | 1% | 8% | 0% | 0% |
| 2026-09-12 second | `EXTERNAL_CALL` learns the pre-0.5 idiom `.call.value(x)()`, which 29 of the 32 reentrancy files use | 23% | 43% | 48% | 43% |
| [2026-09-12 third](BENCHMARK.md) | a function with no visibility keyword counts as callable, which is what it was before 0.5 | 31% | 39% | 68% | 39% |

Both fixes were made after looking at this corpus, so the third row is a tuned number. The
held-out run above is the untuned one.

## What the numbers say

- The two-witness rule is a precision filter and it costs recall, on both corpora. SmartBugs
  reentrancy: the lenses alone reach 94% recall at 14% precision; the rule gives 39% precision at
  68% recall. Held out: any lens 4% precision, the rule 60%.
- On 2017 code Slither is the better tool, and on reentrancy it is not close: 90% / 62% against
  68% / 39%. Slither follows calls and storage; the lenses read lines.
- On the modern corpus the rule is the more precise of the two (60% against 20%) at lower recall
  (30% against 40%), on ten targets. Slither's precision there is spent on `arbitrary-send-eth`
  and `suicidal` firing inside attack contracts and test harnesses, which the harsh rule counts
  against it exactly as it counts the lenses' hits on the same files.
- Slither has no detector for a public setter with no owner check. `Visibility.sol:changeOwner`
  is the one target the lenses confirmed that Slither missed.
- Arithmetic is 0% for both tools on 2017 code: Slither has no overflow detector, and Quorum's
  `unchecked-lens` looks for `unchecked` blocks, which did not exist. On the modern corpus the
  precision-lens saw `Divmultiply.sol:price` and the rule still confirmed nothing, because the
  pair's other lens looks for a different bug. **Two lenses that look for two different bugs can
  never corroborate each other.** That is a design fault in the arithmetic pair, not bad luck, and
  it is the first thing the next lens change fixes.
- Access control at 5% on SmartBugs: the corpus's shapes are arbitrary storage writes and
  misnamed constructors. The pair looks for a missing modifier on a privileged write. Different bug.
- The largest remaining reentrancy miss on SmartBugs is a storage alias (`var acc =
  Acc[msg.sender]` then `acc.balance -= x`): `callorder-lens` cannot see that the write touches
  storage. Unnamed 0.4 fallback functions are not parsed at all, so labels on them are dropped,
  which flatters recall; that is the other pending fix.
- Quorum keys a finding by file, function and risk, not by contract. In DeFiVulnLabs a vulnerable
  contract and its remediated twin often share a file and a function name, so they share a key.
  The labels file records where that happens.
