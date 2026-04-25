"""Smoke tests for the rendering helpers in fuzzyclock_core.

These don't try to assert pixel-exact output (which would be brittle
against font hinting). They just confirm the helpers run end-to-end and
produce something that looks like a real render rather than a blank
canvas.

Run with: python3 -m unittest test_render
"""

import unittest
from datetime import datetime

from PIL import Image, ImageDraw

from fuzzyclock_core import draw_border, load_font, render_clock


WIDTH, HEIGHT = 250, 122  # landscape orientation of the 2.13" V4 panel


def _count_black_pixels(image):
    # histogram()[0] is the count of value-0 pixels, which for a mode "1"
    # image is exactly the black-pixel count. Avoids the getdata() warning
    # in newer Pillow releases.
    return image.histogram()[0]


class LoadFontTests(unittest.TestCase):
    def test_returns_font_for_each_size_used_by_the_app(self):
        for size in (14, 22, 24, 28):
            self.assertIsNotNone(load_font(size))


class DrawBorderTests(unittest.TestCase):
    def test_marks_some_pixels(self):
        image = Image.new("1", (WIDTH, HEIGHT), 255)
        draw_border(ImageDraw.Draw(image), WIDTH, HEIGHT)
        self.assertGreater(_count_black_pixels(image), 0)

    def test_border_is_sparse_not_a_filled_rectangle(self):
        image = Image.new("1", (WIDTH, HEIGHT), 255)
        draw_border(ImageDraw.Draw(image), WIDTH, HEIGHT)
        self.assertLess(_count_black_pixels(image), (WIDTH * HEIGHT) // 4)


class RenderClockTests(unittest.TestCase):
    def setUp(self):
        self.fonts = (load_font(28), load_font(22), load_font(14))

    def _render(self, when):
        image = Image.new("1", (WIDTH, HEIGHT), 255)
        render_clock(ImageDraw.Draw(image), WIDTH, HEIGHT, when, *self.fonts)
        return image

    def test_produces_text_and_border(self):
        image = self._render(datetime(2026, 4, 25, 9, 15))
        # Border + phrase + hour + day line should leave plenty of black ink.
        self.assertGreater(_count_black_pixels(image), 200)

    def test_long_phrase_path_does_not_crash(self):
        # Phrases like "twenty-five past" trip the >12-char branch that
        # switches to the smaller font; make sure that path renders.
        for minute in (25, 27, 32, 35):
            self._render(datetime(2026, 4, 25, 9, minute))

    def test_renders_every_hour_at_known_minute_marks(self):
        for hour in range(24):
            for minute in (0, 15, 30, 45, 58):
                image = self._render(datetime(2026, 4, 25, hour, minute))
                self.assertGreater(
                    _count_black_pixels(image), 100,
                    f"render produced too little ink at {hour:02d}:{minute:02d}",
                )


if __name__ == "__main__":
    unittest.main()
