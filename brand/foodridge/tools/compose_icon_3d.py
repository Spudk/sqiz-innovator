"""Place the 3D symbol render on the navy rounded-square app icon."""
import os

from PIL import Image, ImageDraw

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
NAVY = (20, 33, 61, 255)

sym = Image.open(os.path.join(ROOT, "3d", "foodridge-symbol-3d.png"))
sym = sym.crop(sym.getbbox())
mask = Image.new("L", (2048, 2048), 0)
ImageDraw.Draw(mask).rounded_rectangle((0, 0, 2047, 2047), radius=448, fill=255)
icon = Image.new("RGBA", (2048, 2048), (0, 0, 0, 0))
icon.paste(Image.new("RGBA", (2048, 2048), NAVY), (0, 0), mask)
k = 1520 / sym.width  # same symbol width as the flat app icon
sym = sym.resize((round(sym.width * k), round(sym.height * k)), Image.LANCZOS)
icon.alpha_composite(sym, ((2048 - sym.width) // 2, (2048 - sym.height) // 2))
icon.save(os.path.join(ROOT, "3d", "foodridge-app-icon-3d.png"), optimize=True)
print("wrote app icon")
