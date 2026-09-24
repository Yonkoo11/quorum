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

# the recent-contest corpus: sixteen Code4rena repos, each pinned to a commit in the label file
.venv/bin/python bench/fetch_modern.py /tmp/modern
.venv/bin/python bench/modern.py /tmp/modern --labels bench/labels/modern-c4.json                 > bench/MODERN.md
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

## The numbers, 2026-09-16

A third corpus, [MODERN.md](MODERN.md), asks a different question: of everything recent audits actually
report, how much is this tool even looking for. The answer is 5%, and of the seven findings in its four
shapes it confirmed none. Read that file before the two tables below, because they are scored on corpora
built from the bugs these lenses were written for.

| | SmartBugs-curated (73 targets) | | DeFiVulnLabs, held out (10 targets) | |
|---|---|---|---|---|
| | recall | precision | recall | precision |
| lenses, any single lens | 79% | 11% | 50% | 4% |
| **lenses, two-witness rule** | **64%** | **52%** | **50%** | **71%** |
| Slither, strict | 48% | 41% | 40% | 20% |
| Slither, loose | 49% | 24% | 40% | 7% |

Per risk, two-witness against Slither strict (recall / precision):

| risk | two-witness, SmartBugs | Slither, SmartBugs | two-witness, held out | Slither, held out |
|---|---|---|---|---|
| reentrancy | 90% / 72% | 90% / 62% | 2 of 4, 67% | 2 of 4, 40% |
| unguarded-state-write | 10% / 40% | 33% / 19% | 1 of 2, 100% | 1 of 2, 8% |
| unsafe-math | 81% / 40% | 0% | 2 of 4, 50% | 1 of 4, 50% |
| accounting-mismatch | no labels; 4 confirmed, all counted false | no detector for this shape | no labels; 0 confirmed | no detector for this shape |

Files: [BENCHMARK.md](BENCHMARK.md), [HELDOUT.md](HELDOUT.md), [SLITHER.md](SLITHER.md),
[SLITHER-HELDOUT.md](SLITHER-HELDOUT.md), [ACCOUNTING.md](ACCOUNTING.md) (the fourth pair, measured before it was posted), [MULTICHAIN.md](MULTICHAIN.md).

## History of the lenses on SmartBugs-curated, corpus commit `230e649`

