## The confirmations, read by hand

All 36 were opened and read in the source. None is a bug an audit missed.

Twenty-four of them do not involve the consistency lens, and they are what is left of the 28 read one by one
before that lens existed. Those 28 were: nine `unchecked` arithmetic bounded by a checked operation beside it,
seven a setter that copies a value out of a trusted contract, four vendored Uniswap libraries whose wrap is the
design, four payouts that zero the balance before they pay, two calls to a contract fixed in the constructor,
one a stateless multicall helper that holds no funds, and `ReferralRegistry.becomeReferrer`, below. Four have
since gone on their own: a struct's fields are not contract state, the declaration reader used to think they
were, and a local sharing a field's name read as a state write.

The twelve the consistency lens takes part in were read this run. Two are the labelled findings above. The other
ten are false, in four shapes:

- **Write-once on a fresh id** (morpheus `createBuilderPool`, twice, and merkl `addReferralKey`). The id is a hash of a name the caller supplies, and an existence check refuses to overwrite anything, so an arbitrary caller can only write a slot nobody was using.
- **An in-body check the modifier reading cannot see** (ekubo `transferFrom`, merkl `increaseTokenBalance`, bitvault `urgentRedemption`). An ERC20 allowance check, a `safeTransferFrom` that makes the caller pay for what they credit, and a shutdown-plus-balance check. The rule that skips a function testing its own caller wants `msg.sender` inside one `require`; these spread it over several statements.
- **The caller writes their own row** (blackhole and hybra `delegate`). `delegate(address)` calls `_delegate(msg.sender, delegatee)`, so the only slot written is the caller's. The rule that drops `v[msg.sender]` writes reads one line and cannot follow `msg.sender` into a helper's parameter.
- **A value no caller can influence** (morpheus `distributeRewards` writes `block.timestamp`, liquid-ron `pruneValidatorList` writes a constant `false` for a validator already fully unwound).

The first and the last are the two shapes worth a rule next, and like every other rule here they will be built
against a labelled corpus before they are measured on this one.

`ReferralRegistry.becomeReferrer` in the Merkl contest is still worth its own line, because it is not quite a
false alarm. It pays ether to an address any caller can register, and pulls a caller-chosen token, before it
writes its state, with no guard anywhere in the file despite a comment that claims one. The audit did not report
it because the file is named in that contest's out-of-scope list. So the shape is real and nobody was looking at
it. It is not counted as a true positive here, because this benchmark scores against what the audits found, and
nothing was verified beyond reading it.

