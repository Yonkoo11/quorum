# The 9 lenses on recent audit contests

Run 2026-09-20 · 16 contests, each at the commit its published report links · 512 Solidity files scanned · quorum threshold 2 · `python bench/modern.py <workdir> --labels bench/labels/modern-c4.json`

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
| unguarded-state-write | 5 | 354 | 4 | 1% | 80% | **19** | 2 | **11%** | **40%** |
| unsafe-math | 0 | 221 | 0 | 0% | n/a | **12** | 0 | **0%** | **n/a** |
| accounting-mismatch | 1 | 84 | 0 | 0% | 0% | **4** | 0 | **0%** | **0%** |
| **all** | 7 | 750 | 4 | 1% | 57% | **40** | 2 | **5%** | **29%** |

## Every labelled target, and what the lenses did with it

- `2025-02-recall/contracts/contracts/gateway/GatewayManagerFacet.sol` `register` unguarded-state-write — missed, seen by no lens
- `2025-02-recall/contracts/contracts/gateway/router/CheckpointingFacet.sol` `execBottomUpMsgs` accounting-mismatch — missed, seen by no lens
- `2025-02-recall/contracts/contracts/subnet/SubnetActorManagerFacet.sol` `leave` reentrancy — missed, seen by no lens
- `2025-04-virtuals-protocol/contracts/contribution/ServiceNft.sol` `updateImpact` unguarded-state-write — CONFIRMED, seen by consistency-lens, modifier-lens
- `2025-04-virtuals-protocol/contracts/virtualPersona/AgentNftV2.sol` `addValidator` unguarded-state-write — CONFIRMED, seen by consistency-lens, modifier-lens
- `2025-04-virtuals-protocol/contracts/virtualPersona/AgentVeToken.sol` `stake` unguarded-state-write — candidate, seen by modifier-lens
- `2025-05-blackhole/contracts/AlgebraCLVe33/GaugeFactoryCL.sol` `createGauge` unguarded-state-write — candidate, seen by modifier-lens

## What happened to each of the seven

Read one by one in the source, not inferred from the table.

| target | what happened |
|---|---|
| recall `leave` reentrancy | Carries `nonReentrant`. The re-entry comes through `stake`, a different entry point with no guard. A cross-function bug, and a line reader inside one function cannot see it. |
| recall `register` unguarded write | Every write goes through `s.` and a local `Subnet storage` pointer. The state is a struct reached through a library, not a declaration this contract inherits, so there is nothing here to key on even reading across files. |
| recall `execBottomUpMsgs` accounting | Same cause: `s.circSupply` is not a declaration this file contains. |
| virtuals `addValidator` unguarded write | **Confirmed.** The body writes nothing; the write is in `_addValidator`, inherited from another file, which `modifier-lens` has been able to see since v0.6.0. `consistency-lens` corroborates: the contract's other writers of `_validatorsMap` all carry a modifier this one does not. |
| virtuals `updateImpact` unguarded write | **Confirmed**, the same way. `mint` writes `_maturities` behind a sender check and `updateImpact` is `public` with nothing. |
| virtuals `stake` unguarded write | Candidate, `modifier-lens` alone. Its siblings that write the same state do not agree on a guard, so there is nothing for the second reading to compare it against. |
| blackhole `createGauge` unguarded write | Candidate, `modifier-lens` alone, for the same reason. |

The second reading of the access pair used to be `sender-lens`, which keys on the *name* of the variable written
(fee, rate, owner, oracle) and on the absence of `msg.sender`. Modern code writes `last_gauge` and
`_validatorsMap`, so it corroborated nothing on this corpus and the recall here was 0%. `consistency-lens`, added
in v0.7.0, is the different second reading that was missing: it asks the contract itself what the guard for a
variable is, by reading what its other writers carry. It confirms two of the seven. It is not free, and the cost
is the next section.

Three of the five still missed come down to one thing: **this tool reads declarations, not storage pointers.**
A diamond struct reached through `s.` is not a declaration any file contains, so there is no state write to see.
That is not a rule to tune; it is a different program, and it is written down as the next decision rather than
hidden in a number.

## What this corpus changed, and what it stopped being

**This corpus is no longer held out for the access risk.** `consistency-lens` was developed against it. Each of
the three rules that narrow it came from opening a false confirmation here and finding a principled reason for
it: a one-shot `initializer` is guarded by being one-shot; a function that tests its own caller is not missing a
guard; and the caller has to be able to reach the write, by choosing either the value or the slot. The two
findings it confirms were labelled blind, months before the lens existed, but the 29% recall above is no longer a
measurement on code the tool has never been fitted to. Anyone reading that number should read this paragraph with
it.

[`HELDOUT.md`](HELDOUT.md) (DeFiVulnLabs) stays the one corpus no lens has ever been tuned against, and it did not
move: 62% precision, 50% recall, the same eight confirmations, before and after. On the tuned corpus
([`BENCHMARK.md`](BENCHMARK.md)) the new lens cost one point of precision (49% to 48%) and gained one of recall
(63% to 64%), and it confirmed one more labelled access-control bug there, `multiowned_vulnerable.sol` `newOwner`.