| run | change | overall recall | overall precision | reentrancy recall | reentrancy precision |
|---|---|---|---|---|---|
| [2026-09-12 first](history/2026-09-12-before-call-value.md) | as shipped for the hackathon | 1% | 8% | 0% | 0% |
| 2026-09-12 second | `EXTERNAL_CALL` learns the pre-0.5 idiom `.call.value(x)()`, which 29 of the 32 reentrancy files use | 23% | 43% | 48% | 43% |
| [2026-09-12 third](history/2026-09-12-before-fallback-and-alias.md) | a function with no visibility keyword counts as callable, which is what it was before 0.5 | 31% | 39% | 68% | 39% |
| [2026-09-12 fourth](history/2026-09-13-before-wrap-bound.md) | unnamed 0.4 fallback functions are parsed, so two labels on them become targets (71 → 73); `callorder-lens` follows a storage alias (`var acc = Acc[msg.sender]`) | 40% | 44% | 90% | 44% |
| [2026-09-13 fifth](history/2026-09-13-before-precision.md) | the arithmetic pair rebuilt as two readings of one bug: `wrap-lens` (the compiler lets it wrap) and `bound-lens` (nothing bounds the operands). The first cut scored 81% / 19% on arithmetic and confirmed WETH9's `deposit` on the production targets, so operands the chain itself bounds (`msg.value`, `block.number`, small constants) now count as bounded | 62% | 36% | 90% | 44% |
| [2026-09-13 sixth](history/2026-09-16-before-accounting.md) | 2300-gas `transfer`/`send` no longer count as external calls (token `transfer(to, amt)` still does); comments stripped before brace matching; evidence lines counted from the brace; `constant` is read-only; 0.4 constructors skipped by the access pair; `delete` is a state write; chain-bounded operands matched as dotted names and `==` accepted as a bound. False positives 81 → 45, true positives 45 → 46 | 63% | 51% | 94% | 69% |
| [2026-09-16 seventh](history/2026-09-18-before-robinhood-fixes.md) | the accounting pair: `ledger-lens` (a balance with no way down anywhere in the contract) and `payout-lens` (value leaves against a balance this function never reduces). Names that count rather than hold (…Id, …Count, …Index, …Nonce) are not ledgers; that rule came after reading the first cut's seven confirmations here (three were an id or a count), so it is tuned. Four confirmations, all on functions the corpus labels for other bugs, all counted false | 63% | 48% | 94% | 69% |
| [2026-09-18 eighth](history/2026-09-19-before-modern.md) | after the Robinhood Chain run ([ROBINHOOD.md](ROBINHOOD.md), 281 confirmations read by hand, 3 true): functions only the owner can call are not reentrancy targets; the reentrancy pair reads one level into the private helpers a function calls; a write anywhere on a line (`unchecked { x -= y; }`, `if (ok) t -= x;`) and a write through a storage alias count for the ledger check; `unchecked { x += y; }` on one line is read by the arithmetic pair; unsafe-math confirms only when both readings are of the same line. One SmartBugs target lost (an owner-only `WithdrawToHolder` that pays a caller-chosen address; the re-entry needs a second owner call), reentrancy false confirmations 13 → 11. The baseline re-run today before any change confirmed 96, one more than the file published on the 16th; the extra one (`smart_billions.sol` `invest`) is read in [ACCOUNTING.md](ACCOUNTING.md) and is false. Only names that mean one privileged party count as owner-only (`onlyMember`, `onlyStaker` stay in scope), which keeps two false reentrancy confirmations | 62% | 48% | 90% | 72% |
| [2026-09-19 ninth](history/2026-09-19-before-crossfile.md) | three defects found by building [MODERN.md](MODERN.md), the first measurement against recent audit contests: a return clause (`external returns (address)`) was read as a modifier, so every returning function was invisible to `modifier-lens`; the access pair now follows the helpers a function calls, as the reentrancy pair already did; `modifier lock()` over an `_unlocked` flag counts as a reentrancy guard, which is the Uniswap V2 Pair idiom. Recall unchanged, one fewer false confirmation | 62% | 49% | 90% | 72% |
| [2026-09-19 tenth](history/2026-09-19-before-consistency.md) | a lens stops reading one file at a time: a contract is now read with the state and the internal helpers it inherits, resolved through the inheritance graph of the whole run and nothing wider. Nested mappings (`mapping(a => mapping(b => c))`) are declarations at last; the first cut stopped at the first closing bracket, so a balance keyed by two things was not state at all. Both came from [MODERN.md](MODERN.md), where four of the seven targets went from invisible to candidates. Recall 62% to 63% with precision held | 63% | 49% | 90% | 72% |
| [2026-09-19 eleventh](history/2026-09-20-before-determinism.md) | `consistency-lens`, a ninth lens and a third reading of the access risk: a function that writes state its siblings only write behind a guard, and carries no guard itself. The contract says what the guard for a variable is, so a name that looks nothing like a fee or an owner is still readable. Built against [MODERN.md](MODERN.md), where it takes the recall on recent audit findings from 0% to 29% and which it therefore stops holding out; three rules narrow it, each from a false confirmation there (a one-shot `initializer` is guarded by being one-shot, a function that tests its own caller is not missing a guard, the caller must be able to reach the write). One more labelled SmartBugs target confirmed (`multiowned_vulnerable.sol` `newOwner`), four more false confirmations, and the held-out corpus did not move at all | 64% | 48% | 90% | 72% |
| [2026-09-20 twelfth](history/2026-09-20-before-determinism.md) | not a lens change: a defect that made this table depend on luck. `_reads` reported only the first variable a line mentions, taken from a set, and Python randomises set order per process, so `require(balances[msg.sender] >= MinDeposit)` reported `balances` in one run and `MinDeposit` in the next. payout-lens intersects what a function reads with what it writes, so identical code confirmed an accounting finding on one run and not on the next: three runs of this corpus on the same commit gave 523, 518 and 517 any-lens sightings. Every match on a line is reported now, in a fixed order, and three runs under different hash seeds produce byte-identical files. The confirmed set did not move at all; the any-lens count settles at 513 because the duplicates it was counting were never distinct findings | 64% | 48% | 90% | 72% |
| [2026-09-20 thirteenth](history/2026-09-20-before-structfields.md) | a struct's fields are not contract state. `struct SwapParams { bool zeroForOne; }` made `zeroForOne` a state variable everywhere in the file, so a local or a named return sharing a field's name read as a state write; a Uniswap adapter's `quote` was confirmed for assigning a local bool. Found by reading the first confirmations of the Robinhood Chain re-run. One fewer confirmation here and all 47 true ones kept, so precision 48% to 49% with recall held; on the modern corpus 40 confirmations to 36 with the same two true; the held-out corpus did not move | 64% | 49% | 90% | 72% |
| [2026-09-22 fourteenth](ROBINHOOD.md) | a hand-rolled one-shot guard is one-shot. The lens knew the OpenZeppelin `initializer` modifier and nothing else, so `if (_initialized) revert AlreadyInitialized();` with no modifier read as an unguarded setter beside guarded siblings (`DirectLaunchFeeSplitter.initialize`, found on the Robinhood Chain run). A function now counts as one-shot if it refuses to run when a flag is set AND sets that flag itself; both halves are required, or a paused check would qualify. **This moves nothing here.** All three labelled corpora are identical before and after, so the rule earns no number; its evidence is one hand-read false confirmation in the wild and two tests | 64% | 49% | 90% | 72% |
| [2026-09-24 fifteenth](history/2026-09-24-before-splitwitness.md) | not a lens change: the harness was not using the swarm's own definition of a confirmation. `quorum/swarm.py` has held a rule since the Robinhood Chain run that the two readings of an `unsafe-math` finding must be of the same sum, because wrap-lens on an `unchecked` add and bound-lens on the checked `+=` above it are two candidates and not agreement. The benchmarks kept their own idea of confirmed, keyed on the function alone, so every published unsafe-math number described a tool that was not the shipped one. Both now import `split_witness` from the swarm. No lens moved and no true positive was lost: SmartBugs 96 confirmations to 91 with the same 47 true, held-out 8 to 7 with the same 5 true, the modern corpus 36 to 29 with the same 2 | 64% | 52% | 90% | 72% |

