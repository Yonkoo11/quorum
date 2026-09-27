# A token let anyone mint a million tokens to themselves

**Sandbox (SAND) OFT · Base · August 2026 · proven, not asserted**

## What happened

SAND, a well-known token, had a cross-chain version (an "OFT") that could move between blockchains. To
move tokens between chains, the token trusts a messaging system and a "delegate" that configures how
incoming messages are verified. An attacker made the token appoint **them** as that delegate — and then
rewrote the rules so that the attacker's own say-so was enough to verify a message. They forged a
message that said "mint SAND to me," and the token minted it.

**1,000,000 SAND, out of thin air, to an ordinary wallet.**

This one is worth dwelling on: a careful auditor reading the code first called this route *safe*,
because the obvious door (`setDelegate`) is owner-only. It wasn't safe. The attack got in through a
different door, and only running it proved the auditor wrong.

## How it worked

The token had a helper, `approveAndCall(target, amount, data)`, that made **the token itself** call
`target` with `data`. Its only guard was that the first word of `data` equalled the caller:

```solidity
approveAndCall(target, amount, data);   // makes OFTSand call target.call(data), as the token
// guard: the first ABI word of `data` must equal msg.sender, and data.length >= 68
```

The attacker pointed it at the messaging endpoint and passed `setDelegate(attacker)`. That function's
only argument *is* the attacker's address — so the guard ("first word equals the caller") passed. Now
the attacker was the token's delegate. As delegate, they set themselves as the only required verifier,
self-attested a forged incoming transfer, and let the token mint SAND straight to them.

The obvious guard on the obvious function was real. The attack simply didn't use the obvious function.

## The proof

[`../prove/proofs/SandboxOFT.t.sol`](../prove/proofs/SandboxOFT.t.sol) forks Base at the block the bug
was live and runs the whole chain as an unprivileged wallet:

```
[PROOF] attacker gained 0xac53…2DcF (SAND) 1000000000000000000000000   →  +1,000,000 SAND
```

Reproduces with the model gone, no faked state, no owner or role impersonated. Run it:

```bash
export BASE_RPC_URL=https://base.drpc.org
cd prove/scaffold && forge test --match-path ../proofs/SandboxOFT.t.sol -vv
```

## The lesson

**A guard that checks the shape of a call is not a guard on what the call can do.** Checking that "the
first word equals the caller" says nothing about the target or the rest of the payload. And a
function being "only-owner" protects that function, not every other path to the same power.

- **If you're a builder:** any function that makes your contract call an arbitrary target with
  arbitrary data is a loaded gun. A partial check on the calldata is not a safety catch. Assume an
  attacker will reach every privileged setting your contract can touch, through whatever door is open.
- **If you're a user:** "audited by a top firm" did not catch this — a human read the code and called
  the route safe. The only thing that caught it was running the attack. When you hear "it's safe,"
  the honest question is *"safe how — did someone prove it, or just read it?"*
