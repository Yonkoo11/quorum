"""Draw the Quorum mark from one geometry and export every size natively.

    /usr/bin/python3 brand/logo-forge/build.py round1      # three candidate geometries, a gallery
    /usr/bin/python3 brand/logo-forge/build.py final --overlap 1.06 --stroke 0.20   # the chosen one, all deliverables

Vector route: three primitives, rendered by headless Chrome at each target size (nothing upscaled),
type outlined with fontTools so no file depends on a font being installed. Needs the system
python3 (fontTools, Pillow) and Google Chrome.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from PIL import Image

HERE = Path(__file__).resolve().parent
BRAND = HERE.parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
FONT = BRAND / "fonts" / "ArchivoBlack-Regular.ttf"

PAPER, INK, GREEN, DARK, DARK_INK = "#f3eee4", "#121212", "#3fb950", "#0d100d", "#e9ede9"
R = 100.0  # the master radius; everything is a multiple of it


# ---------------------------------------------------------------- the mark
def mark_geometry(overlap: float, stroke: float) -> dict:
    w = stroke * R
    d = overlap * R
    cx1 = w / 2 + R
    cx2 = cx1 + d
    cy = w / 2 + R
    return {"w": w, "cx1": cx1, "cx2": cx2, "cy": cy, "width": cx2 + R + w / 2, "height": 2 * R + w}


def mark_body(g: dict, ink: str, uid: str) -> str:
    """The three shapes, in master units, no wrapper. The green sits under the ink arcs."""
    return (f'<clipPath id="lens-{uid}"><circle cx="{g["cx1"]:.2f}" cy="{g["cy"]:.2f}" r="{R}"/></clipPath>'
            f'<g clip-path="url(#lens-{uid})"><circle cx="{g["cx2"]:.2f}" cy="{g["cy"]:.2f}" r="{R}" fill="{GREEN}"/></g>'
            f'<circle cx="{g["cx1"]:.2f}" cy="{g["cy"]:.2f}" r="{R}" fill="none" stroke="{ink}" stroke-width="{g["w"]:.2f}"/>'
            f'<circle cx="{g["cx2"]:.2f}" cy="{g["cy"]:.2f}" r="{R}" fill="none" stroke="{ink}" stroke-width="{g["w"]:.2f}"/>')


def mark_svg(overlap: float, stroke: float, ink: str = INK) -> str:
    g = mark_geometry(overlap, stroke)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {g["width"]:.2f} {g["height"]:.2f}" role="img" aria-label="Quorum">'
            f'<title>Quorum: two lenses, one finding</title>{mark_body(g, ink, "m")}</svg>')


def placed(g: dict, ink: str, uid: str, x: float, y: float, width: float) -> str:
    """The mark translated and scaled so its box is `width` wide with its top-left at (x, y)."""
    s = width / g["width"]
    return f'<g transform="translate({x:.2f} {y:.2f}) scale({s:.5f})">{mark_body(g, ink, uid)}</g>'


def tile_svg(overlap: float, stroke: float, side: float, radius_pct: float, ground: str, ink: str, mark_pct: float) -> str:
    g = mark_geometry(overlap, stroke)
    mw = side * mark_pct
    mh = mw * g["height"] / g["width"]
    rx = side * radius_pct
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {side} {side}" role="img" aria-label="Quorum">'
            f'<rect width="{side}" height="{side}" rx="{rx:.2f}" fill="{ground}"/>'
            f'{placed(g, ink, "t", (side - mw) / 2, (side - mh) / 2, mw)}</svg>')


FAVICON_STROKE, FAVICON_FILL = 0.30, 0.94  # measured at 16 px (rounds/round1/zoom-favicon.png): thinner goes grey, thicker crushes the green
# The favicon gets its own overlap, wider than the master's 1.06 (2026-09-18, round 2).
# Measured natively at 16 px on both grounds: at the master overlap the vesica loses its points
# below ~24 px and the green becomes a two-pixel bar, so the mark reads as spectacles and the
# rings become the subject instead of the finding. 0.96 keeps the green dominant at 16 px without
# tipping into the single-eye reading that 0.86 produces. Evidence: ../explorations/round2-*.png,
# verdicts in ../CRITIQUE.md. Everything else stays on the master geometry.


FAVICON_OVERLAP = 0.96


def favicon_svg(overlap: float = FAVICON_OVERLAP, stroke: float = FAVICON_STROKE) -> str:
    """One file for both tab themes: paper tile with ink by default, dark tile with paper strokes when the OS is dark.
    The stroke is heavier than the master's because a 16 px tab has no room for a thin ring."""
    g = mark_geometry(overlap, stroke)
    side = 64.0
    mw = side * FAVICON_FILL
    mh = mw * g["height"] / g["width"]
    body = placed(g, "currentColor", "f", (side - mw) / 2, (side - mh) / 2, mw).replace('stroke="currentColor"', 'class="k"')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {side} {side}" role="img" aria-label="Quorum">'
            f'<style>.g{{fill:{PAPER}}} .k{{stroke:{INK}}} @media (prefers-color-scheme: dark){{.g{{fill:{DARK}}} .k{{stroke:{DARK_INK}}}}}</style>'
            f'<rect class="g" width="{side}" height="{side}"/>{body}</svg>')