All twelve changes were made after looking at this corpus, so every row after the first is a tuned
number. The seventh added a pair for a bug this corpus does not label, so its four confirmations
there can only count as false; the row records what the pair costs, not what it finds. The held-out run above is the untuned one. It did not move for the third and fourth
changes; the fifth moved it from 30% / 60% to 40% / 44%, because the old arithmetic pair
could not confirm anything there and the new one confirms four; the sixth moved it to 50% / 62%
(one more true positive, two fewer false).

## What the numbers say

- The two-witness rule is a precision filter and it costs recall, on both corpora. SmartBugs
  reentrancy: the lenses alone reach 90% recall at 31% precision; the rule gives 72% precision at
  the same 90% recall. Arithmetic: 100% at 12% alone, 81% at 35% with the rule. Held out: any lens
  4% precision, the rule 62%.
- The sixth run changed the comparison with Slither. Until then Slither was more precise on
  reentrancy (62% against 44%); the difference was one rule Slither has always applied, that a
  2300-gas `transfer`/`send` cannot re-enter. With the same rule the two-witness pair finds 28 of
  31 at 72% against Slither's 28 at 62%. Slither still finds more access-control bugs on this
  corpus (33% against 10%) and follows calls and storage, which the lenses do not: a call inside a
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
  unchecked arithmetic behind a guard is a candidate; only both together confirm. 81% recall at
  35% precision on 2017 code, where Slither has no overflow detector at all. Division before
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
