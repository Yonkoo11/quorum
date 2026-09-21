# Every public Solidity repo on Robinhood Chain, scanned

Run started 2026-09-16 18:44 UTC. Listing: heyresearch.xyz/api, projects with a public GitHub repo, every GitHub repo in each project's sources. Repos whose GitHub language list includes Solidity or Vyper were cloned at depth 1 and read by the eight lenses with a fresh memory per repo; tests, libraries, scripts and mocks excluded. Command: `python bench/ecosystem.py <workdir>`.

| | count |
|---|---|
| projects HEY lists with a public repo | 1456 |
| distinct GitHub repos in their sources | 1779 |
| repos containing Solidity, cloned and scanned | 631 |
| Solidity files read | 11,506 |
| lens-units scanned | 92,048 |
| findings confirmed (two lenses agreed) | 281 |
| candidates held back (one lens only) | 11,018 |
| repos with at least one confirmed finding | 149 |
| repos where nothing was confirmed | 482 |
| skipped: clone failed | 7 |
| skipped: error | 39 |
| skipped: no repo url | 28 |
| skipped: no solidity | 1127 |

Skipped listings without a Solidity repo are not counted as scanned. Seven repos failed to clone (deleted or private since HEY read them).

## The hand-read, 2026-09-18

Every one of the 281 confirmed findings was read by Claude Code under one strict rubric (true only if the shape is there and matters; false if guarded, bounded, by design or reduced elsewhere; out of scope for tests and mocks), each verdict tied to a concrete reason in the file. The three true findings and the three adjacent bugs were then re-read line by line in the source before anyone was told. No human read the 228 false ones; the reasons are there so anyone can. The full list of verdicts with one reason each is in [hand-read.json](robinhood/hand-read.json).

| verdict | count |
|---|---|
| true: the flagged shape is real and matters | 3 |
| false: the shape is guarded, bounded, by design, or reduced elsewhere | 228 |
| out of scope: test, mock, fixture, harness, deprecated or flattened audit copy that slipped past the path filter | 50 |

So on code nobody labelled, the lenses' confirmations were right about 1 time in 100. That number goes on the front page next to the 48% on the labelled corpus; the labelled corpus flatters the lenses because it was written to contain the bugs they look for.

The three true findings, and three more bugs the readers found next to a flagged line that the lenses did not point at, are with the repo owners first. They are added here with their reasons once fixed or fourteen days after the owner was told, whichever comes first.

## What the false ones teach, in order of count

1. **Unsafe-math on checked code.** 81 of the 96 unsafe-math confirmations were on a 0.8 pragma with the arithmetic outside `unchecked`, or inside an `unchecked` block whose operands are bounded by construction (Uniswap timestamp wrap, solmate balance adds). The wrap and bound lenses do not read the pragma. They will.
2. **Reentrancy on functions only the owner can call, or on calls to fixed addresses.** Most of the 82 false reentrancy confirmations were external calls in `onlyOwner` functions, calls to an immutable router or factory, or transfers to a burn address with only counters written afterwards. A re-entry by the owner into the owner's own function is not an attack, and a call to an immutable contract that cannot call back is not an entry.
3. **Accounting on a balance that is reduced in another function.** 47 false accounting confirmations, most of them a stake or deposit decremented in the withdraw path. The one-way check was meant to catch exactly that and missed some: a defect to reproduce and fix, not a rule to add.
4. **Test files outside test folders.** 50 out-of-scope findings came from `.t.sol`, `Mock*`, `Test*`, `fixtures/`, `harness`, `deprecated/` and `.flat.sol` audit copies that the path filter did not know. The filter learns the names.
5. **Reentrancy through a private helper.** The one exploitable reentrancy the readers found sits in a private function called by three external ones; the lenses only sight external functions and flagged the wrong shape on the neighbour. The call-order lens should follow one level of internal calls.

Every one of those became a change to the lenses the same day, measured on the labelled corpora before and after (before files in `history/2026-09-18-*`):

| | SmartBugs recall | SmartBugs precision | held-out recall | held-out precision |
|---|---|---|---|---|
| before | 63% | 48% | 50% | 62% |
| after | 62% | 48% | 50% | 62% |

The labelled corpora barely move, which is the point: they were built from the bugs the lenses were written for.

The whole run was then re-done twice, as the lenses grew:

| | first run, 2026-09-16 (8 lenses) | re-run, 2026-09-19 (8 lenses) | re-run, 2026-09-21 (9 lenses) |
|---|---|---|---|
| projects listed | 1,506 | 1,506 | 1,560 |
| repos with Solidity, scanned | 631 | 658 | 682 |
| Solidity files read | 11,506 | 11,132 | 10,849 |
| findings confirmed | 281 | 244 | 339 |

The third run added `consistency-lens`, the ninth, and it takes part in 115 of the 339, which is why the total rose. **All 115 were read by hand** (the other 224 are the reentrancy, arithmetic and old-access findings the earlier runs already characterised). Of the 115: 113 false, and two real bugs on live code that the audits had not touched, plus the two Virtuals findings the modern-audit corpus already carries.

1. **A Uniswap V4 hook where anyone can steal another position's fees.** `B20HUBHook.setPending` in madebyshun/blue-agent is `external` with no caller check, while the sibling that writes the same pool binding is `onlyPoolManager`. An attacker binds a junk pool to their own address and a victim's LP tokenId in one transaction, then calls the permissionless `claimFees`, which sweeps the victim position's fees to the hook and pays the attacker 80%. A code comment calls `claimFees` a revert stub; the collect path is fully implemented. The hook is deployed on Base 8453 (the repo's own notes verify its treasury on-chain, dated 2026-08-18).

2. **A circuit-breaker registry anyone can seize.** `BreakerRegistry.arm` in millw14/merrymen has no check that the caller controls the account it arms; the first caller becomes the permanent owner, and every other function is `onlyOwner`. An attacker front-runs the real owner, becomes the breaker owner for a victim account, and can `halt` it with no reset path for the victim. Griefing and denial of service, no direct profit.

The 113 false ones fall into the same shapes recorded in [MODERN.md](MODERN.md): a caller-keyed write, a fresh-slot-only registration, a one-shot init flag (the OpenZeppelin modifier and hand-rolled `if (_initialized) revert`), a value fixed by a signature, Merkle proof, vote or oracle, a payout whose recipient is never the caller, or a demo, test or benchmark file. The full hand-read is in the run's workdir, `FINDINGS.md`.

## Reproduce

```
python bench/ecosystem.py <workdir>            # a day of machine time; resumable
python bench/ecosystem.py <workdir> --report   # this file's first half
```
