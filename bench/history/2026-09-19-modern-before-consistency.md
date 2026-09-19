# The 8 lenses on recent audit contests

Run 2026-09-19 · 16 contests, each at the commit its published report links · 512 Solidity files scanned · quorum threshold 2 · `python bench/modern.py <workdir> --labels bench/labels/modern-c4.json`

## What share of modern findings is this tool even looking for

| | count |
|---|---|
| High and Medium findings read and classified | 131 |
| of those, High | 29 |
| in one of the four shapes Quorum's lenses look for | 7 |
| not a shape Quorum looks for | 124 |
| could not be tied to a file and function at that commit | 3 |

The four risks account for **5%** of what these audits reported at High and Medium. Everything else was: business-logic 62, dos 16, validation 15, signature 7, slippage 6, token-integration 5, rounding-precision 5, front-running 2, config 2, other 2, cross-chain 1, oracle 1.

That number is the ceiling on this tool's usefulness against a modern audit, before asking whether it finds the ones it is looking for. It is a line-reading scanner for four bug shapes, not an auditor.

## Of the shapes it does look for

| risk | targets | any-lens found | true | precision | recall | **quorum confirmed** | true | **precision** | **recall** |
|---|---|---|---|---|---|---|---|---|---|
| reentrancy | 1 | 91 | 0 | 0% | 0% | **5** | 0 | **0%** | **0%** |
| unguarded-state-write | 5 | 346 | 4 | 1% | 80% | **7** | 0 | **0%** | **0%** |
| unsafe-math | 0 | 221 | 0 | 0% | n/a | **12** | 0 | **0%** | **n/a** |
| accounting-mismatch | 1 | 92 | 0 | 0% | 0% | **4** | 0 | **0%** | **0%** |
| **all** | 7 | 750 | 4 | 1% | 57% | **28** | 0 | **0%** | **0%** |

## Every labelled target, and what the lenses did with it

- `2025-02-recall/contracts/contracts/gateway/GatewayManagerFacet.sol` `register` unguarded-state-write — missed, seen by no lens
- `2025-02-recall/contracts/contracts/gateway/router/CheckpointingFacet.sol` `execBottomUpMsgs` accounting-mismatch — missed, seen by no lens
- `2025-02-recall/contracts/contracts/subnet/SubnetActorManagerFacet.sol` `leave` reentrancy — missed, seen by no lens
- `2025-04-virtuals-protocol/contracts/contribution/ServiceNft.sol` `updateImpact` unguarded-state-write — candidate, seen by modifier-lens
- `2025-04-virtuals-protocol/contracts/virtualPersona/AgentNftV2.sol` `addValidator` unguarded-state-write — candidate, seen by modifier-lens
- `2025-04-virtuals-protocol/contracts/virtualPersona/AgentVeToken.sol` `stake` unguarded-state-write — candidate, seen by modifier-lens
- `2025-05-blackhole/contracts/AlgebraCLVe33/GaugeFactoryCL.sol` `createGauge` unguarded-state-write — candidate, seen by modifier-lens

## Why each of the seven was missed

Read one by one in the source, not inferred from the table.

| target | why the lenses did not confirm it |
|---|---|
| recall `leave` reentrancy | The function carries `nonReentrant`. The re-entry comes through `stake`, a different entry point that has no guard. A cross-function bug: the announced limit, and a line reader inside one function cannot see it. |
| recall `register` unguarded write | Every write goes through `s.` and a local `Subnet storage` pointer. The state is a struct reached through a library, not a declaration this contract inherits, so even reading across files there is no state write here to see. |
| recall `execBottomUpMsgs` accounting | Same cause: `s.circSupply` is not a declaration this file contains. |
| virtuals `addValidator` unguarded write | The function body writes nothing; the writes happen in `_addValidator`, inherited from another file. Since reading across files this is a candidate, seen by `modifier-lens`. |
| virtuals `stake`, `updateImpact` unguarded write | Both seen by `modifier-lens` and held as candidates. `sender-lens` did not corroborate because each body mentions `msg.sender`, which the lens reads as a caller check. |
| blackhole `createGauge` unguarded write | Seen by `modifier-lens`, held as a candidate. `sender-lens` did not corroborate because the variables written (`last_gauge`, `__gauges`) do not carry a privileged-looking name. |

