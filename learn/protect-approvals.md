# The approval that keeps draining you

**A defensive habit · for anyone who holds tokens · not a contract bug — a trick on you**

> **Honest note up front:** the hack cards in this folder are bugs in a project's code, and we prove
> each one by running it. This one is different. It isn't a flaw in a contract — it's a permission
> *you* grant, that an attacker uses later. Quorum's scanner does **not** catch this, because there's
> no bug to find. We teach it because it's one of the most common ways ordinary people lose funds, and
> the fix takes two minutes.

## What an "approval" actually is

To let an app trade or spend your tokens, you sign an **approval**: permission for another address to
move that token out of your wallet. Most apps, to save you signing again later, ask for an **unlimited**
approval — permission to move *all* of that token, *forever*, until you take it back.

That permission doesn't expire. It sits in your wallet after you've forgotten the app existed. If the
address you approved is malicious — or a legitimate contract that later gets hacked — it can move those
tokens any time, without asking you again.

## How the money actually leaves

The common version isn't a clever exploit. It's a fake or lookalike site:

1. You land on a "claim your airdrop" / "migrate your tokens" / "connect to unlock" page.
2. It asks you to approve a token, or to sign a `Permit` (an off-chain signature that grants the same
   power with no on-chain transaction, so it doesn't even cost you gas).
3. Nothing obvious happens. You move on.
4. Minutes or weeks later, the approved address drains that token. You never signed anything else.

This is a documented, major category of theft (approval phishing and "wallet drainer" kits), tracked by
firms like Chainalysis. The point isn't a scary number — it's that the door was a permission you signed,
not a wall someone broke.

## What to do — today, and as a habit

**Now (two minutes):**
- Open an approval checker — **revoke.cash**, or Etherscan/Basescan's "Token Approvals" tab for your
  address. It lists every approval your wallet has out.
- Revoke anything you don't recognize, anything unlimited that you're done using, and anything tied to a
  site you no longer trust. Revoking is one small transaction.

**As a habit:**
- **Approve the amount you're spending, not "unlimited,"** when your wallet lets you edit it.
- **Use a hardware wallet** for anything you'd be upset to lose. It doesn't stop a bad approval, but it
  stops the far bigger category — key and seed-phrase theft.
- **Read what you're signing.** A `Permit` or `Approve` for a token you didn't mean to trade is a red
  flag. If a "claim" page wants approval over a token, ask why.
- **Simulate before you sign** where your wallet or an extension shows you the balance changes a
  transaction will cause. If it says a token leaves and nothing comes back, stop.
- **Re-check your approvals every so often,** the way you'd check a bank statement.

## The one line to remember

**An approval is a key you hand out, and it stays out until you take it back.** Give out as few as you
can, only as large as you must, and take back the ones you're done with.

---

*Where Quorum can and can't help: our engine proves bugs in contract code (the other cards here). It
can't tell you a site is a phishing site or that an approval is a trap — that's on you and your wallet.
The best thing we can do is make sure you know the habit. If you're ever unsure whether a contract or
approval is safe, ask in the community before you sign, not after.*
