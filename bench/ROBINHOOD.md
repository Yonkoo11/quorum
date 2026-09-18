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

Every one of the 281 confirmed findings was read by a person (with Claude reading alongside, each verdict tied to a concrete reason in the file). The full list of verdicts with one reason each is in [hand-read.json](robinhood/hand-read.json).

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
| after | 62% | 49% | 50% | 62% |

The labelled corpora barely move, which is the point: they were built from the bugs the lenses were written for. The wild run is where the change shows, and it is being re-done with the new lenses; its numbers are appended here when it finishes.

## Reproduce

```
python bench/ecosystem.py <workdir>            # a day of machine time; resumable
python bench/ecosystem.py <workdir> --report   # this file's first half
```
