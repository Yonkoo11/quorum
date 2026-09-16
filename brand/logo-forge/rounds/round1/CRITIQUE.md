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
