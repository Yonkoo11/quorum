# Facts the Zcash checks rest on

Each block is re-fetched by `python3 -m watch.drift`. Format and host allow-list match
zcash-skills `docs/check-facts.py`. `verified` is the day the value was read from `upstream`.

```facts
id: zebra-latest-release
value: 7.0.0
verified: 2026-11-01
upstream: https://raw.githubusercontent.com/ZcashFoundation/zebra/main/CHANGELOG.md
extract: ^## \[Zebra (\d+\.\d+\.\d+)\]
```

```facts
id: zebra-advisories-page-1
value: GHSA-2w9f-9wx8-f5c8, GHSA-3c94-hf7p-g5mf, GHSA-5h3r-fpmj-483w, GHSA-6v36-c42v-v98p, GHSA-7jp4-mq53-4cvq, GHSA-9hq5-pfgc-cx5h, GHSA-h5rr-8pqv-grp9, GHSA-j4cw-58mj-7w6v, GHSA-jhpp-8h75-7pv5, GHSA-jq45-ghw5-v37x
verified: 2026-11-01
upstream: https://github.com/ZcashFoundation/zebra/security/advisories
extract: (GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4})
extract_all: true
note: the page shows the newest 10 of many; any change here means a new advisory was published
```

```facts
id: zebra-value-pool-ids
value: ironwood, lockbox, orchard, sapling, sprout, transparent
verified: 2026-11-01
upstream: https://raw.githubusercontent.com/ZcashFoundation/zebra/main/zebra-rpc/src/methods/types/get_blockchain_info.rs
extract: new_internal\("(\w+)"
extract_all: true
note: watch/zcash.py POOLS must list exactly these
```

```facts
id: zebra-max-block-subsidy
value: ((25 * COIN) / 2)
verified: 2026-11-01
upstream: https://raw.githubusercontent.com/ZcashFoundation/zebra/main/zebra-chain/src/parameters/network/subsidy/constants.rs
extract: MAX_BLOCK_SUBSIDY: u64 = (.+?) as u64;
note: 12.5 ZEC; watch/zcash.py MAX_BLOCK_SUBSIDY_ZAT = 1_250_000_000
```
