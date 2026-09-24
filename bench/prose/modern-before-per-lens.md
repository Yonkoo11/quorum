## What happened to each of the seven

Read one by one in the source, not inferred from the table.

| target | what happened |
|---|---|
| recall `leave` reentrancy | Carries `nonReentrant`. The re-entry comes through `stake`, a different entry point with no guard. A cross-function bug, and a line reader inside one function cannot see it. |
| recall `register` unguarded write | Every write goes through `s.` and a local `Subnet storage` pointer. The state is a struct reached through a library, not a declaration this contract inherits, so there is nothing here to key on even reading across files. |
| recall `execBottomUpMsgs` accounting | Re-read 2026-09-22; the earlier note here blamed the same struct-pointer cause as the row above, and that was wrong. `circSupply` is credited in `LibGateway.sol:252` and **debited in this very file**, `subnet.circSupply -= totalAmount` (line 151), so it has a way down and `ledger-lens` would not call it one-way even with perfect cross-file and diamond-storage sight. The bug is that the debit skips `IpcMsgKind.Call` messages, so one class of credit is never matched by a debit. That is a conditional gap in a two-way ledger, a strictly harder shape than the "no way down anywhere" this pair reads for. Not a reader gap; a scope gap. |
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

The five still missed do not share one cause. An earlier version of this paragraph said they did; corrected
2026-09-22 after re-reading the source.

- **One is a reader gap.** `register`: a diamond struct reached through `s.` is not a declaration any file
  contains, so **this tool reads declarations, not storage pointers** and there is no state write to see. That is
  not a rule to tune, it is a different program.
- **One is a scope gap.** `execBottomUpMsgs`: the ledger is debited in the same file, so no amount of reader work
  reaches it. The pair reads for a balance with no way down anywhere; this is a conditional gap in a ledger that
  does have one. The row above says it in full.
- **One is cross-function.** `leave` carries `nonReentrant`; the re-entry arrives through a different entry point.
- **Two are the rule working as designed.** `stake` and `createGauge` are single-lens candidates, held back
  because the siblings that write the same state do not agree on a guard, so there was nothing to corroborate.

Lumping them together made one fixable-looking problem out of three different ones, and only the first is a
reader that could be extended.

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

An observation from the first run said most of the arithmetic false confirmations were an `unchecked` block whose
operands are bounded by a checked operation on the line above, and that a rule for it was owed. On 2026-09-24
that was chased, and there was no rule to write. The shape was real, but the tool already refused it: the swarm
has required since the Robinhood Chain run that the two readings of an `unsafe-math` finding be of the **same
sum**, and wrap-lens on the `unchecked` add plus bound-lens on the checked `+=` above it is two candidates, not
agreement. The benchmark was the only thing counting them, because it kept its own definition of a confirmation
keyed on the function alone. Both harnesses import the swarm's rule now. Seven of the nine went, no lens moved,
and no recall number changed anywhere. The remaining two are cases where both readings really are of one line.

