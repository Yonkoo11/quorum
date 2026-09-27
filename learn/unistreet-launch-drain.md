# A launchpad let anyone drain everyone else's liquidity

**Unistreet Launchpad · Ethereum · August 2026 · proven, not asserted**

## What happened

A token launchpad held the liquidity for every token it launched — everyone's trading pool sat inside
one factory contract. A single function, `launch()`, let anyone create a new token. But the same call
also let the caller hand the factory a list of raw instructions to run. Nothing checked what those
instructions were. So an attacker called `launch()` and, in the same breath, told the factory to pull
**every earlier launch's liquidity out and send it to them.**

No password, no admin key, no special access. Just a normal call anyone could make.

## How it worked, in one line

`launch()` forwarded two attacker-written blobs straight into the position manager as the factory:

```solidity
calls[0] = initCalldata;      // whatever the caller passed
calls[1] = modifyCalldata;    // whatever the caller passed
IPositionManager(POSITION_MANAGER).multicall(calls);   // run as the factory, which owns every pool's LP
```

Because the factory owned every launch's liquidity NFT, and it ran the caller's instructions **as
itself**, the caller could say "decrease this position's liquidity to zero and send the tokens to me"
for any pool it wanted. The instruction shape was identical to the factory's own `harvest()` — the
attacker just aimed it at other people's positions.

## The proof

[`../prove/proofs/UnistreetLaunchpad.t.sol`](../prove/proofs/UnistreetLaunchpad.t.sol) forks Ethereum
at the block the bug was live and runs the attack as an ordinary wallet. It drains a real earlier
launch's pool:

```
[PROOF] attacker gained 0xC02a…6Cc2 (WETH) 7209570881911319   →  +0.0072 WETH
```

It reproduces to the exact wei on two independent public nodes, with no faked state and no role
impersonated. Run it yourself:

```bash
export ETHEREUM_RPC_URL=https://eth.drpc.org
cd prove/scaffold && forge test --match-path ../proofs/UnistreetLaunchpad.t.sol -vv
```

## The lesson

**If a contract runs instructions you hand it, using its own powers, it must check what those
instructions do.** "Forward the caller's calldata" is one of the most dangerous patterns in a
contract that custodies other people's funds — the caller borrows the contract's authority.

- **If you're a builder:** never pass unchecked caller data into a call your contract makes as itself,
  especially when your contract holds funds or NFTs that belong to others. Whitelist the exact actions.
- **If you're a user:** a launchpad or vault that pools everyone's funds in one contract is only as
  safe as its least-checked function. "It's audited" is not the same as "this specific function was
  proven safe." Ask whether anyone has actually run the attack, not just read the code.