# ---------------------------------------------------------------- the wordmark, outlined
def word_paths(text: str, tracking_em: float = -0.02) -> tuple[str, float, float]:
    """(path data in font units, advance width, cap height) for the text in Archivo Black."""
    font = TTFont(FONT)
    glyphs = font.getGlyphSet()
    cmap = font.getBestCmap()
    upm = font["head"].unitsPerEm
    cap = font["OS/2"].sCapHeight or int(upm * 0.7)
    x = 0.0
    out = []
    for ch in text:
        name = cmap[ord(ch)]
        pen = SVGPathPen(glyphs)
        glyphs[name].draw(pen)
        d = pen.getCommands()
        if d:
            out.append(f'<path transform="translate({x:.1f} 0) scale(1 -1)" d="{d}"/>')
        x += glyphs[name].width + tracking_em * upm
    x -= tracking_em * upm
    return "".join(out), x, cap


def lockup_svg(overlap: float, stroke: float, ink: str = INK, ground: str | None = None) -> str:
    g = mark_geometry(overlap, stroke)
    paths, adv, cap = word_paths("QUORUM")
    # mark height = cap height; gap = 0.6 cap
    scale = cap / g["height"]
    mw = g["width"] * scale
    gap = 0.6 * cap
    pad = 0.35 * cap
    width = pad + mw + gap + adv + pad
    height = cap + 2 * pad
    bg = f'<rect width="{width:.1f}" height="{height:.1f}" fill="{ground}"/>' if ground else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.1f} {height:.1f}" role="img" aria-label="Quorum">'
            f'<title>Quorum</title>{bg}'
            f'{placed(g, ink, "l", pad, pad, mw)}'
            f'<g fill="{ink}" transform="translate({pad + mw + gap:.1f} {pad + cap:.1f})">{paths}</g></svg>')


def social_svg(overlap: float, stroke: float, side: float = 1200) -> str:
    """A paper square with the lockup centred at 72% of the width, for places that ask for a square image."""
    g = mark_geometry(overlap, stroke)
    paths, adv, cap = word_paths("QUORUM")
    scale = cap / g["height"]
    mw = g["width"] * scale
    gap = 0.6 * cap
    lw = mw + gap + adv
    s = side * 0.72 / lw
    x = (side - lw * s) / 2
    y = (side - cap * s) / 2
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {side} {side}" role="img" aria-label="Quorum">'
            f'<rect width="{side}" height="{side}" fill="{PAPER}"/>'
            f'<g transform="translate({x:.1f} {y:.1f}) scale({s:.5f})">{placed(g, INK, "s", 0, 0, mw)}'
            f'<g fill="{INK}" transform="translate({mw + gap:.1f} {cap:.1f})">{paths}</g></g></svg>')


