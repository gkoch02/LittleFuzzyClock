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

from fuzzyclock_core import (
    _BODY_MAX_SIZE,
    _BODY_MIN_SIZE,
    _TINY_SIZE,
    DEFAULT_DIALECT,
    DEFAULT_FONT,
    DIALECTS,
    FONT_CANDIDATES,
    FONT_VARIANTS,
    draw_border,
    load_font,
    render_clock,
)

WIDTH, HEIGHT = 250, 122  # landscape orientation of the 2.13" V4 panel


def _count_black_pixels(image):
    # histogram()[0] is the count of value-0 pixels, which for a mode "1"
    # image is exactly the black-pixel count. Avoids the getdata() warning
    # in newer Pillow releases.
    return image.histogram()[0]


class LoadFontTests(unittest.TestCase):
    def test_returns_font_for_each_size_used_by_the_app(self):
        # Body font ranges from _BODY_MIN_SIZE to _BODY_MAX_SIZE; tiny and
        # goodnight are fixed at _TINY_SIZE and 24 respectively.
        for size in (_BODY_MIN_SIZE, _BODY_MAX_SIZE, _TINY_SIZE, 24):
            self.assertIsNotNone(load_font(size))

    def test_default_variant_walks_legacy_font_candidates(self):
        # variant=None and variant="dejavu" must attempt the same paths in
        # the same order so the legacy fallback chain isn't accidentally
        # broken when callers start passing a variant explicitly.
        attempted_default = []
        attempted_dejavu = []

        def fake_truetype_default(path, size):
            attempted_default.append(path)
            raise OSError("nope")

        def fake_truetype_dejavu(path, size):
            attempted_dejavu.append(path)
            raise OSError("nope")

        with mock.patch("fuzzyclock_core.ImageFont.truetype", side_effect=fake_truetype_default):
            with self.assertRaises(SystemExit):
                load_font(20)
        with mock.patch("fuzzyclock_core.ImageFont.truetype", side_effect=fake_truetype_dejavu):
            with self.assertRaises(SystemExit):
                load_font(20, variant="dejavu")
        self.assertEqual(attempted_default, FONT_CANDIDATES)
        self.assertEqual(attempted_dejavu, FONT_CANDIDATES)

    def test_each_variant_attempts_its_registered_paths(self):
        # Mock truetype so we can assert the right candidate list is walked
        # for each variant without requiring every font to be installed.
        for variant, paths in FONT_VARIANTS.items():
            with self.subTest(variant=variant):
                attempted = []

                def fake_truetype(path, size, _attempted=attempted):
                    _attempted.append(path)
                    raise OSError("nope")

                with mock.patch("fuzzyclock_core.ImageFont.truetype", side_effect=fake_truetype):
                    with self.assertRaises(SystemExit):
                        load_font(20, variant=variant)
                self.assertEqual(attempted, list(paths))

    def test_default_font_constant_is_a_registered_variant(self):
        self.assertIn(DEFAULT_FONT, FONT_VARIANTS)


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
    def _render(self, when, dialect=DEFAULT_DIALECT, invert=False):
        bg = 0 if invert else 255
        image = Image.new("1", (WIDTH, HEIGHT), bg)
        render_clock(ImageDraw.Draw(image), WIDTH, HEIGHT, when, dialect=dialect, invert=invert)
        return image

    def test_produces_text_and_border(self):
        image = self._render(datetime(2026, 4, 25, 9, 15))
        # Border + phrase + hour + day line should leave plenty of black ink.
        self.assertGreater(_count_black_pixels(image), 200)

    def test_long_phrase_renders(self):
        # Long phrases like "twenty-five past" auto-size to a smaller font;
        # confirm they render without error and produce ink.
        for minute in (25, 27, 32, 35):
            self._render(datetime(2026, 4, 25, 9, minute))

    def test_short_phrase_renders_larger(self):
        # Short phrases like "almost" should use a larger auto-sized font than
        # long ones; both must produce ink on canvas.
        short = self._render(datetime(2026, 4, 25, 8, 58))  # "almost"
        long_ = self._render(datetime(2026, 4, 25, 9, 27))  # "twenty-five past"
        self.assertGreater(_count_black_pixels(short), 100)
        self.assertGreater(_count_black_pixels(long_), 100)

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
        inverted = self._render(datetime(2026, 4, 25, 9, 15), invert=True)
        normal_black = _count_black_pixels(normal)
        inverted_white = WIDTH * HEIGHT - _count_black_pixels(inverted)
        self.assertEqual(normal_black, inverted_white)

    def test_shakespeare_dialect_renders(self):
        image = self._render(datetime(2026, 4, 25, 9, 15), dialect="shakespeare")
        self.assertGreater(_count_black_pixels(image), 200)

    def test_german_dialect_renders(self):
        # German is the only dialect with non-ASCII glyphs (ä, ö, ü). If the
        # font fallback ever lands on a face missing them we'd render tofu
        # boxes; this asserts real ink lands on canvas.
        image = self._render(datetime(2026, 4, 25, 9, 30), dialect="german")
        self.assertGreater(_count_black_pixels(image), 200)


class AllDialectsRenderTests(unittest.TestCase):
    """Sweep every registered dialect through render_clock at a few times of
    day. Catches dialect-specific glyph or layout regressions (e.g. a new
    dialect with characters DejaVu doesn't have, or a hour_str so long that
    it overflows the canvas)."""

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

    def test_unknown_variant_raises_keyerror(self):
        # The daemon validates user input upstream; a KeyError here indicates
        # a programming bug (caller passed an unregistered variant directly).
        with self.assertRaises(KeyError):
            load_font(20, variant="comic-sans")

    def test_failure_message_lists_variant_paths(self):
        # When a specific variant fails to load, the SystemExit message must
        # name the variant and list its tried paths — not the global default
        # candidates — so the user can see what was attempted.
        with mock.patch("fuzzyclock_core.ImageFont.truetype", side_effect=OSError("nope")):
            with self.assertRaises(SystemExit) as cm:
                load_font(20, variant="roboto-slab")
        message = str(cm.exception)
        self.assertIn("roboto-slab", message)
        for path in FONT_VARIANTS["roboto-slab"]:
            self.assertIn(path, message)


if __name__ == "__main__":
    unittest.main()
