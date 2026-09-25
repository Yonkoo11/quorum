# What actually took money in 2026, and how much of it Quorum reads for

Read by hand 2026-09-25 from [`SunWeb3Sec/DeFiHackLabs`](https://github.com/SunWeb3Sec/DeFiHackLabs),
which reproduces real hacks as runnable Foundry proofs of concept. 123 of them are dated 2026, and 53
carry an explicit root-cause note written by the person who reproduced the exploit. Those 53 were
read one at a time and classified. The other 70 were not classified and are not counted here.

This is a different question from [`MODERN.md`](MODERN.md). That file asks what share of *audit
report findings* Quorum looks for, and the answer is 5%. This file asks what share of *hacks that
actually happened* Quorum looks for. The two numbers are very different, and the difference is the
point.

## The answer

**21 of 53, about 40%, are one of the four shapes Quorum reads for.**

| category | hacks | a shape Quorum reads for |
|---|---|---|
| access-control | 12 | **12** |
| business-logic | 12 | 0 |
| price-oracle-manipulation | 12 | 0 |
| accounting-mismatch | 5 | **5** |
| key-or-admin-compromise | 3 | 0 |
| reentrancy | 3 | **3** |
| arithmetic | 3 | **1** |
| signature-or-approval | 2 | 0 |
| token-integration | 1 | 0 |
| **total** | **53** | **21** |

Three things in that table are worth saying out loud.

**Access control is the joint-largest cause of real 2026 hacks, at 12 of 53.** It is also the risk
Quorum reads with three separate lenses, and the one `consistency-lens` was added for in v0.7.0. In
audit reports this risk looks small. In hacks it does not.

**The accounting pair is not the dead weight it looked like last night.** `accounting-mismatch` is
the fourth-largest category here, 5 of 53, while [`ACCOUNTING.md`](ACCOUNTING.md) records that the
pair has no recall number at all because no corpus on disk labels that bug. Five real 2026 hacks of
that shape say the pair is aimed at something real, whatever its current recall turns out to be.

**Price manipulation and business logic together are 24 of 53, and Quorum reads for neither.** An
oracle trusted at spot, a fee interpreted in the wrong unit, a redemption that is not split-invariant:
these are not line-level shapes and a line reader will not find them. That is close to half of all
real hacks, permanently out of scope for this design.

## What this does not say

**It is not a recall claim.** "A shape Quorum reads for" is an upper bound on what it could catch,
not a claim that it would have. On recent audit contests Quorum confirms 29% of the targets in the
shapes it does read for, so the realistic figure is a fraction of the 40%, not the 40%. Nobody should
quote this as a hit rate.

**The denominator is incidents, not dollars.** By dollars, 2026 went the other way: roughly 74% of
attributed losses came from operational failures, stolen keys, signer compromise and backend
breaches, against 26% from smart contract vulnerabilities, and compromised keys passed contract bugs
as the leading vector for the first time on record. A source reader cannot touch that 74%.

**Bitget is the clearest example.** $351.6M on 24 September, the largest exchange breach of the year,
and the preliminary cause is a supply chain compromise of a third-party tool leading to hot and warm
wallet access. There is no vulnerable function in that story. **Quorum could not have helped, and
would not have flagged anything.** That is worth stating plainly rather than leaving to inference.

**The sample is biased, in a knowable direction.** These are exploits somebody could reproduce on
chain, which selects for contract bugs and against key theft and exchange breaches. So 40% is the
share among *reproducible contract exploits*, and the honest reading of the two denominators together
is: most of the money is lost where Quorum cannot look, and among the incidents where it can look,
its four shapes cover a large minority.

## Reproduce

```
git clone --depth 1 https://github.com/SunWeb3Sec/DeFiHackLabs /tmp/dhl
grep -rli "root cause" /tmp/dhl/src/test/2026-* --include="*.sol"   # the 53 read here
```

Each file's header names the protocol, the loss, the exploit transaction and the author's root-cause
note. The classification above is a judgement on those notes; where a note did not settle the cause,
the entry was left out rather than guessed.
