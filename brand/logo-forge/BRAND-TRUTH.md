# Brand truth: Quorum

Read from the codebase on 2026-09-16 (ai/style.config.md, docs/quorum.css, brand/post-*.html, brand/logo.svg, brand/wordmark.svg, docs/index.html). Nothing here is invented.

- **name:** Quorum. Wordmark set in Archivo Black, uppercase, ends with a period in headlines ("TWO LENSES. ONE FINDING.").
- **purpose:** finds bugs in smart contracts and reports one only when two separate readings agree, so fewer false alarms.
- **core_verb:** agree. Two independent lenses land on the same spot; the overlap is the only thing published.
- **metaphor:** two lenses, one finding. Two circles read the same code from different sides; where they overlap is the finding. The overlap is the product. Everything outside it is a candidate that is held back. On the site the overlap fills green when memory is on and empties when memory is off, so the mark is also the product's one live control.
- **palette:** paper `#f3eee4` (ground, light), ink `#121212` (strokes, text), green `#3fb950` (the overlap, the only accent; `#24772f` when green must be text). Dark ground `#0d100d` with ink strokes becoming `#e9ede9`. No other colour. No gradient, no glow, no transparency in strokes.
- **type:** Archivo Black 400 for the wordmark (shipped at docs/fonts/ArchivoBlack-Regular.woff2 and brand/fonts/*.ttf); IBM Plex Sans 500 for labels. Square corners everywhere; the only radius allowed is an app-icon tile.
- **constraints:** must read at 16 px (favicon, browser tab) and in a circle crop (X avatar); vector route only; no text inside the icon; no shield, padlock, magnifying glass, eye, leaf or camera reading; no near-black tile with translucent strokes (the current file, rejected by ai/style.config.md as the dark template).

## What exists today, and why it reads as average

The same mark is drawn three different ways:

| where | overlap (centre distance / radius) | stroke | ground |
|---|---|---|---|
| site bar, `docs/quorum.css` `.mark` | 18 / 17 = 1.06 | ink, 3.4 of a 38-high box | paper |
| cards, `brand/post-*.html` | 168 / 186 = 0.90 | ink, 22 of a 664-high box | paper |
| icon, `brand/logo.svg`, `docs/logo.svg`, `docs/icon-256.png` | 120 / 132 = 0.91 | green at 55% opacity, 14 of 512 | near-black rounded tile |

And `brand/wordmark.svg` sets the name in a green monospace lowercase that appears nowhere else. So the identity is the site's and the cards', and the icon and wordmark files are leftovers from before the direction was chosen. The rebuild fixes one geometry, one stroke rule, one ground rule, and derives every export from a single master.
