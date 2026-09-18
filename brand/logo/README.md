# The Quorum mark

Two equal circles in ink, overlapping. The overlap is filled green. That is the whole mark, and it is the product: two independent readings of the same code, and the only thing published is where they agree. On the site the green empties when memory is switched off, so the mark is also the product's one live control.

## Geometry

One master, everything derived. Radius `r`; centres `1.06 r` apart, so the overlap is taller than it is wide and reads as two things overlapping rather than as an eye or a leaf; stroke `0.20 r`, solid ink, the green under the ink. Paper `#f3eee4` with ink `#121212`; dark ground `#0d100d` with `#e9ede9`; green `#3fb950` on both. No gradient, glow, shadow or transparency anywhere. The only curve besides the circles is the app-icon tile's corner.

## Files

| file | use |
|---|---|
| `mark.svg`, `mark-dark.svg`, `mark-512.png` | the mark alone |
| `lockup.svg`, `lockup-dark.svg`, `lockup-1600.png` | mark and wordmark; QUORUM in Archivo Black, outlined, no font needed |
| `icon.svg`, `icon-dark.svg`, `icon-{1024,512,256,180,64,32,16}.png` | app icon on a tile, corner radius 22% |
| `favicon.svg` | one file for both tab themes (switches on `prefers-color-scheme`); stroke `0.30 r`, mark at 94% of the box, measured at 16 px |
| `favicon.ico` | 48, 32 and 16, paper tile, each rendered natively |
| `avatar-800.png`, `avatar-dark-800.png` | X and other circle crops; the mark sits inside the 80% safe circle |
| `social-1200.png` | a paper square with the lockup, for places that ask for one |

Every PNG is rendered at its own size by headless Chrome from the SVG; nothing is upscaled. Rebuild everything with:

```
/usr/bin/python3 brand/logo-forge/build.py final --overlap 1.06 --stroke 0.20
# the favicon does not take these: it has its own FAVICON_OVERLAP = 0.96 in build.py, because the
# vesica loses its points below ~24px and the green goes to a two-pixel bar at the master overlap
```

## How it was chosen

`brand/`: BRAND-TRUTH.md (what the codebase already said), ART-DIRECTION.md (the idea, the forbidden list, the rules), CRITIQUE.md (the verdicts, round 1 and the round 2 test at 16 px), explorations/ (round1/ with three geometries at every size, round2-* with the favicon at the size floor). `brand/logo-forge/` keeps build.py and the raw round-1 renders. Paths moved 2026-09-18 to the ones ~/System/scripts/skill-contracts.txt checks. The previous files drew the same idea three different ways; this is the one way.
