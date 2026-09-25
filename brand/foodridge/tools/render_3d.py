"""FOODRIDGE 3D (embossed metallic gold) logo renderer.

Takes the flat, outlined master SVGs in ../svg and renders a bevelled,
extruded gold version with lighting from the top-left and a soft shadow.
Output: ../3d/*.png (transparent background, except the app icon).

Usage: python3 render_3d.py
Requires: pip install cairosvg numpy scipy pillow
"""
import io
import os

import cairosvg
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Metallic gold ramp: shadow -> body -> highlight (Foodridge Gold family)
RAMP = np.array([
    (0.00, (92, 60, 14)),
    (0.35, (140, 100, 32)),    # Gold Dark
    (0.60, (184, 134, 47)),    # Foodridge Gold
    (0.82, (230, 199, 122)),   # Gold Light
    (1.00, (255, 244, 208)),
], dtype=object)
SIDE = np.array((110, 74, 20), dtype=float)   # extrusion side colour
NAVY = (20, 33, 61)


def mask_from_svg(path, width):
    png = cairosvg.svg2png(url=path, output_width=width)
    return np.asarray(Image.open(io.BytesIO(png)).convert("RGBA"), dtype=float)[..., 3] / 255


def ramp(v):
    v = np.clip(v, 0, 1)
    out = np.zeros(v.shape + (3,))
    for (p0, c0), (p1, c1) in zip(RAMP[:-1], RAMP[1:]):
        m = (v >= p0) & (v <= p1)
        t = ((v - p0) / (p1 - p0))[m][:, None]
        out[m] = np.array(c0) * (1 - t) + np.array(c1) * t
    return out


def _over(src_rgb, src_a, dst_rgb, dst_a):
    out_a = src_a + dst_a * (1 - src_a)
    num = src_rgb * src_a[..., None] + dst_rgb * (dst_a * (1 - src_a))[..., None]
    return num / np.maximum(out_a, 1e-6)[..., None], out_a


def perspective(alpha, near=1.0, far=0.78, squeeze=0.88, lift=0.10):
    """Side-angle view: the logo turns away to the right like a sign seen from the left.

    near/far: relative height of the left/right edge, squeeze: width kept,
    lift: how much the right edge rises (fraction of height).
    """
    h, w = alpha.shape
    img = Image.fromarray((alpha * 255).astype(np.uint8), "L")
    W2 = int(w * squeeze)
    top_r = h * (1 - far) / 2 - h * lift
    dst = [(0, 0), (W2, top_r), (W2, top_r + h * far), (0, h * near)]
    off = -min(0, top_r)
    dst = [(x, y + off) for x, y in dst]
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    rows, rhs = [], []
    for (X, Y), (x, y) in zip(dst, src):  # PIL wants output -> input mapping
        rows.append([X, Y, 1, 0, 0, 0, -x * X, -x * Y]); rhs.append(x)
        rows.append([0, 0, 0, X, Y, 1, -y * X, -y * Y]); rhs.append(y)
    coeffs = np.linalg.solve(np.array(rows, float), np.array(rhs, float))
    H2 = int(max(y for _, y in dst)) + 1
    out = img.transform((W2, H2), Image.PERSPECTIVE, tuple(coeffs), Image.BICUBIC)
    return np.asarray(out, dtype=float) / 255


