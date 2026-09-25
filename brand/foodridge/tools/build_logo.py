"""FOODRIDGE logo system generator.

Builds every official logo file from one geometry spec so all variants stay
identical. Text is converted to outlines, so the SVGs open in Illustrator,
Figma or a browser without the fonts installed.

Usage:
    python3 build_logo.py <Cinzel-SemiBold.ttf> <NotoSerifKR-SemiBold.ttf>
Requires: pip install fonttools uharfbuzz cairosvg
"""
import os
import sys

import cairosvg
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

OUT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# ---- Brand colours --------------------------------------------------------
GOLD = "#B8862F"        # Foodridge Gold (primary)
GOLD_LIGHT = "#E6C77A"  # gradient highlight
GOLD_DARK = "#8C6420"   # gradient shadow
NAVY = "#14213D"        # Foodridge Navy (secondary / reversed background)
BLACK = "#1A1A1A"
WHITE = "#FFFFFF"


# ---- Text to outlines -----------------------------------------------------
def text_path(font_file, text, size, tracking=0.0):
    """Return (svg path d, advance width, cap height) at `size` px, baseline y=0."""
    face = hb.Face(hb.Blob.from_file_path(font_file))
    font = hb.Font(face)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(font, buf, {"kern": True})
    tt = TTFont(font_file)
    gs, order = tt.getGlyphSet(), tt.getGlyphOrder()
    scale = size / tt["head"].unitsPerEm
    pen = SVGPathPen(gs)
    x = 0.0
    last = len(buf.glyph_infos) - 1
    for i, (info, pos) in enumerate(zip(buf.glyph_infos, buf.glyph_positions)):
        tp = TransformPen(pen, (scale, 0, 0, -scale, x + pos.x_offset * scale, -pos.y_offset * scale))
        gs[order[info.codepoint]].draw(tp)
        x += pos.x_advance * scale + (tracking * size if i < last else 0)
    return pen.getCommands(), x, tt["OS/2"].sCapHeight * scale


# ---- Bridge symbol (unit box 600 x 262) -----------------------------------
# One H-tower, two catenary main cables, hangers and a tapered deck that also
# reads as a "ridge". Fills only, so it prints and cuts cleanly.
SYM_W, SYM_H = 600, 262
CABLE_L = ((290, 33), (208, 219), (18, 235))  # left main cable centre-line


def _quad(p, t):
    (x0, y0), (x1, y1), (x2, y2) = p
    u = 1 - t
    return u * u * x0 + 2 * u * t * x1 + t * t * x2, u * u * y0 + 2 * u * t * y1 + t * t * y2


def _cable_y(x):
    return min((abs(_quad(CABLE_L, i / 2000)[0] - x), _quad(CABLE_L, i / 2000)[1]) for i in range(2001))[1]


def _deck_y(x):
    return _quad(((0, 262), (300, 220), (600, 262)), x / 600)[1]


def bridge_symbol(fill):
    tower = "M281 28h14v250h-14z M305 28h14v250h-14z M277 18h46v12h-46z M295 112h10v10h-10z"
    cables = ("M288 30 Q205 214 18 232 L18 238 Q212 224 292 36Z"
              " M312 30 Q395 214 582 232 L582 238 Q388 224 308 36Z")
    hangers = []
    for x in (246, 202, 158, 114, 70):
        top, bot = _cable_y(x) + 2, _deck_y(x) + 1
        for xx in (x, SYM_W - x):
            hangers.append(f"M{xx - 2:.1f} {top:.1f}H{xx + 2:.1f}V{bot:.1f}H{xx - 2:.1f}Z")
    deck = "M0 262 Q300 220 600 262 Q300 240 0 262Z"
    return (f'<g fill="{fill}"><path d="{tower}"/><path d="{cables}"/>'
            f'<path d="{" ".join(hangers)}"/><path d="{deck}"/></g>')


# ---- Assembly -------------------------------------------------------------
GRADIENT = (f'<defs><linearGradient id="fg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0" stop-color="{GOLD_LIGHT}"/><stop offset="0.55" stop-color="{GOLD}"/>'
            f'<stop offset="1" stop-color="{GOLD_DARK}"/></linearGradient></defs>')

VARIANTS = {
    "gold": (GOLD, None),
    "gradient": ("url(#fg)", None),
    "black": (BLACK, None),
    "white": (WHITE, NAVY),
}


