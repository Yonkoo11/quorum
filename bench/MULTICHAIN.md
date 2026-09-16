# Verified source from five chains, no key

Run 2026-09-13 (fetch) and re-run 2026-09-16 with the eight lenses (the swarm lines below) · `quorum fetch --chain <name> <address>` · Blockscout v2 API on each chain · no API key, no RPC, no token.

One verified contract per chain, chosen because each is the wrapped native token (or the canonical proxy on Arbitrum) and anyone can check it exists. The sixth address is a deliberate miss to show what a refusal looks like.

```
$ quorum fetch --chain ethereum 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
$ quorum fetch --chain base 0x4200000000000000000000000000000000000006
$ quorum fetch --chain arbitrum 0x82aF49447D8a07e3bd95BD0d56f35241523fBab1
$ quorum fetch --chain optimism 0x4200000000000000000000000000000000000006
$ quorum fetch --chain polygon 0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270 0x0000000000000000000000000000000000000001
saved ethereum/WETH9.sol  (38,401 bytes)  0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
saved base/WETH9.sol  (38,516 bytes)  0x4200000000000000000000000000000000000006
saved arbitrum/TransparentUpgradeableProxy.sol  (20,235 bytes)  0x82aF49447D8a07e3bd95BD0d56f35241523fBab1
saved optimism/WETH9.sol  (37,684 bytes)  0x4200000000000000000000000000000000000006
saved polygon/WMATIC.sol  (38,492 bytes)  0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270
not saved 0x0000000000000000000000000000000000000001 has no verified source on polygon
exit 1
```

Files land under `targets/<chain>/`, and a finding is keyed by that path, so `WETH9.sol` on three chains is three targets, not one. A multi-file contract (the Arbitrum proxy came back as one main file and three imports) is joined into one file with a `// file: <path>` line before each part.

## The swarm on the five files, fresh memory

```
$ quorum --db fresh.db run
  candidate polygon/WMATIC.sol:transferFrom unsafe-math  only wrap-lens — held back

scanned 40 lens-units | confirmed 0 | recalled 0 | candidates 20 | suppressed 0 | duplicate work avoided 0

$ quorum --db fresh2.db run --no-memory

scanned 40 lens-units | confirmed 0 | recalled 0 | candidates 20 | suppressed 0 | duplicate work avoided 0
nothing was confirmed, recalled or suppressed: without memory the swarm cannot corroborate, recognise or forget.
```

Nothing confirmed on any of the five: every sighting was one lens alone and was held back. That is the expected answer on years-old, heavily used wrapped-token code, and it is the same answer on every chain, which is the point of the run. The `recalled 0` is because the memory was fresh; on a memory that has learned the fixture idiom, the Base file recalls as before.

## What the explorer can and cannot do

The file name is the contract name with everything but `[A-Za-z0-9_.-]` replaced, it goes under `targets/<chain>/`, and an answer over 5 MB, without verified source, or that is not JSON is refused with one line and the command moves to the next address (exit code 1 at the end). Tests: `tests/test_targets.py`, 8 tests, no network.