def render(alpha, unit, extrude=(1.0, 0.35), depth_mul=1.6):
    """alpha: HxW coverage mask. unit: pixels per 'stroke unit' (sets bevel/depth).

    extrude: (dy, dx) direction the thickness shows per pixel of depth.
    """
    h, w = alpha.shape
    bevel = 2.2 * unit
    depth = int(round(depth_mul * unit))
    pad = depth + int(6 * unit)
    a = np.pad(alpha, pad)
    inside = a > 0.5

    # height field: rounded bevel from the edge inward
    d = ndimage.distance_transform_edt(inside)
    hgt = np.sin(np.clip(d / bevel, 0, 1) * np.pi / 2)
    hgt = ndimage.gaussian_filter(hgt, unit * 0.35)
    gy, gx = np.gradient(hgt * bevel * 1.1)
    n = np.dstack((-gx, -gy, np.ones_like(hgt)))
    n /= np.linalg.norm(n, axis=2, keepdims=True)

    light = np.array((-0.45, -0.65, 0.62))
    light /= np.linalg.norm(light)
    diffuse = np.clip((n * light).sum(2), 0, 1)
    half = light + np.array((0, 0, 1.0))
    half /= np.linalg.norm(half)
    spec = np.clip((n * half).sum(2), 0, 1) ** 40

    # vertical "studio" reflection band typical of polished gold
    H = a.shape[0]
    yy = np.linspace(0, 1, H)[:, None]
    band = 0.10 * np.cos((yy - 0.35) * np.pi * 2.2)

    tone = 0.31 + 0.62 * diffuse + band
    face = ramp(tone) + spec[..., None] * np.array((255, 240, 200)) * 0.55
    face = np.clip(face, 0, 255)

    # extrusion: stack of the mask shifted down/right, darker further back
    # (hairline tips are opened away first so they don't leave dark slivers)
    base = np.clip((ndimage.grey_opening(a, size=max(3, int(unit * 0.6))) - 0.35) / 0.3, 0, 1)
    side_a = np.zeros_like(a)
    side_rgb = np.zeros(a.shape + (3,)) + SIDE * 0.75
    for k in range(depth, 0, -1):
        sh = np.roll(np.roll(base, int(round(k * extrude[0])), 0), int(round(k * extrude[1])), 1)
        shade = SIDE * (0.75 + 0.25 * (1 - k / depth))
        side_rgb = side_rgb * (1 - sh[..., None]) + shade * sh[..., None]
        side_a = np.maximum(side_a, sh)

    # soft drop shadow
    sh_a = ndimage.gaussian_filter(np.roll(np.roll(a, depth + int(2 * unit), 0), int(unit), 1), 3 * unit) * 0.28

    # composite (straight alpha): shadow < extrusion < face
    rgb, alpha_out = np.zeros(a.shape + (3,)) + (20, 14, 4), sh_a
    for layer_rgb, layer_a in ((side_rgb, side_a), (face, a)):
        rgb, alpha_out = _over(layer_rgb, layer_a, rgb, alpha_out)
    img = np.dstack((np.clip(rgb, 0, 255), alpha_out * 255)).astype(np.uint8)
    return Image.fromarray(img, "RGBA")


def main():
    src = os.path.join(ROOT, "svg")
    out = os.path.join(ROOT, "3d")
    os.makedirs(out, exist_ok=True)
    jobs = {
        "primary": 3000,
        "primary-kr": 3000,
        "horizontal": 3600,
        "symbol": 2000,
        "wordmark": 3000,
    }
    for name, width in jobs.items():
        alpha = mask_from_svg(os.path.join(src, f"foodridge-{name}-black.svg"), width)
        unit = width / 3000 * 9 * (1.35 if name == "symbol" else 1)
        img = render(alpha, unit)
        img.save(os.path.join(out, f"foodridge-{name}-3d.png"), optimize=True)
        print("wrote", name)

    # Side-angle 3D (like a metal sign seen from the left): thicker body,
    # thickness showing on the left/lower faces.
    for name, width in (("primary", 3000), ("primary-kr", 3000), ("horizontal", 3600)):
        alpha = perspective(mask_from_svg(os.path.join(src, f"foodridge-{name}-black.svg"), width))
        unit = width / 3000 * 9
        img = render(alpha, unit, extrude=(0.55, -1.0), depth_mul=3.2)
        img.save(os.path.join(out, f"foodridge-{name}-3d-angle.png"), optimize=True)
        print("wrote", name, "angle")

    # 3D app icon: symbol on navy rounded square
    sym = Image.open(os.path.join(out, "foodridge-symbol-3d.png"))
    icon = Image.new("RGBA", (2048, 2048), (0, 0, 0, 0))
    bg = Image.new("L", (2048, 2048), 0)
    ImageDraw.Draw(bg).rounded_rectangle((0, 0, 2047, 2047), radius=448, fill=255)
    icon.paste(Image.new("RGBA", (2048, 2048), NAVY + (255,)), (0, 0), bg)
    k = (760 / 1024 * 2048) / (600 / 720 * 2000)  # match the flat icon's symbol width
    s = sym.resize((int(sym.width * k), int(sym.height * k)), Image.LANCZOS)
    icon.alpha_composite(s, ((2048 - s.width) // 2, (2048 - s.height) // 2))
    icon.save(os.path.join(out, "foodridge-app-icon-3d.png"), optimize=True)
    print("wrote app-icon")


if __name__ == "__main__":
    main()