Earlier, three defects showed up on this corpus and were fixed the same day, each with a test built from the shape
that exposed it, and each measured on the labelled corpora before and after:

1. A return clause read as a modifier. `external returns (address)` made `modifier-lens` treat a function as guarded, so every function that returns something was invisible to it.
2. The access pair did not follow the helpers a function calls, although the reentrancy pair had been taught to in v0.4.1.
3. `modifier lock()` over an `_unlocked` flag was not recognised as a reentrancy guard. That is the Uniswap V2 Pair idiom and the most forked guard in Solidity, so every fork of it looked unguarded.

On SmartBugs-curated those three moved precision from 48% to 49% with recall unchanged at 62%; the held-out corpus
did not move at all.

One observation from the first run is still **not** a rule. An `unchecked` block whose operands are bounded by a
checked operation on the line above it cannot wrap, and most of the arithmetic false confirmations are that shape.
It will be built against a labelled corpus first, then re-measured here.

## Per lens

| lens | sightings | on a target |
|---|---|---|
| callorder-lens | 15 | 0 |
| guard-lens | 81 | 0 |
| modifier-lens | 320 | 4 |
| sender-lens | 33 | 0 |
| consistency-lens | 20 | 2 |
| wrap-lens | 23 | 0 |
| bound-lens | 210 | 0 |
| ledger-lens | 22 | 0 |
| payout-lens | 66 | 0 |

Candidates held back by the rule (one lens only): 710. Confirmations that name no labelled finding: 38.

## The confirmations, read by hand

All 40 were opened and read in the source. None is a bug an audit missed.

The 28 from the run before the consistency lens are unchanged: nine are `unchecked` arithmetic bounded by a
checked operation beside it, seven are a setter that copies a value out of a trusted contract, four are vendored
Uniswap libraries whose wrap is the design, four are payouts that zero the balance before they pay, two are calls
to a contract fixed in the constructor, one is a stateless multicall helper that holds no funds, and one is
`ReferralRegistry.becomeReferrer`, below.

The twelve the consistency lens takes part in were read this run. Two are the labelled findings above. The other
ten are false, in four shapes:

- **Write-once on a fresh id** (morpheus `createBuilderPool`, twice, and merkl `addReferralKey`). The id is a hash of a name the caller supplies, and an existence check refuses to overwrite anything, so an arbitrary caller can only write a slot nobody was using.
- **An in-body check the modifier reading cannot see** (ekubo `transferFrom`, merkl `increaseTokenBalance`, bitvault `urgentRedemption`). An ERC20 allowance check, a `safeTransferFrom` that makes the caller pay for what they credit, and a shutdown-plus-balance check. The rule that skips a function testing its own caller wants `msg.sender` inside one `require`; these spread it over several statements.
- **The caller writes their own row** (blackhole and hybra `delegate`). `delegate(address)` calls `_delegate(msg.sender, delegatee)`, so the only slot written is the caller's. The rule that drops `v[msg.sender]` writes reads one line and cannot follow `msg.sender` into a helper's parameter.
- **A value no caller can influence** (morpheus `distributeRewards` writes `block.timestamp`, liquid-ron `pruneValidatorList` writes a constant `false` for a validator already fully unwound).

The first and the last are the two shapes worth a rule next, and like every other rule here they will be built
against a labelled corpus before they are measured on this one.

`ReferralRegistry.becomeReferrer` in the Merkl contest is still worth its own line, because it is not quite a
false alarm. It pays ether to an address any caller can register, and pulls a caller-chosen token, before it
writes its state, with no guard anywhere in the file despite a comment that claims one. The audit did not report
it because the file is named in that contest's out-of-scope list. So the shape is real and nobody was looking at
it. It is not counted as a true positive here, because this benchmark scores against what the audits found, and
nothing was verified beyond reading it.

## Contests

| contest | findings | Quorum-shaped | files scanned | confirmations |
|---|---|---|---|---|
| 2025-01-liquid-ron | 3 | 0 | 6 | 2 |
| 2025-01-next-generation | 2 | 0 | 6 | 0 |
| 2025-02-recall | 13 | 3 | 36 | 0 |
| 2025-03-nudgexyz | 4 | 0 | 3 | 0 |
| 2025-04-bitvault | 2 | 0 | 49 | 1 |
| 2025-04-kinetiq | 8 | 0 | 9 | 0 |
| 2025-04-virtuals-protocol | 32 | 3 | 52 | 6 |
| 2025-05-blackhole | 24 | 1 | 64 | 5 |
| 2025-08-morpheus | 4 | 0 | 41 | 3 |
| 2025-10-hybra-finance | 10 | 0 | 89 | 7 |
| 2025-10-sequence | 6 | 0 | 35 | 0 |
| 2025-11-ekubo | 4 | 0 | 81 | 2 |
| 2025-11-garden | 1 | 0 | 6 | 0 |
| 2025-11-megapot | 11 | 0 | 6 | 2 |
| 2025-11-merkl | 3 | 0 | 21 | 10 |
| 2025-11-sukukfi | 4 | 0 | 8 | 2 |
