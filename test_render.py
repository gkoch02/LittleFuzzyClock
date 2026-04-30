"""Smoke tests for the rendering helpers in fuzzyclock_core.

These don't try to assert pixel-exact output (which would be brittle
against font hinting). They just confirm the helpers run end-to-end and
produce something that looks like a real render rather than a blank
canvas.

Run with: python3 -m unittest test_render
"""

import unittest
from datetime import datetime
from unittest import mock

from PIL import Image, ImageDraw

from fuzzyclock_core import DIALECTS, draw_border, load_font, render_clock

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

    def test_inverted_border_draws_in_white(self):
        # Black canvas with invert=True should leave a sparse white border —
        # i.e. some white pixels appear, but the bulk of the canvas stays black.
        image = Image.new("1", (WIDTH, HEIGHT), 0)
        draw_border(ImageDraw.Draw(image), WIDTH, HEIGHT, invert=True)
        black = _count_black_pixels(image)
        self.assertGreater(WIDTH * HEIGHT - black, 0)
        self.assertGreater(black, (WIDTH * HEIGHT) * 3 // 4)


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
                    _count_black_pixels(image),
                    100,
                    f"render produced too little ink at {hour:02d}:{minute:02d}",
                )

    def test_inverted_render_swaps_ink(self):
        # Same scene rendered normally vs. inverted should be (near-)complementary:
        # the count of black pixels in one should roughly equal the count of
        # white pixels in the other, since invert just swaps fill colours.
        normal = self._render(datetime(2026, 4, 25, 9, 15))
        inverted = Image.new("1", (WIDTH, HEIGHT), 0)
        render_clock(
            ImageDraw.Draw(inverted),
            WIDTH,
            HEIGHT,
            datetime(2026, 4, 25, 9, 15),
            *self.fonts,
            invert=True,
        )
        normal_black = _count_black_pixels(normal)
        inverted_white = WIDTH * HEIGHT - _count_black_pixels(inverted)
        self.assertEqual(normal_black, inverted_white)

    def test_shakespeare_dialect_renders(self):
        # Shakespeare phrases like "'tis a quarter past" trip the long-phrase
        # branch that switches to font_small. Confirm it puts ink on canvas.
        image = Image.new("1", (WIDTH, HEIGHT), 255)
        render_clock(
            ImageDraw.Draw(image),
            WIDTH,
            HEIGHT,
            datetime(2026, 4, 25, 9, 15),
            *self.fonts,
            dialect="shakespeare",
        )
        self.assertGreater(_count_black_pixels(image), 200)

    def test_german_dialect_renders(self):
        # German is the only dialect with non-ASCII glyphs (ä, ö, ü). If the
        # font fallback ever lands on a face missing them we'd render tofu
        # boxes; this asserts real ink lands on canvas.
        image = Image.new("1", (WIDTH, HEIGHT), 255)
        render_clock(
            ImageDraw.Draw(image),
            WIDTH,
            HEIGHT,
            datetime(2026, 4, 25, 9, 30),
            *self.fonts,
            dialect="german",
        )
        self.assertGreater(_count_black_pixels(image), 200)


class AllDialectsRenderTests(unittest.TestCase):
    """Sweep every registered dialect through render_clock at a few times of
    day. Catches dialect-specific glyph or layout regressions (e.g. a new
    dialect with characters DejaVu doesn't have, or a hour_str so long that
    it overflows the canvas). Every dialect's "almost X" slot has a long-ish
    hour string, which trips the >12-char small-font branch differently."""

    def setUp(self):
        self.fonts = (load_font(28), load_font(22), load_font(14))

    def test_every_dialect_renders_at_several_times(self):
        sample_times = [
            datetime(2026, 4, 25, 9, 0),  # on-the-hour slot
            datetime(2026, 4, 25, 9, 30),  # half-hour slot
            datetime(2026, 4, 25, 9, 58),  # "almost"/cap-at-11 slot
            datetime(2026, 4, 25, 21, 15),  # PM slot (HAL/Latin handle this differently)
        ]
        for dialect in sorted(DIALECTS):
            for when in sample_times:
                with self.subTest(dialect=dialect, when=when.isoformat(timespec="minutes")):
                    image = Image.new("1", (WIDTH, HEIGHT), 255)
                    render_clock(
                        ImageDraw.Draw(image),
                        WIDTH,
                        HEIGHT,
                        when,
                        *self.fonts,
                        dialect=dialect,
                    )
                    self.assertGreater(
                        _count_black_pixels(image),
                        100,
                        f"{dialect} produced too little ink at {when}",
                    )


class LoadFontFailureTests(unittest.TestCase):
    def test_no_candidate_paths_raises_systemexit(self):
        # The clearest failure mode for a missing font: SystemExit with a
        # message listing every path tried. Ensures the daemon fails loud
        # rather than rendering with PIL's default bitmap fallback.
        with mock.patch("fuzzyclock_core.ImageFont.truetype", side_effect=OSError("nope")):
            with self.assertRaises(SystemExit) as cm:
                load_font(20)
        self.assertIn("No usable font", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
