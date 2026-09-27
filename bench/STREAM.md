# The stream: every tool, scored on hacks nobody tuned for

Every other corpus in this folder stopped being a test the day a lens was built from its misses.
This one is built so that cannot happen. [`labels/stream-freeze.txt`](labels/stream-freeze.txt)
lists the 861 proofs of concept in DeFiHackLabs at commit `0520ddb` (2026-09-27); only a hack
reproduced after that is admitted, and it is scored before anyone here reads why it happened.

```
python bench/stream.py intake  <DeFiHackLabs clone> <workdir>
python bench/stream.py predict <contestant> <workdir>        # regex-v0 · generic · v4-1pass
python bench/stream.py label   <DeFiHackLabs clone> <workdir>
python bench/stream.py score                                 # reproduces from the saved files
```

Three roles, each kept from what it must not see, with the order enforced in code and tested
([`tests/test_stream.py`](../tests/test_stream.py)): intake passes on the victim's address and
nothing else; a contestant sees only the victim's source, renamed `target.sol`; the labeller reads
the root-cause note and never a prediction. A prediction is refused once a label exists, a label
waits for every contestant, and a prediction written after its label is not scored. Scoring is by a
model judge (same root cause, related code, or none), cached per verdict so a re-score is free and
cannot drift; every judged hit on the first set was also read by hand.

## The development set, not the stream

The stream has no entries yet: nothing has been reproduced since the freeze. Until it does, the
harness runs on the nine 2026 hacks with readable victim source. **These are in-sample.** Two lenses
were built from their misses and their labels were written by hand before this harness existed.
Treat this table as a calibration of the harness, not as a result.

| contestant | hacks run | root cause found, any tier | exact root cause | exact, top tier only | items written | items on the root cause | cost |
|---|---|---|---|---|---|---|---|
| regex-v0 | 9 | 3 | 1 | 1 | 10 | 5 | $0.00 |
| generic | 9 | 6 | 3 | 3 | 12 | 8 | $2.55 |
| v4-1pass | 9 | 9 | 7 | 5 | 130 | 28 | $75.76 |

An item that is not on the labelled root cause counts against its tool even when it may be a real, different bug; nobody has checked those yet.

Run 2026-09-27. Contestants: `regex-v0` is Quorum's ten lenses at v0.7.1 under the two-lens rule;
`generic` is one prompt to Claude (Opus 5.5) reading the file; `v4-1pass` is Pashov's
[solidity-auditor](https://github.com/pashov/skills) at tag `v23092026`, one pass of its twelve
agents. All three ran headless with web tools off. Costs are the CLI's own accounting.

What it says, with the caveats attached:

- **v4 finds the root cause of every one of the nine**, the exact one for seven, and five of those
  in its top tier. The regex engine finds the exact one once. The gap is not close.
- **Where v4 puts the truth matters.** Two of its seven exact hits were not in its top tier: one
  below its confidence threshold, one in its unscored leads (ORB). A reader who stops at the
  findings list misses them.
- **v4 writes a lot.** 130 items for nine contracts, 28 of them on the labelled root cause. The
  other 102 count against it here, but they are not known to be false: a hand review of an earlier
  v4 run called 7 distinct unlabelled loss paths real. Precision is unmeasured until those are
  proved or disproved by execution, which is the next stage of Quorum, not this file.
- **It varies between runs.** An earlier single v4 scan of all ten files together found the right
  mechanism in six of nine; one scan per file found all nine, at 2.3 times the cost ($75.76 against
  $32.76).
- **n = 9.** Nothing here is a rate. The stream is how it becomes one.

## Validation: the pipeline run blind on hacks the operator had never read

Run 2026-09-28. Before any real post-freeze hack existed, the whole automated chain was exercised on
**two 2026-09 hacks the operator had never examined** and that are not among the classified set — a
sandbox run in a separate ledger, not real stream entries. The operator never read either root cause:
intake and labelling are model steps that read the proof of concept, contestants see only the victim
source, and predictions were frozen before the labels were written. Both hacks are dated after the
models' training cutoff, so contamination is low.

| contestant | hacks | exact root cause | items written | items on target | cost |
|---|---|---|---|---|---|
| regex-v0 | 2 | 0 | 0 | 0 | $0.00 |
| generic (one prompt) | 2 | **2** | 4 | 2 | $0.63 |
| v4, one pass | 2 | **2** | 23 | 7 | $14.20 |

Both AI contestants named the exact root cause of both hacks (`GaslessReservoirEnabler` and an
`InternetToken` liquidity unifier, both access-control); the regex engine caught neither. On this
pair the single generic prompt matched v4's recall at a twentieth of the cost and a fifth of the
noise — a real out-of-sample signal, though n = 2 proves nothing on its own.

**What this shows and doesn't.** It shows the automated chain works end to end on cases the operator
did not know — and it earned its keep by breaking twice on real bugs (a label answer wrapped in prose,
and a JSON-array-vs-object parse) that are now fixed and tested, so the daily cron would have hit them.
It does **not** show the live stream running on novel events: these hacks existed before the freeze, so
they are "unread by the operator," not "the future." The real stream still fills only as new hacks are
reproduced after the freeze date.
