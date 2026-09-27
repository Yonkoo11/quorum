# For the community manager: the education direction, and posts you can use

This is everything you need to run Quorum's education/protection content, in plain English. Nothing
here needs you to read code. Two parts: **the direction** (what we're doing and the one rule that
protects it), and **ready-to-post copy** for the first two pieces.

---

## Part 1 — The direction, in plain words

Quorum hunts bugs in crypto projects. Alongside that, we protect and educate the community against
scams and hacks. But we do it in a way nobody else does, and that difference is the whole brand:

> **We show, we don't assert. Every hack we talk about, we can prove — we actually run the attack and
> show the money move. If we can't prove it, we don't post it.**

Most "scam awareness" accounts just make claims and scare people. We're the opposite: pick anything we
say, and you can watch it happen for real. That's the trust we're building.

**What this means for you when you post:**
- ✅ We teach real, named cases (real projects, real dates, with proof anyone can re-run).
- ✅ We can teach general safety too (poisoned addresses, wrong-network sends, blind signing) — but only
  by pointing at real documented losses, never made-up numbers.
- ❌ We never say "this is a scam" or "X is unsafe" unless we've proven it. No guessing, no fear-bait.
- ❌ No price talk, no "to the moon," no invented statistics. Our credibility is that every claim is real.

That one rule is the product. Keep to it and the education arm makes us more trusted. Break it once and
we're just another noisy account.

---

## Part 2 — The first two posts (ready to use)

Both are real August 2026 hacks. Both come with a proof anyone can run. Full write-ups live in this
folder: `unistreet-launch-drain.md` and `sandbox-delegate-mint.md`.

### Post 1 — "Anyone could drain everyone's money"

**Short version (X / Telegram):**
> A crypto launchpad in Aug 2026 held everyone's trading liquidity in one contract. One function let
> *anyone* pass it instructions to run — and nobody checked what those instructions were. So a normal
> user could tell it: "send everyone else's liquidity to me." No hack tools. No admin key. Just a call
> anyone could make.
>
> We didn't just read the code. We ran the attack on a copy of the real chain and drained a real pool.
> The proof is public — you can run it yourself.

**The lesson to add:** if a contract runs instructions you hand it using its own powers, it has to check
what those instructions do. "Audited" isn't the same as "someone proved this exact function is safe."

### Post 2 — "Anyone could mint a million tokens"

**Short version (X / Telegram):**
> A well-known token's cross-chain version got drained in Aug 2026. An attacker tricked the token into
> making *them* the trusted operator, then rewrote the rules so their own say-so was enough to approve a
> fake transfer. The token minted 1,000,000 tokens straight to them.
>
> Here's the wild part: a professional auditor read this code and called that path *safe* — because the
> obvious door was locked. It wasn't safe. The attack used a different door. Only *running* it proved
> the auditor wrong. That's why we prove instead of assert.

**The lesson to add:** "audited by a top firm" did not catch this. A human read it and got it wrong. The
only thing that caught it was running the attack. When someone says "it's safe," ask: *safe how — did
someone prove it, or just read it?*

---

## How to talk about the proof (without being technical)

You don't need to explain the code. Just say, honestly:
- "We ran the actual attack on a copy of the real blockchain, at the moment the bug was live."
- "The attacker's balance went up by a real amount — we show the number."
- "Anyone can re-run it and get the same result. It's not our word, it's a fact you can check."

The proofs are in the project's `prove/proofs/` folder and the write-ups are in `learn/`. If someone
technical asks for it, send them there.

## The cadence

These aren't one-offs. Every time we hunt and prove a new hack, it becomes a new card like these. So the
education feed is fed by the bug-hunting — you'll get a steady stream of real, proven cases to post,
each with the same shape: what happened, how, proof, lesson.

## When you're unsure

If you're ever about to post a claim you can't point to a proof or a real source for — don't. Ask first.
That one habit is what keeps this whole thing credible.
