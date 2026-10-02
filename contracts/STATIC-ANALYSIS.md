# Static analysis of ClaimRegistry

Both Slither and Aderyn were run on `src/` (0.8.28, optimizer 200). Neither finds a real bug, and
we leave what they flag on the record with the reason it does not hold, rather than reporting "zero
findings". This is the same discipline the product applies to other people's code: a flag is a claim
until it survives review.

Reproduce:
```
cd contracts
slither . --filter-paths "lib|test|script|out" --exclude-dependencies
aderyn .
```

## What the tools reported

- **Slither** (3 contracts, 100 detectors): 3 results, all on `ClaimRegistry.claim`:
  - `reentrancy-no-eth`: external calls (`transferFrom` via raw call L53-54, `token.burn` L59) with the
    guard variable `_entered` written afterward (L64).
  - `reentrancy-events` (x2): `Claimed` emitted after the external calls (L63).
- **Aderyn**: 1 High — "Reentrancy: State change after external call" (same site); 1 Low — "Missing
  Inheritance" (cosmetic: the contract does not formally `is` an interface).

## Why each is a false positive

`claim` (src/ClaimRegistry.sol#44-65):

1. **Explicit reentrancy guard.** `_entered` is 1 at rest, set to 2 at entry (L46) and checked at
   entry (L45: `if (_entered != 1) revert Reentered()`), then reset to 1 at the end (L64). While the
   external calls run, `_entered == 2`, so any re-entrant `claim` reverts. The `_entered = 1` that
   Slither flags "after the call" is the guard *release*, which is correct precisely because it runs
   last.
2. **Marked before the external call.** `claimedAt[digest][msg.sender]` is set at L49, before any
   external call. Even without the guard, a re-entrant claim of the same digest reverts with
   `AlreadyClaimed`.
3. **No second external function.** The contract has one state-changing external function (`claim`).
   There is nothing else to cross-reenter, so the "cross-function reentrancy" note has no target.
4. **Proven by test.** `test/ClaimRegistry.t.sol::test_ReentryDuringTransferIsRefused` wires a token
   that calls back into `claim` during `transferFrom`; the re-entrant call is refused. `forge test`
   is green (19 tests incl. a fuzz and an invariant).

The `reentrancy-events` flags are event ordering only (emit after an external call); no state the
event reflects is wrong. The Aderyn "Missing Inheritance" Low is cosmetic — the registry calls the
token through `IQuorumToken` but does not itself implement an interface.

## Conclusion

The flagged pattern is real (external calls sit mid-function), and it is safe here by construction:
a guard, mark-before-call ordering, a single external function, and a test that exercises the exact
re-entrant path. No change is made to suppress the detectors; the reasoning is the record.
