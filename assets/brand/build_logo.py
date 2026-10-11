#!/usr/bin/env python3
"""Builds the SlowAI logo SVGs ("Route" direction) with outlined Sora SemiBold lettering.

The reversed S is a drawn path that ends in a decision node: raw signal at the
top, a decision at the end. Usage:

    python assets/brand/build_logo.py path/to/sora-latin-wght-normal.woff2

Sora is licensed under the SIL Open Font License 1.1.
"""
import sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

OUT = Path(__file__).parent
S_PATH = "M78 32 C72 16 56 10 46 10 C30 10 20 20 20 36 C20 56 40 62 52 66 C68 71 82 80 82 100 C82 120 66 130 50 130 C36 130 24 124 18 110"
ASC, TRACK, STROKE = 730, -34, 19          # "l" ascender (font units), tracking, mark stroke (path units)
SC = ASC / 120                             # path spans y 10..130
PALETTES = {
    "light": {"ink": "#0a1f3a", "ai": "#1f63c6", "g0": "#8fbaf0", "g1": "#1f63c6", "node_fill": "#ffffff", "node": "#1f63c6"},
    "dark":  {"ink": "#f4f8fc", "ai": "#6fb0ff", "g0": "#3a6fb3", "g1": "#6fb0ff", "node_fill": "#071a33", "node": "#6fb0ff"},
}


def mark_group(p, ox, base, grad_id):
    tx, ty = ox, base - 130 * SC
    return (f'<g transform="translate({tx:.1f} {ty:.1f}) scale({SC:.4f})">'
            f'<g transform="translate(100 0) scale(-1 1)"><path d="{S_PATH}" fill="none" stroke="url(#{grad_id})" '
            f'stroke-width="{STROKE}" stroke-linecap="round"/></g>'
            f'<circle cx="82" cy="110" r="11" fill="{p["node_fill"]}" stroke="{p["node"]}" stroke-width="7"/></g>')


def gradient(p, gid):
    return (f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{p["g0"]}"/><stop offset="1" stop-color="{p["g1"]}"/></linearGradient>')


def main(font_path):
    font = instancer.instantiateVariableFont(TTFont(font_path), {"wght": 600})
    gs, cmap, hmtx = font.getGlyphSet(), font.getBestCmap(), font["hmtx"]
    pad, base = 40, 40 + ASC + 10
    mark_w = (64 + STROKE + 10) * SC                # path x 18..82 plus stroke and node
    for name, p in PALETTES.items():
        x = pad + mark_w + 95
        parts = []
        for i, ch in enumerate("lowAI"):
            g = cmap[ord(ch)]
            pen = SVGPathPen(gs)
            gs[g].draw(TransformPen(pen, (1, 0, 0, -1, x, base)))
            parts.append(f'<path d="{pen.getCommands()}" fill="{p["ai"] if ch in "AI" else p["ink"]}"/>')
            x += hmtx[g][0] + TRACK
        width, height = int(x + pad), int(base + 60)
        gid = f"slowai-{name}-g"
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="SlowAI">'
               f'<title>SlowAI</title><defs>{gradient(p, gid)}</defs>'
               f'{mark_group(p, pad - 18 * SC + STROKE * SC / 2, base, gid)}{"".join(parts)}</svg>\n')
        (OUT / f"slowai-logo-{name}.svg").write_text(svg)
    # App icon / favicon: the mark alone on a navy tile
    p = PALETTES["dark"]
    icon = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="SlowAI">'
            f'<title>SlowAI</title><defs>{gradient(p, "slowai-icon-g")}</defs>'
            '<rect width="120" height="120" rx="28" fill="#0a1f3a"/>'
            '<g transform="translate(15 4) scale(.9)"><g transform="translate(100 0) scale(-1 1)">'
            f'<path d="{S_PATH}" fill="none" stroke="url(#slowai-icon-g)" stroke-width="16" stroke-linecap="round"/></g>'
            '<circle cx="82" cy="110" r="11" fill="#0a1f3a" stroke="#6fb0ff" stroke-width="8"/></g></svg>\n')
    (OUT / "slowai-icon.svg").write_text(icon)
    print("wrote", sorted(f.name for f in OUT.glob("slowai-*.svg")))


if __name__ == "__main__":
    main(sys.argv[1])