Four of the seven are now candidates rather than invisible, because a lens reads what a contract inherits since
v0.6.0. None of the four is confirmed, and they all stop at the same place: `sender-lens`, the second reading of
the access pair, keys on the *name* of the variable written (fee, rate, owner, oracle and the rest) and on the
absence of `msg.sender`. Modern code writes `last_gauge` and `_validatorsMap`. Loosening that rule to "any state
write" would make the two lenses one lens, and a quorum of one is not a quorum, so the answer is a genuinely
different second reading and it is not designed yet. That is the next open question, and it will be worked on the
labelled corpora, not here.

Four of the seven come down to one thing: **this tool reads one file at a time.** Modern protocols keep their state in a diamond struct, a base contract or a library, and split a function's work across files. That is not a rule to tune; it is a different program, and it is written down as the next decision rather than hidden in a number.

## What this corpus changed, and what it deliberately did not

Three defects showed up here and were fixed the same day, each with a test built from the shape that exposed it, and each measured on the labelled corpora before and after:

1. A return clause read as a modifier. `external returns (address)` made `modifier-lens` treat a function as guarded, so every function that returns something was invisible to it.
2. The access pair did not follow the helpers a function calls, although the reentrancy pair had been taught to in v0.4.1.
3. `modifier lock()` over an `_unlocked` flag was not recognised as a reentrancy guard. That is the Uniswap V2 Pair idiom and the most forked guard in Solidity, so every fork of it looked unguarded.

On SmartBugs-curated those three moved precision from 48% to 49% with recall unchanged at 62%; the held-out corpus did not move at all.

Two things this corpus showed that were **not** turned into rules, because inventing a rule from the test set is how a benchmark stops meaning anything:

- A zero-argument setter that copies a value from a trusted contract has no access control and needs none, because the caller chooses nothing. Seven of the false confirmations are that one shape.
- An `unchecked` block whose operands are bounded by a checked operation on the line above it cannot wrap. Most of the arithmetic false confirmations are that shape.

Both are written down here and will be built against the labelled corpora first, then re-measured here.

## Per lens

| lens | sightings | on a target |
|---|---|---|
| callorder-lens | 15 | 0 |
| guard-lens | 81 | 0 |
| modifier-lens | 320 | 4 |
| sender-lens | 33 | 0 |
| wrap-lens | 23 | 0 |
| bound-lens | 210 | 0 |
| ledger-lens | 22 | 0 |
| payout-lens | 74 | 0 |

Candidates held back by the rule (one lens only): 722. Confirmations that name no labelled finding: 28.

## The confirmations, read by hand

All 28 were opened and read in the source. None is a bug the audit missed. Nine are `unchecked` arithmetic
bounded by a checked operation beside it, seven are a zero-argument setter that copies a value from a trusted
contract, four are vendored Uniswap libraries whose wrap is the design, four are payouts that zero the balance
before they pay, two are calls to a contract fixed in the constructor, and one is a stateless multicall helper
that holds no funds.

The twenty-eighth is worth its own line, because it is not quite a false alarm. `ReferralRegistry.becomeReferrer`
in the Merkl contest pays ether to an address any caller can register, and pulls a caller-chosen token, before it
writes its state, with no guard anywhere in the file despite a comment that claims one. The audit did not report
it because the file is named in that contest's out-of-scope list. So the shape is real and nobody was looking at
it; it is not counted as a true positive here, because this benchmark scores against what the audits found, and
nothing was verified beyond reading it.

## Contests

| contest | findings | Quorum-shaped | files scanned | confirmations |
|---|---|---|---|---|
| 2025-01-liquid-ron | 3 | 0 | 6 | 1 |
| 2025-01-next-generation | 2 | 0 | 6 | 0 |
| 2025-02-recall | 13 | 3 | 36 | 0 |
| 2025-03-nudgexyz | 4 | 0 | 3 | 0 |
| 2025-04-bitvault | 2 | 0 | 49 | 0 |
| 2025-04-kinetiq | 8 | 0 | 9 | 0 |
| 2025-04-virtuals-protocol | 32 | 3 | 52 | 4 |
| 2025-05-blackhole | 24 | 1 | 64 | 4 |
| 2025-08-morpheus | 4 | 0 | 41 | 0 |
| 2025-10-hybra-finance | 10 | 0 | 89 | 6 |
| 2025-10-sequence | 6 | 0 | 35 | 0 |
| 2025-11-ekubo | 4 | 0 | 81 | 1 |
| 2025-11-garden | 1 | 0 | 6 | 0 |
| 2025-11-megapot | 11 | 0 | 6 | 2 |
| 2025-11-merkl | 3 | 0 | 21 | 8 |
| 2025-11-sukukfi | 4 | 0 | 8 | 2 |
