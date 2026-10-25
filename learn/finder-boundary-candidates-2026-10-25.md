# Finder note: boundary candidates are the ones worth proving (2026-10-25)

Source: the ARSEN workshop, a recorded audit-method talk. Reviewed in full against our pipeline.
Full review lives in the bughunter repo; this note is only the part that touches Quorum.

## The one thing it says that matters here

Quorum proves; it does not hunt. The method in the talk is a hunting method, so almost none of
it applies to us. The single point that does: the bugs that are worth an execution proof live at
boundaries, not inside one function. The talk's own three paid bugs are all boundary bugs — a
cross-chain message dropped by an uncaught error leaving a sequencer stuck, a perps position
opened already below liquidation (a check present on update, absent on open), a cross-contract
call whose failure semantics the caller assumed wrong.

That is exactly the class Quorum is built to settle. A boundary bug's whole claim is "these two
components disagree about what is guaranteed across the seam," and the only honest way to resolve
that is to fork at the block it was live and run the attack. A single-function arithmetic claim a
reader can often settle by reading; a cross-contract or cross-chain or platform-semantics claim
usually cannot be, which is where prove-by-execution earns its keep.

## What this implies for the finder, and what I deliberately did not do

The finder stage (`prove/hunt.py`, finders in `bench/stream.py` `CONTESTANTS`) proposes the
candidate (contract, function, one-line attack) tuples the prover then settles. The implication
is that a finder should surface boundary candidates: cross-contract calls, cross-chain or bridge
messages, and assumptions the in-scope code makes about its platform (gas, revert vs bounce
semantics, sequencer liveness, finality). Those convert into provable hypotheses more often than
a lone function body does.

I did **not** change any finder prompt. The finders are benchmarked, and their blind wrong-rate
in `bench/STREAM.md` is the trust moat of this project. Editing a finder prompt silently would
invalidate that number without anyone noticing. If we adopt a boundary-biased finder, the cost of
doing it honestly is a re-run of the blind benchmark so the published wrong-rate still describes
the finder we ship. That is a deliberate decision for later, not a quiet edit now.

Nothing here was sent anywhere.