# ---------------------------------------------------------------- rendering
def render(svg_path: Path, png_path: Path, size: tuple[int, int]) -> None:
    """Native render at exactly `size` pixels, device scale 1, no upscaling."""
    html = svg_path.with_suffix(".render.html")
    html.write_text(f'<!doctype html><meta charset="utf-8"><style>html,body{{margin:0;background:transparent}}'
                    f'img{{display:block;width:{size[0]}px;height:{size[1]}px}}</style>'
                    f'<img src="{svg_path.name}">')
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--default-background-color=00000000",
                    f"--window-size={size[0]},{size[1]}", "--force-device-scale-factor=1", "--virtual-time-budget=1500",
                    f"--screenshot={png_path.resolve()}", f"file://{html.resolve()}"], check=True, capture_output=True)
    html.unlink()


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# ---------------------------------------------------------------- rounds
CANDIDATES = {"v1-narrow": (1.06, 0.20), "v2-wide": (0.90, 0.20), "v3-narrow-heavy": (1.06, 0.26)}


def round1(out: Path) -> None:
    rows = []
    for name, (overlap, stroke) in CANDIDATES.items():
        d = out / name
        write(d / "mark-light.svg", mark_svg(overlap, stroke, INK))
        write(d / "mark-dark.svg", mark_svg(overlap, stroke, DARK_INK))
        write(d / "icon-light.svg", tile_svg(overlap, stroke, 1024, 0.22, PAPER, INK, 0.62))
        write(d / "icon-dark.svg", tile_svg(overlap, stroke, 1024, 0.22, DARK, DARK_INK, 0.62))
        write(d / "favicon.svg", favicon_svg(overlap, stroke))  # round 1 used the master stroke; see CRITIQUE.md
        write(d / "avatar-light.svg", tile_svg(overlap, stroke, 800, 0, PAPER, INK, 0.60))
        write(d / "lockup-light.svg", lockup_svg(overlap, stroke, INK, PAPER))
        for size in (1024, 64, 32, 16):
            render(d / "icon-light.svg", d / f"icon-light-{size}.png", (size, size))
            render(d / "icon-dark.svg", d / f"icon-dark-{size}.png", (size, size))
        for size in (48, 32, 16):
            render(d / "favicon.svg", d / f"favicon-{size}.png", (size, size))
        render(d / "avatar-light.svg", d / "avatar-light-400.png", (400, 400))
        render(d / "lockup-light.svg", d / "lockup-light-1200.png", (1200, 300))
        rows.append(name)
    # the gallery: every candidate at every size, plus a tab strip and a circle crop
    cells = []
    for name in rows:
        overlap, stroke = CANDIDATES[name]
        cells.append(f'''<section>
<h2>{name} <small>overlap {overlap} r, stroke {stroke} r</small></h2>
<div class="row"><img src="{name}/icon-light-1024.png" width="256"><img src="{name}/icon-dark-1024.png" width="256">
<div class="avatar"><img src="{name}/avatar-light-400.png"></div>
<img src="{name}/lockup-light-1200.png" width="480"></div>
<div class="row small"><span>64</span><img src="{name}/icon-light-64.png"><img src="{name}/icon-dark-64.png">
<span>32</span><img src="{name}/icon-light-32.png"><img src="{name}/icon-dark-32.png">
<span>16</span><img src="{name}/icon-light-16.png"><img src="{name}/icon-dark-16.png">
<span>favicon 48/32/16</span><img src="{name}/favicon-48.png"><img src="{name}/favicon-32.png"><img src="{name}/favicon-16.png"></div>
<div class="tab"><img src="{name}/favicon-16.png"><span>Quorum: a swarm that coordinates through memory</span></div>
<div class="tab dark"><img src="{name}/favicon-16.png"><span>Quorum: a swarm that coordinates through memory</span></div>
</section>''')
    write(out / "gallery.html", '''<!doctype html><meta charset="utf-8"><title>Quorum mark, round 1</title>
<style>body{font:14px/1.4 -apple-system,sans-serif;margin:24px;background:#ddd;color:#111}section{background:#f7f5f0;padding:16px;margin-bottom:16px}
h2{margin:0 0 12px;font-size:16px}small{color:#666;font-weight:normal}.row{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.small img{image-rendering:pixelated}.small span{color:#666;font-size:12px}.avatar{width:200px;height:200px;border-radius:50%;overflow:hidden}.avatar img{width:100%;height:100%}
.tab{display:inline-flex;align-items:center;gap:8px;background:#f1f3f4;color:#202124;padding:6px 12px;margin:8px 8px 0 0;font-size:12px;border-radius:8px 8px 0 0}
.tab.dark{background:#35363a;color:#e8eaed}.tab img{width:16px;height:16px}</style>''' + "".join(cells))
    print("wrote", out / "gallery.html")


