# The accounting pair, measured before it was posted

Built 2026-09-16. The shape, in the words that announced it: a contract that adds to a balance in one function and never takes it back in another. Two readings of that one bug:

- `ledger-lens` reads the whole contract: is there any way down for this variable? A state mapping or integer whose every write, anywhere in the contract, is a credit (`+=`, `++`, `x = x + …`) is a one-way ledger. The lens sights every externally callable function that reads such a ledger and never writes it.
- `payout-lens` reads one function: does value leave here (a call with value, a transfer, a send, a token transfer) against a balance-typed storage variable this function reads and never reduces?

A counter that only grows, read by a setter, gives ledger-lens alone. A payout against a balance the contract lowers elsewhere gives payout-lens alone. Only both together confirm. Names that count rather than hold (…Id, …Count, …Index, …Nonce) and names that configure (owner, fee, rate, price, …) are not ledgers; the first list was added after the run below and is marked as tuned.

**Not this shape, and not visible to a line reader:** a sibling function that forgot one debit another function has. There the variable does go down somewhere, on the other path. The three accounting bugs in the private practice log (Wise Lending, Cork, ZeroLend) are all that second kind; catching them needs a reader that follows calls, which these lenses are not.

## The teaching contract

`tests/test_quorum.py`, `ONE_WAY_VAULT`: `deposit` credits `credits[msg.sender]`, `claim` requires the credit and pays with a call, and nothing in the contract ever lowers `credits`. Both lenses land on `claim`. The fixed twin adds one line, `credits[msg.sender] -= amount`, and neither lens fires. A monotonic `totalDeposited` read by `setCap` gets ledger-lens alone; an `unstake` that pays against a `stake` the owner can zero elsewhere gets payout-lens alone; a `sweep` that reads only `owner` and `feeRate` gets nothing.

## Every real file already on disk

Same day, same code. Every confirmed accounting finding is listed and was read by hand.

| corpus | files | confirmed by the pair | read by hand |
|---|---|---|---|
| SmartBugs-curated (2017 code, labelled for other bugs) | 143 | 4 | 4 pay against a balance the contract never lowers. All 4 count as false in `BENCHMARK.md`, because the corpus labels none of its files for this bug and the rule there is harsh on purpose |
| DeFiVulnLabs (modern teaching contracts) | 57 | 0 | |
| Twelve audited codebases (Pashov-reviewed repos on disk, tests and libraries excluded) | 1,164 | 0 | payout-lens alone 20 times, ledger-lens alone 3 times, all held back |
| Nine verified production contracts (`targets/`: Ethereum, Base, Arbitrum, Optimism, Polygon wrapped tokens; Aerodrome Router; Friend.tech; WETH9; a Compound proxy) | 9 | 0 | |

The four on SmartBugs:

- `0xb11b2fed…`, `0xbaa3de65…`, `0xbebbfe5b…` (three copies of one honeypot, `VaultProxy`/`DepositProxy`): `withdraw` checks `Deposits[msg.sender] >= amount`, transfers, and `Deposits` is only ever credited. The recorded balance never goes down after a withdrawal. True by shape.
- `0x663e4229…` (`SaleClockAuctionERC20`): `withdrawERC20Balance` requires `balances[token] > 0`, transfers `balances[token]`, and never zeroes it. True by shape.

Before the counter-name exclusion the first cut confirmed seven: the four above plus a raffle's `getRefund` and `buyTickets` (the one-way variable was `raffleId`) and a breeding game's `giveBirth` (`gen0CreatedCount`). An id and a count are not balances; the exclusion is a name rule and is recorded as tuned on this corpus.

## What the pair costs the existing numbers

SmartBugs, seventh run: recall unchanged at 63%; overall precision 51% → 48%, because the four confirmations above count as false under the rule. Held-out: unchanged, 50% / 62%. Full tables in `BENCHMARK.md`, `HELDOUT.md`; before-files in `history/2026-09-16-before-accounting.md` and `history/2026-09-16-heldout-before-accounting.md`.

## What is not measured

Recall. No corpus on disk labels this bug, so there is no number for how many such bugs the pair finds. The Pashov reviews name at least four of exactly this shape (a `totalStaked` only incremented; an `amountDeposited` never decreased on withdraw; unclaimed rewards never decremented; withdrawn earnings never reduced), but none of those repos is on disk. The first honest recall number waits for the outside-labels benchmark.

```
$ python bench/run.py <smartbugs-curated>                                  # BENCHMARK.md
$ python bench/run.py <DeFiVulnLabs> --labels bench/labels/defivulnlabs.json   # HELDOUT.md
$ quorum --db fresh.db run --targets targets/ethereum/WETH9.sol targets/base/WETH9.sol targets/arbitrum/TransparentUpgradeableProxy.sol targets/optimism/WETH9.sol targets/polygon/WMATIC.sol
scanned 40 lens-units | confirmed 0 | recalled 0 | candidates 20 | suppressed 0 | duplicate work avoided 0
$ quorum --db fresh.db run --targets targets/Router.sol targets/WETH9.sol targets/TransparentUpgradeableProxy.sol
scanned 24 lens-units | confirmed 0 | recalled 0 | candidates 9 | suppressed 0 | duplicate work avoided 0
```