def svg(w, h, body, bg=None, title="FOODRIDGE"):
    bgr = f'<rect width="100%" height="100%" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" '
            f'width="{w:.0f}" height="{h:.0f}" role="img" aria-label="{title}">'
            f'<title>{title}</title>{bgr}{body}</svg>\n')


def sym(fill, x, y, s):
    return f'<g transform="translate({x:.2f} {y:.2f}) scale({s:.4f})">{bridge_symbol(fill)}</g>'


def word(fill, d, x, baseline):
    return f'<path fill="{fill}" transform="translate({x:.2f} {baseline:.2f})" d="{d}"/>'


def build(cinzel, noto):
    word_d, word_w, cap = text_path(cinzel, "FOODRIDGE", 200, tracking=0.08)
    kr_d, kr_w, _ = text_path(noto, "푸드릿지", 60, tracking=0.30)
    pad = cap  # clear space = cap height of the wordmark ("F" height)

    files = {}
    for key, (fill, bg) in VARIANTS.items():
        defs = GRADIENT if key == "gradient" else ""

        # 1) Primary (stacked): symbol above wordmark
        s = word_w * 0.64 / SYM_W
        gap = cap * 0.30
        base = pad + SYM_H * s + gap + cap
        W = word_w + 2 * pad
        body = defs + sym(fill, pad + (word_w - SYM_W * s) / 2, pad, s) + word(fill, word_d, pad, base)
        files[f"foodridge-primary-{key}.svg"] = svg(W, base + pad, body, bg)

        # 2) Primary + Korean name
        kbase = base + cap * 0.78
        kx = pad + (word_w - kr_w) / 2
        rule_w = kx - pad - cap * 0.3
        ry = kbase - 22
        body2 = (body + word(fill, kr_d, kx, kbase)
                 + f'<rect fill="{fill}" x="{pad:.2f}" y="{ry:.2f}" width="{rule_w:.2f}" height="3"/>'
                 + f'<rect fill="{fill}" x="{W - pad - rule_w:.2f}" y="{ry:.2f}" width="{rule_w:.2f}" height="3"/>')
        files[f"foodridge-primary-kr-{key}.svg"] = svg(W, kbase + pad, body2, bg, "FOODRIDGE 푸드릿지")

        # 3) Horizontal: symbol left, wordmark right, deck ends on the baseline
        hs = cap * 2.3 / SYM_H
        hgap = cap * 0.5
        hbase = pad + SYM_H * hs
        body3 = defs + sym(fill, pad, pad, hs) + word(fill, word_d, pad + SYM_W * hs + hgap, hbase)
        files[f"foodridge-horizontal-{key}.svg"] = svg(pad + SYM_W * hs + hgap + word_w + pad, hbase + pad, body3, bg)

        # 4) Symbol only
        files[f"foodridge-symbol-{key}.svg"] = svg(
            720, 720, defs + sym(fill, 60, 229, 1), bg, "FOODRIDGE symbol")

        # 5) Wordmark only
        files[f"foodridge-wordmark-{key}.svg"] = svg(
            word_w + 2 * pad, cap + 2 * pad, defs + word(fill, word_d, pad, pad + cap), bg)

    # App icon / favicon / SNS profile
    files["foodridge-app-icon.svg"] = svg(
        1024, 1024, f'<rect width="1024" height="1024" rx="224" fill="{NAVY}"/>'
        + sym(GOLD_LIGHT, 132, 357, 760 / SYM_W))
    files["foodridge-sns-profile.svg"] = svg(
        1024, 1024, f'<rect width="1024" height="1024" fill="{NAVY}"/>' + GRADIENT
        + sym("url(#fg)", 187, 330, 650 / SYM_W)
        + f'<g transform="translate({512 - word_w * 0.3 / 2:.2f} {330 + 262 * 650 / SYM_W + 60 + cap * 0.3:.2f}) scale(0.3)">'
          f'<path fill="{GOLD_LIGHT}" d="{word_d}"/></g>')

    for sub in ("svg", "png"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)
    for name, data in files.items():
        with open(os.path.join(OUT, "svg", name), "w", encoding="utf-8") as fh:
            fh.write(data)
        cairosvg.svg2png(bytestring=data.encode(), write_to=os.path.join(OUT, "png", name[:-4] + ".png"),
                         output_width=2000 if "icon" not in name and "sns" not in name else 1024)
    print(f"wrote {len(files)} logos (svg + png)")


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2])
