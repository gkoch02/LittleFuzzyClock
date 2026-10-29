"""Render the README banner at docs/banner.png.

Black and white only, dithered to one bit the way the panel is, in the clock's
own vendored faces and its Bauhaus border. The panel on the right is
`render_clock()` at a pinned time, scaled up pixel-for-pixel, so the banner
tracks the live layout. Deterministic: no clock reads, no random font.

Usage:
    python3 docs/make_banner.py
"""

import os
import sys
from datetime import datetime

from PIL import Image, ImageDraw

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)

from fuzzyclock.fonts import load_font  # noqa: E402
from fuzzyclock.frames import draw_border  # noqa: E402
from fuzzyclock.render import render_clock  # noqa: E402

OUT_PATH = os.path.join(REPO_ROOT, "docs", "banner.png")
WIDTH, HEIGHT = 1600, 400
PANEL_W, PANEL_H = 250, 122  # the 2.13" panel, landscape
SCALE = 3
NOW = datetime(2026, 6, 29, 9, 30)
PAPER, INK = 255, 0


def panel():
    image = Image.new("1", (PANEL_W, PANEL_H), PAPER)
    render_clock(ImageDraw.Draw(image), PANEL_W, PANEL_H, NOW, font_variant="playfair")
    return image.convert("L").resize((PANEL_W * SCALE, PANEL_H * SCALE), Image.Resampling.NEAREST)


def main():
    image = Image.new("L", (WIDTH, HEIGHT), PAPER)
    draw = ImageDraw.Draw(image)

    clock = panel()
    px = WIDTH - clock.width - 60
    py = (HEIGHT - clock.height) // 2
    bezel = 10
    draw.rounded_rectangle(
        (px - bezel, py - bezel, px + clock.width + bezel, py + clock.height + bezel),
        radius=12,
        fill=INK,
    )
    image.paste(clock, (px, py))

    # The left block wears the clock's own Bauhaus border.
    box = Image.new("L", (690, 320), PAPER)
    draw_border(ImageDraw.Draw(box), box.width, box.height, margin=6, frame="bauhaus")
    image.paste(box, (50, 40))

    x = 96
    draw.text((x, 84), "Little Fuzzy Clock", font=load_font(66, "playfair"), fill=INK)
    draw.text((x + 2, 180), "the time, roughly", font=load_font(40, "literata"), fill=INK)
    small = load_font(21, "dejavu")
    for i, line in enumerate(
        (
            "dialects from Shakespeare to Klingon",
            "a border to suit the font",
            "a Raspberry Pi Zero on a 2.13-inch e-ink",
        )
    ):
        draw.text((x + 2, 240 + i * 30), line, font=small, fill=INK)

    image.convert("1", dither=Image.Dither.FLOYDSTEINBERG).save(OUT_PATH, optimize=True)
    print(f"wrote {os.path.relpath(OUT_PATH, REPO_ROOT)} ({WIDTH}x{HEIGHT})")


if __name__ == "__main__":
    main()
