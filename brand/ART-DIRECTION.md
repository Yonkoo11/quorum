# Art direction: the Quorum mark

## The lazy idea, named and forbidden

A security tool's first idea is a shield, a padlock, a magnifying glass or an eye. All four are forbidden. So is a leaf: a fat vesica with a green fill reads as a leaf or an eye at a glance (the founder card shows the risk). So is any chart, node graph, hexagon or check mark.

## The signature element

Two equal circles, drawn in ink, overlapping. The overlap (the vesica) is filled solid green. Nothing else. It encodes the product exactly: two independent readings, one finding, and the finding is the only thing that gets colour. It is already the one decoration the brand uses on every card and page, so the job is to fix it, not replace it.

The transformation the mark tells: two readings come from different sides, and where they agree something solid appears. On the site the green empties when memory is off; the static mark is the "agreed" state.

## Geometry (one master, everything derived)

- Two circles of radius `r`, centres `1.06 r` apart (the site's proportion, the narrower of the three in use); the favicon, and only the favicon, uses `0.96 r` for the reason given under deliverable 4. This keeps the vesica taller than it is wide, so it reads as an overlap of two things, not as a leaf or an eye. Vesica width = `0.94 r`, height = `1.69 r`.
- Stroke = `0.20 r`, ink, square caps and joins where any appear (none do), no transparency.
- The vesica fill sits under the strokes (the ink arcs cross over the green), which is how the cards draw it.
- Master viewBox is the tight box of the two circles plus half a stroke of margin.

## Material and colour

Flat. Ink on paper. No gradient, no glow, no shadow, no bevel, no inner highlight. Green only in the vesica. Two grounds: paper `#f3eee4` with ink `#121212` strokes; dark `#0d100d` with `#e9ede9` strokes. Green `#3fb950` on both.

## The deliverables and the rule for each

1. **Mark** (`mark.svg`, light and dark): the master, no tile.
2. **Wordmark lockup** (`lockup.svg`, light and dark): mark, then "QUORUM" in Archivo Black, uppercase, tracking -0.02em, converted to outlines so the file needs no font. Mark height = cap height of the wordmark; gap = 0.6 of the cap height. This matches the site bar.
3. **App icon** (`icon.svg` and PNG at 1024/512/256/180/64): a square tile, paper or ink, corner radius 22% of the side (the one radius the style allows), the mark centred at 62% of the tile width. Strokes stay ink on paper and paper on ink.
4. **Favicon** (`favicon.svg`, `favicon.ico` 16/32/48): the mark on a square with no radius. This is the one export with geometry of its own, because a 16 px tab is the size floor and the master proportions do not survive it. The stroke is thickened to `0.30 r`, the mark fills 94% of the box, and the centres sit `0.96 r` apart instead of `1.06 r`. Measured on rendered pixels (`logo-forge/rounds/round1/zoom-favicon.png`, `explorations/round2-*.png`): at `0.20 r` the stroke goes grey and at `0.34 r` it crushes the green to two pixels; at the master overlap the vesica loses its points below about 24 px and the ink arcs, which cross over the green, leave a two-pixel bar, so the rings become the subject and the pair reads as spectacles, which is the eye and aperture family this page forbids. `0.96 r` keeps the green a mass at 16 px and the vesica still taller than it is wide; `0.86 r` tips into the single-eye reading round 1 rejected. Verdicts in `CRITIQUE.md`. Every other export stays on the master geometry. The SVG favicon switches to the dark tile under `prefers-color-scheme: dark`; the .ico is the paper tile.
5. **X avatar** (PNG 800x800, light and dark): the tile without the radius, because X crops to a circle; the mark sits inside a safe circle of 80% of the width so nothing is cut.
6. **Social square** (1200x1200) with the lockup, for places that ask for one.

## Composition rules

Centred, generous margin, high-contrast silhouette. The silhouette is the union of two discs; that alone must be recognisable in a dock or a tab. No secondary shapes.

## Forbidden list, as a gate

No text, letters or numbers inside the mark or icon. No gradient, glow, sparkle, shadow, bevel, glass. No rainbow or second accent. No shield, padlock, key, magnifying glass, eye, iris, leaf, camera, aperture, hexagon, node graph, brain, chip, cube, check mark. No translucent strokes. No near-black rounded tile with thin strokes (the current file). No monospace or lowercase wordmark.

## Dual legibility target

At 16 px: two ink rings and one green lens, distinct from every other tab icon on the bar. At 1024 px: the same three shapes, with the ink arcs crossing cleanly over the green and nothing else to look at.

## Route

Vector. The mark is three primitives. Authored as SVG by hand, rendered natively at every size with headless Chrome, type outlined with fontTools. Nothing upscaled, no image model.
