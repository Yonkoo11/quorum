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

## Claims on Base

When a finding reaches quorum it stops being a private opinion. `quorum attest` writes the claim digest to Base mainnet as a self-addressed 0-value transaction with `QUORUM1`-prefixed calldata:

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

---

## Run it

```bash
git clone https://github.com/Yonkoo11/quorum && cd quorum
python3 -m venv .venv && .venv/bin/pip install -e .

# pull real verified source from Base mainnet (no API key needed)
.venv/bin/quorum fetch 0xCF205808Ed36593aa40a44F10c7f7C2F67d4A4d4 \
                       0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43 \
                       0x4200000000000000000000000000000000000006

.venv/bin/quorum run --targets fixtures/*.sol   # the swarm learns
.venv/bin/quorum run                            # a fresh session recognises
.venv/bin/quorum recall                         # what it knows, and how it knows it
.venv/bin/quorum swarm --workers 3              # three processes, one memory
.venv/bin/quorum verify <tx>                    # check a Base claim against memory
.venv/bin/quorum recall --since 2026-09-10T00:00:00+00:00   # what it learned since
.venv/bin/quorum run --no-memory                # the deletion test
.venv/bin/python -m pytest tests -q             # 7 tests
```

`quorum attest` additionally needs `BASE_RPC` and `DEPLOYER_PRIVATE_KEY` in the environment.

Commands: `fetch`, `run`, `swarm`, `recall [--since]`, `retire <key> --reason`, `attest`, `status`.

---

## What this is not

- **Not a vulnerability scanner that proves exploits.** Quorum publishes *corroborated idioms worth review*, not confirmed vulnerabilities. A quorum means two independent lenses agreed on a shape, nothing more. The Friend.tech recall above is a pattern match on a call idiom, not an allegation about that contract.
- **The lenses are deliberately simple.** They are regex-and-brace-matching heuristics over source text, not a compiler front end. The point of this project is the coordination and memory layer; the lenses are the honest minimum needed to have something real to coordinate about.
- **The fixtures in `fixtures/` are vulnerable on purpose** and are not deployed anywhere.

## Built with

[Sibyl Memory](https://github.com/Sibyl-Labs/Sibyl-Memory) (all five tiers, load-bearing) · Base mainnet (verified source via Blockscout, claims via `web3.py`) · MIT licensed.
