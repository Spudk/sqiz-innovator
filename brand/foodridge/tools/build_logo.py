"""FOODRIDGE logo system generator.

Builds every official logo file from one geometry spec so all variants stay
identical. Text is converted to outlines, so the SVGs open in Illustrator,
Figma or a browser without the fonts installed.

Usage:
    python3 build_logo.py <Cinzel-SemiBold.ttf> <NotoSerifKR-SemiBold.ttf> [--towers 2]
    (--towers 2 writes the two-tower option to ../options/two-tower/)
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


def _bez_y(p, x):
    return min((abs(_quad(p, i / 2000)[0] - x), _quad(p, i / 2000)[1]) for i in range(2001))[1]


def _cable_y(x):
    return _bez_y(CABLE_L, x)


def _deck_y(x):
    return _quad(((0, 262), (300, 220), (600, 262)), x / 600)[1]


TOWERS = 1  # 1 = single H-tower (primary), 2 = classic two-tower suspension bridge


def _tapered(p, w, n=48):
    """Constant-width fill along quadratic p (approximates a stroked cable)."""
    pts = [_quad(p, i / n) for i in range(n + 1)]
    left, right = [], []
    for i, (x, y) in enumerate(pts):
        (ax, ay), (bx, by) = pts[max(i - 1, 0)], pts[min(i + 1, n)]
        dx, dy = bx - ax, by - ay
        ln = (dx * dx + dy * dy) ** 0.5
        nx, ny = -dy / ln * w / 2, dx / ln * w / 2
        left.append(f"{x + nx:.1f} {y + ny:.1f}")
        right.append(f"{x - nx:.1f} {y - ny:.1f}")
    return "M" + " L".join(left + right[::-1]) + "Z"


def _two_tower_symbol(fill):
    towers, cables, hangers = [], [], []
    for c in (170, 430):
        towers.append(f"M{c - 16} 48h12v230h-12z M{c + 4} 48h12v230h-12z"
                      f" M{c - 20} 38h40v11h-40z M{c - 4} 48h8v14h-8z M{c - 4} 128h8v9h-8z")
    main = ((170, 50), (300, 404), (430, 50))
    side_l = ((170, 50), (112, 206), (18, 235))
    side_r = tuple((SYM_W - x, y) for x, y in side_l)
    for p in (main, side_l, side_r):
        cables.append(_tapered(p, 6))
    for p, xs in ((main, (206, 238, 270, 300, 330, 362, 394)),
                  (side_l, (134, 98, 62)), (side_r, (466, 502, 538))):
        for x in xs:
            top, bot = _bez_y(p, x) + 2, _deck_y(x) + 1
            if bot - top > 3:
                hangers.append(f"M{x - 2:.1f} {top:.1f}H{x + 2:.1f}V{bot:.1f}H{x - 2:.1f}Z")
    deck = "M0 262 Q300 220 600 262 Q300 240 0 262Z"
    return (f'<g fill="{fill}"><path d="{" ".join(towers)}"/><path d="{" ".join(cables)}"/>'
            f'<path d="{" ".join(hangers)}"/><path d="{deck}"/></g>')


def bridge_symbol(fill):
    if TOWERS == 2:
        return _two_tower_symbol(fill)
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

    out = OUT if TOWERS == 1 else os.path.join(OUT, "options", "two-tower")
    for sub in ("svg", "png"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    for name, data in files.items():
        with open(os.path.join(out, "svg", name), "w", encoding="utf-8") as fh:
            fh.write(data)
        cairosvg.svg2png(bytestring=data.encode(), write_to=os.path.join(out, "png", name[:-4] + ".png"),
                         output_width=2000 if "icon" not in name and "sns" not in name else 1024)
    print(f"wrote {len(files)} logos (svg + png)")


if __name__ == "__main__":
    if "--towers" in sys.argv:
        i = sys.argv.index("--towers")
        TOWERS = int(sys.argv.pop(i + 1))
        sys.argv.pop(i)
    build(sys.argv[1], sys.argv[2])
