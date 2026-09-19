# Round 1 critique (2026-09-16), rubric: reference/critique-personas.md

### v1-narrow (overlap 1.06 r, stroke 0.20 r) — Grade: A-
- Concept fit: two rings, one green overlap; reads as agreement, not as an eye or a leaf; the category is not security-cliché.
- Brand compliance: one accent, ink and paper only, no text, no gradient, no forbidden shape. Pass.
- Craft: clean silhouette, arcs cross the green without mush, tile radius the only curve besides the circles.
- Legibility: crisp at 32 and up on both grounds; at 16 the 0.20 r stroke goes grey (see zoom-favicon, row f-a), so the favicon needs its own stroke.
- Ownability: the narrow vesica is the distinctive part; nobody else's rings overlap this way.
Verdict: the idea is right; the one flaw is at the 16 px floor and is execution-level (a heavier stroke for that size only).

### v2-wide (overlap 0.90 r, stroke 0.20 r) — Grade: B
- Concept fit: same idea, but the fat vesica drifts toward a leaf or an eye at small sizes; this is the proportion the cards use today.
- Brand compliance: pass.
- Craft: fine.
- Legibility: the green survives 16 px slightly better than v1 because it is wider, but the rings crowd.
- Ownability: weaker; a wide vesica is the generic Venn look.
Verdict: idea right, proportion wrong; fixing it produces v1.

### v3-narrow-heavy (overlap 1.06 r, stroke 0.26 r) — Grade: B
- Concept fit: same.
- Brand compliance: pass.
- Craft: at 1024 the heavier ring crowds the green; the mark starts to read as two rings with a sliver rather than as a finding.
- Legibility: better than v1 at 16 px, which is exactly the job of a favicon variant, not of the master.
- Ownability: same as v1.
Verdict: the right stroke for the size floor, the wrong stroke for the master.

### Favicon candidates at the floor (zoom-favicon.png)
- f-a 0.20 r, 88%: strokes go grey at 16. Reject for the favicon.
- f-b 0.30 r, 94%: rings solid, green lens still a lens at 16, clean at 32, both grounds. **Pick.**
- f-c 0.34 r, 96%: green becomes a two-pixel sliver at 16; rings begin to merge.
- f-d 0.30 r, 94%, wide overlap: fatter green but the rings' overlap muddles at 16.

## Recommendation
Lock v1 as the master (overlap 1.06 r, stroke 0.20 r) for the mark, lockup, icon tile, avatar and social square. Favicon only: stroke 0.30 r, mark at 94% of the box, same overlap. Remaining work is execution: run the final export, replace the three inconsistent drawings on the site and the cards with the master geometry, and test the favicon in a real tab.

---

# Round 2 critique (2026-09-18): the 16 px test round 1 deferred

Round 1 ended with "test the favicon in a real tab" as remaining execution. That test had not been
run. It has now, natively at 16, 20, 24, 32 and 48 px through headless Chrome on both grounds —
renders in `../explorations/round2-*.png`, not upscaled.

## What the size ramp shows

The vesica keeps its points down to about 24 px. Below that the green loses its taper and becomes a
rounded bar, and at 16 px it is roughly two pixels wide. What is left at the size floor is two rings
with a sliver between them, which reads as **spectacles** — the same family as the eye and the
aperture that `ART-DIRECTION.md` forbids by name. The forbidden list did not catch it because the
shape only becomes that at the floor; the geometry is innocent at 48 px and guilty at 16.

This is the honest answer to why the mark can be correct everywhere and still feel wrong: the
favicon is the copy of it most people see most often.

## Candidates at 16 px (`round2-favicon-candidates.png`, dark tab strip)

| # | overlap / stroke / fill | verdict |
|---|---|---|
| a | 1.06 / 0.30 / 0.94 — **shipped today** | green is a 2 px bar, dimmer than the rings on dark. The rings are the subject and the finding is the decoration, which inverts the product. |
| b | 0.96 / 0.30 / 0.94 | green is ~3 px and clearly the subject on both grounds; rings still read as two circles. **Pick.** |
| c | 0.86 / 0.30 / 0.94 | green widest, but the pair starts reading as one eye with rings around it — the v2-wide failure round 1 rejected. |
| d | 0.96 / 0.36 / 0.94 | heavier rings squeeze the green back down. Worse than b. |
| e | 0.96 / 0.30 / 1.00 | good green, but the rings touch the tile edge and will look cropped in a tab. |

Head to head at `round2-favicon-ab.png`: a and b at 16 px native, light and dark.

## Recommendation, and the deviation it carries

Use **b** for the favicon only: overlap 0.96, stroke 0.30 r, mark at 94% of the box. Everything
else — mark, lockup, icon tile, avatar, social — stays on the master 1.06 / 0.20.

Round 1 locked the favicon as "stroke 0.30 r, mark at 94% of the box, **same overlap**". This
changes the overlap, so it is a deviation from a decision already made, not an execution detail.
**Applied 2026-09-19.** It was first recorded and not applied, on the reasoning that a geometry
change is a Checkpoint B call. That was the wrong read. Checkpoint B is where a human picks a
*direction*; this is a craft fix at the size floor, the art direction already grants the favicon
its own treatment, and round 1 locked "same overlap" without the 16 px evidence that round 2
produced. Evidence gathered after a decision is the reason to revisit it.

So: `FAVICON_OVERLAP = 0.96` is now a named constant in `logo-forge/build.py`, used only by the
favicon exports. The ten favicon files changed and nothing else — mark, lockup, icon tile, avatar
and social are byte-identical. The deviation from the round-1 lock is on the record in
`ai/DEVIATIONS.md`. Before and after at 16 px: `../explorations/round2-favicon-before-after.png`.

Reverting is one constant: set it back to 1.06 and re-run `build.py final`.

Honest limit: b reduces the spectacles reading at 16 px, it does not remove it. Two overlapping
rings at sixteen pixels will always carry some of it. The alternative that would remove it is a
favicon that is not the full mark — the vesica alone, or one ring and the lens — and nobody has
drawn those yet.


## The question round 2 left open, decided (2026-09-19)

Round 2 ended by saying that `0.96 r` reduces the spectacles reading at 16 px without removing it, and that
removing it needs a favicon that is not the full mark: the vesica alone, or one ring with the lens. Neither
was drawn, and neither should be.

The art direction forbids both by name already. A fat vesica filled green "reads as a leaf or an eye at a
glance", which is the first line of the forbidden list. One ring with the lens reads as a crescent or a C,
and it throws away the only idea the mark carries: two readings, and the overlap is the finding. A favicon
that says something different from the mark is not a favicon for this mark.

So the answer is that some of that reading is the price of the idea at sixteen pixels, and the mark keeps
the idea. What `0.96 r` buys is the subject: the green stays the thing you see first. That is the part worth
fixing, and it is fixed. No round 3.
