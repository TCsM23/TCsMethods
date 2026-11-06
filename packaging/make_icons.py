"""Draw the app icon as 32x32 pixel art and export it at every size needed.

    python packaging/make_icons.py      # -> packaging/icons/*.png, pixel-slides.ico
"""
from pathlib import Path

from PIL import Image

OUT = Path(__file__).parent / "icons"
DARK, MID, LIGHT, PAPER = "#0f380f", "#306230", "#8bac0f", "#c4d88a"

# A slide on an LCD: a dark body, a light screen with a title bar, lines of
# text, a play arrow and a row of "progress" pips. Rectangles on a 32x32 grid.
SHAPES = [
    (MID, 2, 3, 30, 27),     # screen bezel
    (PAPER, 3, 4, 29, 26),   # screen
    (LIGHT, 5, 6, 27, 8),    # title bar
    (DARK, 5, 10, 15, 12),   # heading
    (DARK, 5, 13, 20, 14),   # text lines
    (DARK, 5, 16, 17, 17),
    (DARK, 5, 19, 22, 20),
    (LIGHT, 5, 22, 9, 24),   # progress pips
    (LIGHT, 10, 22, 14, 24),
    (LIGHT, 15, 22, 19, 24),
]
ARROW = [(23, 12, 1), (23, 13, 2), (23, 14, 3), (23, 15, 4), (23, 16, 3), (23, 17, 2), (23, 18, 1)]


def draw() -> Image.Image:
    image = Image.new("RGB", (32, 32), DARK)
    for colour, x0, y0, x1, y1 in SHAPES:
        image.paste(colour, (x0, y0, x1, y1))
    for x, y, width in ARROW:
        image.paste(DARK, (x, y, x + width, y + 1))
    return image.convert("RGBA")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    art = draw()
    big = lambda n: art.resize((n, n), Image.NEAREST)  # noqa: E731 - crisp pixels, no smoothing
    for n in (16, 32, 48, 180, 192, 256, 512):
        big(n).save(OUT / f"icon-{n}.png")
    # Maskable: the art inside the 80% safe zone, on the dark body colour.
    for n in (192, 512):
        canvas = Image.new("RGBA", (n, n), DARK)
        inner = round(n * 0.75)
        canvas.paste(big(inner), ((n - inner) // 2, (n - inner) // 2))
        canvas.save(OUT / f"maskable-{n}.png")
    big(256).save(OUT / "pixel-slides.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])


if __name__ == "__main__":
    main()
