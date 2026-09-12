# Quorum

[quorum site](https://yonkoo11.github.io/quorum/) · [demo video](https://github.com/Yonkoo11/quorum/releases/download/v0.1.0/quorum-demo-v2.mp4) · [the claim on Base](https://basescan.org/tx/0xa648821d91093df770b72c60be56834d069c9355c785e6195183e911f00bf713)

**A swarm of security lenses that never talk to each other. Sibyl Memory is the only channel between them, and it is the only reason the swarm can agree on anything, recognise anything, or forget anything.**

Six independent lenses read Solidity source. No lens can publish a finding on its own. A finding becomes real only when two lenses that work from different evidence arrive at the same conclusion, and the count of who agreed lives in memory, not in any agent's head. Once a pattern is confirmed, the swarm recognises that idiom on sight in a completely different contract, in a completely different session, from a single sighting.

Delete the memory layer and there is no swarm left. Just six programs that each shout once and forget.

---

## The 30-second version

```console
$ quorum run --targets fixtures/VulnerableVault.sol fixtures/OpenFeeSetter.sol
  QUORUM    VulnerableVault.sol:withdraw   reentrancy   corroborated by callorder-lens, guard-lens
  QUORUM    OpenFeeSetter.sol:setFeeRate   unguarded-state-write   corroborated by modifier-lens, sender-lens
scanned 12 lens-units | confirmed 2 | recalled 1 | candidates 5

# new process, new day, contracts it has never seen. Real verified Base mainnet source
$ quorum run
recalled before reading any code: 2 confirmed pattern(s)
  RECALLED  FriendtechSharesV1.sol:buyShares   reentrancy
            first confirmed on VulnerableVault.sol   (1 sighting was enough)
scanned 24 lens-units | confirmed 0 | recalled 1 | candidates 11

# same swarm, same contracts, memory removed
$ quorum run --no-memory
scanned 24 lens-units | confirmed 0 | recalled 0 | candidates 12
nothing was confirmed, recalled or suppressed: without memory the swarm
cannot corroborate, recognise or forget.
```

```console
$ quorum recall

confirmed patterns (REFERENCE tier)
  reentrancy             reentrancy:97d18d17cfa4494a
    first confirmed on VulnerableVault.sol by callorder-lens, guard-lens
    recognised since on FriendtechSharesV1.sol  (1 sighting each, no quorum needed)
```

The pattern was learned on a teaching fixture and recognised in production code deployed on Base. `msg.sender.call{value: amount}("")` and `protocolFeeDestination.call{value: protocolFee}("")` are the same idiom, so they hash to the same signature. `weth.deposit{value: amountETH}()` is a different idiom and does not.

---

## Where memory is load-bearing

Every Sibyl Memory read and write in this project is in one file: [`quorum/memory.py`](quorum/memory.py). Four call sites carry the whole product.

| What breaks without it | Written at | Read at | Tier |
|---|---|---|---|
| **Agents duplicate each other's work.** A lens claims a (contract, lens) unit; a peer that finds it claimed does not scan it. This is the only coordination mechanism in the system. | [`claim_work`](quorum/memory.py#L91) | same call | HOT `state/` |
| **Quorum can never be reached.** Corroboration is accumulated across lenses, processes and sessions on the finding entity. A lens has no idea who else agreed with it; memory does. | [`record_sighting`](quorum/memory.py#L112) | [`swarm.py:74`](quorum/swarm.py#L74) | WARM `entities/` |
| **Nothing is ever recognised again.** A confirmed idiom becomes permanent swarm knowledge and is matched on sight in later sessions, on contracts the swarm has never read. | [`promote`](quorum/memory.py#L152) | [`known_pattern`](quorum/memory.py#L181) → [`swarm.py:79`](quorum/swarm.py#L79) | REFERENCE `reference/` |
| **Human corrections evaporate.** Retire a finding once and no later session reports that shape again. | [`retire`](quorum/memory.py#L196) | [`is_retired`](quorum/memory.py#L209) → [`swarm.py:64`](quorum/swarm.py#L64) | ARCHIVE `archive/` |

Every sighting, promotion, suppression and on-chain claim is also appended to the COLD journal ([`log`](quorum/memory.py#L144)), which is what makes a published claim auditable after the fact.

### The deletion test, as a command

The rules ask what happens if you delete the memory layer. Rather than assert an answer, Quorum ships it as a runtime flag. [`NoMemory`](quorum/memory.py#L225) implements the identical interface and forgets everything the instant it is written:

```console
$ quorum run --no-memory
```

Every claim succeeds, so agents duplicate work. Every sighting looks like the first, so corroboration never accumulates and quorum is never reached. Nothing is recognised from an earlier session. Retirements do not stick. Confirmed findings: **0**. Recalled: **0**. The core function is gone, and the same behaviour is asserted in [`tests/test_quorum.py`](tests/test_quorum.py).

---

## Coordination without a message bus

Quorum's agents are separate operating-system processes. They share one memory
file and nothing else: no queue, no broker, no RPC between them.

```console
$ quorum swarm --workers 3

3 agent processes, one memory, no message bus
  agent-1   scanned   9  stood down on  15 units a peer had already claimed
  agent-2   scanned   7  stood down on  17 units a peer had already claimed
  agent-3   scanned   8  stood down on  16 units a peer had already claimed

  24 units scanned in total, 48 skipped, in 0.7s
  no agent sent a message to any other agent. The HOT tier decided who did what.
```

Three processes, twenty-four units of work, each done exactly once. Claiming is
optimistic because a read-then-write across processes is not atomic: an agent
writes its own id into the claim, waits out the window in which a peer could be
writing too, then reads the claim back and stands down unless it sees itself
([`claim_work`](quorum/memory.py#L110)). Take the HOT tier away and all three
agents do all twenty-four units.

## Why a quorum

A single detector that reports everything it sees is noise. Six of them are six times the noise.

Quorum pairs its lenses two per risk, and each pair reasons from different evidence:

| Risk | Lens A | Lens B |
|---|---|---|
| `reentrancy` | `callorder-lens`: an external call precedes a state write in the same function | `guard-lens`: the function moves value out and carries no reentrancy guard |
| `unguarded-state-write` | `modifier-lens`: externally callable, writes storage, carries no modifier at all | `sender-lens`: writes a privileged-looking variable with no `msg.sender` check anywhere on the path |
| `unsafe-math` | `unchecked-lens`: arithmetic inside an `unchecked` block | `precision-lens`: a division evaluated before a multiplication |

Agreement is signal. Disagreement is kept as a candidate and never published. Run Quorum against audited production contracts and it mostly holds its tongue. On Aerodrome's Router, WETH9 and a Compound proxy it confirms nothing and files eleven candidates. That is the intended behaviour, not a failure to find bugs.

---

## Claims on Robinhood Chain

When a finding reaches quorum it stops being a private opinion. `quorum attest` writes the claim digest to Robinhood Chain as a self-addressed 0-value transaction. The first claim was written to Base before the token existed, with `QUORUM1`-prefixed calldata:

```console
$ quorum attest
signer 0xf9946775891a24462cD4ec885d0D4E2675C84355  balance 0.000500 ETH
  claimed on Base FriendtechSharesV1.sol:buyShares:reentrancy
    https://basescan.org/tx/0xa648821d91093df770b72c60be56834d069c9355c785e6195183e911f00bf713
```

A live claim, block 51138878. It can be read back and checked against the evidence that produced it:

```console
$ quorum verify 0xa648821d91093df770b72c60be56834d069c9355c785e6195183e911f00bf713

claim on Base  block 51138878  2026-09-10T19:05:03+00:00
  published by 0xf9946775891a24462cD4ec885d0D4E2675C84355
  digest       0xfd7d5ec6e350aa28f160c2d3cf60d3faf4b52d8f7280bfe9f665ce1809042721

  the evidence for this claim is still in memory
    FriendtechSharesV1.sol:buyShares:reentrancy
    corroborated by guard-lens  (recall)
  digest recomputed from memory matches the chain
```

The digest commits to the risk, the idiom signature, the contract, the function and the exact set of lenses that corroborated it ([`chain.py`](quorum/chain.py)). The finding itself never leaves the machine. Sibyl Memory is local-first and so is this. What goes on chain is a timestamped, verifiable claim that *this swarm knew this shape at this block*, which is what a disclosure timeline actually needs. The transaction hash is written back onto the finding entity in memory, so the claim and its evidence stay joined.

The signing key is read from the process environment at call time. It is never logged, printed or written to disk.

### Publishing costs. Scanning does not.

The claims above form a public registry of "this swarm knew this bug shape at this block". A public registry that is free to write to fills with junk, so writing to it has a cost, and the cost is destroyed rather than paid to anyone: each claim burns **100,000 QUORUM** through the token contract's own `burn(uint256)` on Robinhood Chain before the claim is written to the same chain, and the claim's calldata (`QUORUM2` shape) carries the burn's transaction hash. `quorum verify` checks both halves: the digest on chain, and that the burn it points at is a real burn of at least the fee by the same signer. Burn and claim share one chain, so one RPC verifies both. A claim whose fee was never burned does not verify.

The first claim at the current fee, 2026-09-12. (The launch claim at the 1,000 fee, claim `0xacd123…efb0` at block 60748972 with burn `0x76da2f…d5d7`, came 22 minutes earlier and still verifies.)

```console
$ quorum attest --limit 1
signer 0xf994...4355  0.002358 ETH on Robinhood Chain  100,830 QUORUM on Robinhood Chain
each claim burns 100,000 QUORUM before it is written. Scanning is free; publishing is not.
  burned 100,000 QUORUM
    https://robinhoodchain.blockscout.com/tx/0x2005d3b84a3286980ff134d0641d120e7859e13568abf003e393300ac3c9b34a
  claimed on Robinhood Chain FriendtechSharesV1.sol:buyShares:reentrancy
    https://robinhoodchain.blockscout.com/tx/0xb999d218981ad9985b587da6c4017ae7dc8557ef702e27c9bbc9ca4f68bf1655

$ quorum verify 0xb999d218981ad9985b587da6c4017ae7dc8557ef702e27c9bbc9ca4f68bf1655
claim on Robinhood Chain  block 60762176  2026-09-12T02:46:55+00:00
  published by 0xf9946775891a24462cD4ec885d0D4E2675C84355
  digest       0xfd7d5ec6e350aa28f160c2d3cf60d3faf4b52d8f7280bfe9f665ce1809042721
  fee burned   100,000 QUORUM on Robinhood Chain, block 60762150, by the same signer
  ...
  digest recomputed from memory matches the chain
```

The burn is saved to memory the moment it lands, before the claim is sent, so if the claim transaction fails the next `quorum attest` reuses that burn instead of paying a second fee.

Once a claim is paid, its owner can **reveal** the pattern behind it, and any other swarm can **import** it. Run live the same day, the import into a memory database that had never seen anything:

```console
$ quorum reveal FriendtechSharesV1.sol:buyShares:reentrancy      # discloses the claimed fields on chain (QUORUM3)
  revealed on Robinhood Chain FriendtechSharesV1.sol:buyShares:reentrancy
    https://robinhoodchain.blockscout.com/tx/0x7556ec748f8ffb9e2ca5809c4383e407f4affb9b847124c0d33205281e905f32

$ quorum --db fresh.db import 0x7556ec748f8ffb9e2ca5809c4383e407f4affb9b847124c0d33205281e905f32   # someone else's machine
reveal reentrancy  reentrancy:97d18d17cfa4494a  by 0xf9946775891a24462cD4ec885d0D4E2675C84355
  ok  digest matches the claim
  ok  revealed by the claim's signer
  ok  claim fee of 100,000 QUORUM burned
  imported into REFERENCE: the swarm will recognise this idiom on sight
```

An import checks three things and refuses if any fails: the revealed fields hash to the claim's digest, the reveal came from the claim's signer, and the claim's fee was burned. So a pattern nobody paid to publish never enters anyone's memory. That is the whole job of the token: it is the cost of being listened to by other people's swarms. Everything else, `run`, `swarm`, `recall`, `retire`, the memory tiers, the `--no-memory` test, has no token in it, and [`tests/test_token.py`](tests/test_token.py) asserts that the scanner modules never touch it.

Token: `QUORUM` on Robinhood Chain (chain id 4663), contract [`0xa6452Fd7134218f62056a304eaf501F8714A26b9`](https://robinhoodchain.blockscout.com/address/0xa6452Fd7134218f62056a304eaf501F8714A26b9). The first claim (Base, block 51138878) predates the fee and the move to Robinhood Chain; the first paid claim is the one above; `quorum verify` looks on Robinhood Chain first, then Base, and reads it back as a v1 claim with no burn to check. `QUORUM_CHAIN_ID` can point new claims at any chain in `chain.CHAINS`; the fee burn is always on Robinhood Chain, where the token is. The fee was 1,000 QUORUM at launch and is 100,000 from Robinhood Chain block 60761164 (`chain.FEE_SCHEDULE`); a burn is judged against the fee in force at its own block, so claims paid at the launch rate keep verifying.

---

## Run it

Python 3.10 to 3.13. If `python3 -m venv` fails on your machine, the `uv` path below avoids it entirely.

```bash
git clone https://github.com/Yonkoo11/quorum && cd quorum

python3 -m venv .venv && .venv/bin/pip install -e .   # or:
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e .

# pull real verified source from Base mainnet (no API key needed)
.venv/bin/quorum fetch 0xCF205808Ed36593aa40a44F10c7f7C2F67d4A4d4 \
                       0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43 \
                       0x4200000000000000000000000000000000000006

.venv/bin/quorum run --targets fixtures/*.sol   # the swarm learns
.venv/bin/quorum run                            # a fresh session recognises
.venv/bin/quorum recall                         # what it knows, and how it knows it
.venv/bin/quorum swarm --workers 3              # three processes, one memory
.venv/bin/quorum verify <tx>                    # check a claim against memory
.venv/bin/quorum recall --since 2026-09-10T00:00:00+00:00   # what it learned since
.venv/bin/quorum run --no-memory                # the deletion test
.venv/bin/python -m pytest tests -q             # 19 tests
```

`quorum attest` additionally needs `DEPLOYER_PRIVATE_KEY` in the environment, gas on Robinhood Chain, and the claim fee in QUORUM. `QUORUM_RPC` overrides the public Robinhood Chain endpoint; `BASE_RPC` overrides the public Base endpoint used only to read the first claim.

Commands: `fetch`, `run`, `swarm`, `recall [--since]`, `retire <key> --reason`, `attest`, `verify <tx>`, `reveal <key>`, `import <tx>`, `status`.

---

## What this is not

- **Not a vulnerability scanner that proves exploits.** Quorum publishes *corroborated idioms worth review*, not confirmed vulnerabilities. A quorum means two independent lenses agreed on a shape, nothing more. The Friend.tech recall above is a pattern match on a call idiom, not an allegation about that contract.
- **The lenses are deliberately simple.** They are regex-and-brace-matching heuristics over source text, not a compiler front end. The point of this project is the coordination and memory layer; the lenses are the honest minimum needed to have something real to coordinate about.
- **The fixtures in `fixtures/` are vulnerable on purpose** and are not deployed anywhere.

## Built with

[Sibyl Memory](https://github.com/Sibyl-Labs/Sibyl-Memory) (all five tiers, load-bearing) · Base mainnet (verified target source via Blockscout) · Robinhood Chain (token, fee burn and claims via `web3.py`) · MIT licensed.
