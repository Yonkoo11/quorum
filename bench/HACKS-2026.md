# What actually took money in 2026, and how much of it Quorum reads for

Read from [`SunWeb3Sec/DeFiHackLabs`](https://github.com/SunWeb3Sec/DeFiHackLabs), which reproduces
real hacks as runnable Foundry proofs of concept. 123 of them are dated 2026, and 53 carry an
explicit root-cause note written by the person who reproduced the exploit. Those 53 were read one at
a time and classified. The other 70 were not classified and are not counted here.

Every one of the 53 calls is written down in [`labels/hacks-2026.json`](labels/hacks-2026.json) with
the category, whether it counts as a shape Quorum reads for, and one line of why. The table below is
printed from that file by [`hacks.py`](hacks.py), not typed, so the number and the labels cannot
drift apart.

This is a different question from [`MODERN.md`](MODERN.md). That file asks what share of *audit
report findings* Quorum looks for, and the answer is 5%. This file asks what share of *hacks that
actually happened* Quorum looks for. The two numbers are very different, and the difference is the
point.

## The answer

**23 of 53, about 43%, are one of the four shapes Quorum reads for.**

| category | hacks | a shape Quorum reads for |
|---|---|---|
| access-control | 13 | **13** |
| price-oracle-manipulation | 13 | 0 |
| business-logic | 9 | 0 |
| accounting-mismatch | 7 | **7** |
| arithmetic | 3 | **1** |
| key-or-admin-compromise | 3 | 0 |
| reentrancy | 2 | **2** |
| signature-or-approval | 2 | 0 |
| token-integration | 1 | 0 |
| **total** | **53** | **23** |

Four things in that table are worth saying out loud.

**Access control is the joint-largest cause of real 2026 hacks, at 13 of 53.** It is also the risk
Quorum reads with three separate lenses, and the one `consistency-lens` was added for in v0.7.0. In
audit reports this risk looks small. In hacks it does not.

**The accounting pair is not the dead weight it looked like.** `accounting-mismatch` is third here,
7 of 53, while [`ACCOUNTING.md`](ACCOUNTING.md) records that the pair has no recall number at all
because no corpus on disk labels that bug. Seven real 2026 hacks of that shape say the pair is aimed
at something real, whatever its current recall turns out to be.

**Reentrancy is nearly extinct, at 2 of 53.** It is the risk the whole field still leads with, and
the one Quorum's demo fixture uses. Two hacks in nine months. The lenses that read for it are not
wasted, but nobody should present reentrancy as the main event any more.

**Price manipulation and business logic together are 22 of 53, and Quorum reads for neither.** An
oracle trusted at spot, a fee interpreted in the wrong unit, a redemption that is not split-invariant:
these are not line-level shapes and a line reader will not find them. That is over 40% of real hacks,
permanently out of scope for this design.

## What this does not say

**It is not a recall claim, and the recall has since been measured.** "A shape Quorum reads for" is
an upper bound on what it could catch, not a claim that it would have.
[`HACKS-RECALL.md`](HACKS-RECALL.md) puts the lenses in front of the actual victim source: of these
23, nine could be scanned at all, and the two-witness rule confirmed the labelled bug in **one** of
them. It named the right function in three, with the wrong risk in two of those. So the distance
between this file's 43% and what the tool reaches is large, and it is written down rather than left
to the reader. Nobody should quote the 43% as a hit rate.

**The denominator is incidents, not dollars.** By dollars, 2026 went the other way: roughly 74% of
attributed losses came from operational failures, stolen keys, signer compromise and backend
breaches, against 26% from smart contract vulnerabilities, and compromised keys passed contract bugs
as the leading vector for the first time on record. A source reader cannot touch that 74%.

**Bitget is the clearest example.** $351.6M on 24 September, the largest exchange breach of the year,
and the preliminary cause is a supply chain compromise of a third-party tool leading to hot and warm
wallet access. There is no vulnerable function in that story. **Quorum could not have helped, and
would not have flagged anything.** That is worth stating plainly rather than leaving to inference.

**The sample is biased, in a knowable direction.** These are exploits somebody could reproduce on
chain, which selects for contract bugs and against key theft and exchange breaches. So 43% is the
share among *reproducible contract exploits*, and the honest reading of the two denominators together
is: most of the money is lost where Quorum cannot look, and among the incidents where it can look,
its four shapes cover a large minority.

**The categories overlap, and where they do the call is a judgement.** Nine of the 53 notes describe
a chain rather than one bug. Those carry an `also` list in the labels file; only the primary category
is counted. GDC is the clearest case: four bugs, including a reentrancy leg and a gate bypass, and it
is counted once, as the accounting mismatch that actually collapsed the reserve. Someone reading the
same notes could reasonably move two or three entries. That is why the per-file reasons are published
rather than the totals alone.

### The first pass said 21, and was not written down

An earlier hand pass over the same 53 notes produced 21 of 53, about 40%, with a slightly different
spread: 12 access-control, 5 accounting, 3 reentrancy, 12 business-logic. Those per-file calls were
never recorded, so nobody — including the person who made them — could check them or say where the
two passes disagree.

This pass records every call. Comparing the two tables, business logic is down three, accounting up
two, access control and price manipulation up one each, reentrancy down one. **Which individual
files moved cannot be recovered**, because the first pass never wrote its per-file calls down — that
is exactly the hole this file closes, and it would be dishonest to reconstruct the missing side of
the comparison from the totals. What can be said is that no new data arrived and no exploit was
re-read: the same 53 notes, judged again, against the rules now written at the top of the labels
file.

**The 43% supersedes the 40% only because it is the one anyone can audit.** If a reader disagrees
with a specific line, the file makes that disagreement precise instead of leaving it as a quarrel
about a percentage.

## Reproduce

```
git clone --depth 1 https://github.com/SunWeb3Sec/DeFiHackLabs /tmp/dhl
python3 bench/hacks.py                    # the table above
python3 bench/hacks.py --check /tmp/dhl   # every label resolves, nothing with a note is missing
```

The check prints `53 labelled, 53 with a note, 0 missing, 0 unlabelled`. It is what stops a label
surviving after the file it points at is renamed, and what stops a new note going unclassified.