def final(out: Path, overlap: float, stroke: float) -> None:
    write(out / "mark.svg", mark_svg(overlap, stroke, INK))
    write(out / "mark-dark.svg", mark_svg(overlap, stroke, DARK_INK))
    write(out / "lockup.svg", lockup_svg(overlap, stroke, INK))
    write(out / "lockup-dark.svg", lockup_svg(overlap, stroke, DARK_INK))
    write(out / "icon.svg", tile_svg(overlap, stroke, 1024, 0.22, PAPER, INK, 0.62))
    write(out / "icon-dark.svg", tile_svg(overlap, stroke, 1024, 0.22, DARK, DARK_INK, 0.62))
    write(out / "favicon.svg", favicon_svg())
    write(out / "avatar.svg", tile_svg(overlap, stroke, 800, 0, PAPER, INK, 0.60))
    write(out / "avatar-dark.svg", tile_svg(overlap, stroke, 800, 0, DARK, DARK_INK, 0.60))
    write(out / "social.svg", social_svg(overlap, stroke))
    for size in (1024, 512, 256, 180, 64, 32, 16):
        render(out / "icon.svg", out / f"icon-{size}.png", (size, size))
        render(out / "icon-dark.svg", out / f"icon-dark-{size}.png", (size, size))
    render(out / "avatar.svg", out / "avatar-800.png", (800, 800))
    render(out / "avatar-dark.svg", out / "avatar-dark-800.png", (800, 800))
    render(out / "mark.svg", out / "mark-512.png", (512, int(512 * mark_geometry(overlap, stroke)["height"] / mark_geometry(overlap, stroke)["width"])))
    g = mark_geometry(overlap, stroke)
    _, adv, cap = word_paths("QUORUM")
    lw = 0.35 * cap * 2 + g["width"] * cap / g["height"] + 0.6 * cap + adv
    lh = cap * 1.7
    render(out / "lockup.svg", out / "lockup-1600.png", (1600, int(1600 * lh / lw)))
    render(out / "social.svg", out / "social-1200.png", (1200, 1200))
    write(out / "favicon-light.svg", favicon_svg().split("<style>")[0] + "<style>.g{fill:" + PAPER + "} .k{stroke:" + INK + "}</style>" + favicon_svg().split("</style>")[1])
    write(out / "favicon-dark.svg", favicon_svg().split("<style>")[0] + "<style>.g{fill:" + DARK + "} .k{stroke:" + DARK_INK + "}</style>" + favicon_svg().split("</style>")[1])
    for size in (48, 32, 16):
        render(out / "favicon-light.svg", out / f"favicon-{size}.png", (size, size))
        render(out / "favicon-dark.svg", out / f"favicon-dark-{size}.png", (size, size))
    # the .ico carries the three native renders; Pillow takes the largest as the base and the rest appended
    Image.open(out / "favicon-48.png").save(out / "favicon.ico", sizes=[(48, 48), (32, 32), (16, 16)],
                                            append_images=[Image.open(out / "favicon-32.png"), Image.open(out / "favicon-16.png")])
    print("wrote finals to", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["round1", "final"])
    ap.add_argument("--overlap", type=float, default=1.06)
    ap.add_argument("--stroke", type=float, default=0.20)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    if a.stage == "round1":
        round1(Path(a.out) if a.out else HERE / "rounds" / "round1")
    else:
        final(Path(a.out) if a.out else BRAND / "logo", a.overlap, a.stroke)
