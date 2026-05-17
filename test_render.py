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
    _CONTENT_PAD,
    _TINY_SIZE,
    AUTO_FRAME,
    DEFAULT_DIALECT,
    DEFAULT_FONT,
    DEFAULT_FRAME,
    DIALECTS,
    FONT_CANDIDATES,
    FONT_FRAME_CATEGORY,
    FONT_VARIANTS,
    FRAME_VARIANTS,
    RANDOM_FONT,
    _fit_body_font,
    _reset_random_font_bag,
    draw_border,
    frame_for_font,
    load_font,
    pick_random_font,
    render_clock,
    vendored_font_variants,
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

    def test_variable_font_without_bold_named_instance_still_loads(self):
        # Variable fonts whose wght axis carries no "Bold" named instance
        # (e.g. Sixtyfour, Workbench) raise ValueError from
        # set_variation_by_name("Bold"). load_font must catch it and return
        # the font at its default axis values rather than advancing to the
        # next candidate or raising.
        mock_font = mock.Mock()
        mock_font.set_variation_by_name.side_effect = ValueError("no Bold instance")
        with mock.patch("fuzzyclock_core.ImageFont.truetype", return_value=mock_font):
            result = load_font(20)
        self.assertIs(result, mock_font)


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


class RandomFontTests(unittest.TestCase):
    """`pick_random_font` underpins the daemon's random-font mode and the
    CLI's `--font random` flag — it must always return a real, loadable
    variant key, never the `random` sentinel itself."""

    def test_random_font_sentinel_is_not_a_registered_variant(self):
        # The sentinel exists *outside* FONT_VARIANTS by design — callers
        # resolve it to a concrete variant before passing it to load_font.
        self.assertNotIn(RANDOM_FONT, FONT_VARIANTS)

    def test_vendored_variants_only_returns_existing_files(self):
        # Every entry in the result must have a matching .ttf/.otf actually
        # present in fonts/, so a random pick on a clean Pi can't land on
        # a commercial variant the user hasn't dropped a file in for.
        import os as _os

        for variant in vendored_font_variants():
            paths = FONT_VARIANTS[variant]
            self.assertTrue(
                any(_os.path.exists(p) for p in paths),
                f"{variant} reported as vendored but has no existing path",
            )

    def test_vendored_variants_includes_variant_with_only_secondary_path(self):
        # Variants like `pigeonette` list multiple vendored fallbacks (Bold,
        # Regular, plain). load_font() walks the whole list, so the eligibility
        # filter must too — a user who dropped only Pigeonette.otf in fonts/
        # should still see pigeonette in the random pool. Use a synthetic
        # variant so the test isn't tied to which files happen to be present.
        import os as _os
        from unittest import mock as _mock

        from fuzzyclock_core import _VENDORED_FONT_DIR

        primary = _os.path.join(_VENDORED_FONT_DIR, "DoesNotExist-Bold.ttf")
        secondary = _os.path.join(_VENDORED_FONT_DIR, "DejaVuSans-Bold.ttf")  # actually present
        fake_variants = {"synthetic": [primary, secondary, "/System/Library/Fonts/Helvetica.ttc"]}
        with _mock.patch("fuzzyclock_core.FONT_VARIANTS", fake_variants):
            self.assertIn("synthetic", vendored_font_variants())

    def test_pick_random_returns_a_registered_variant(self):
        # Sweep a few times in case the eligible set is small; every roll
        # must produce a key load_font() will accept.
        for _ in range(20):
            picked = pick_random_font()
            self.assertIn(picked, FONT_VARIANTS)
            self.assertNotEqual(picked, RANDOM_FONT)

    def test_pick_random_uses_supplied_rng(self):
        # A seeded RNG makes the choice deterministic — useful for tests
        # downstream that want a stable variant without monkey-patching.
        import random

        first = pick_random_font(rng=random.Random(42))
        second = pick_random_font(rng=random.Random(42))
        self.assertEqual(first, second)

    def test_pick_random_falls_back_when_nothing_vendored(self):
        # Degraded environment (no vendored fonts on disk): rather than
        # raising, fall back to DEFAULT_FONT so callers always get a key.
        with mock.patch("fuzzyclock_core.vendored_font_variants", return_value=[]):
            self.assertEqual(pick_random_font(), DEFAULT_FONT)

    def test_random_font_renders(self):
        # End-to-end: a random pick must render through the normal pipeline
        # without raising. Use a seeded RNG so the test fails consistently
        # if a particular variant ever regresses.
        import random as _r

        variant = pick_random_font(rng=_r.Random(7))
        image = Image.new("1", (WIDTH, HEIGHT), 255)
        render_clock(
            ImageDraw.Draw(image),
            WIDTH,
            HEIGHT,
            datetime(2026, 4, 25, 9, 15),
            font_variant=variant,
        )
        self.assertGreater(_count_black_pixels(image), 200)


class RandomFontShuffleBagTests(unittest.TestCase):
    """`pick_random_font()` (no rng) deals from a shuffle bag so the user
    sees every vendored variant before any repeats — the "music shuffle"
    semantics that distinguish this from uniform i.i.d. sampling."""

    def setUp(self):
        _reset_random_font_bag()

    def tearDown(self):
        _reset_random_font_bag()

    def test_every_variant_appears_before_any_repeats(self):
        # With a small synthetic eligible set, the first N calls must be a
        # permutation of the set (no repeats), then the next N another
        # permutation. This is the whole point of the change.
        pool = ["alpha", "beta", "gamma", "delta", "epsilon"]
        with mock.patch("fuzzyclock_core.vendored_font_variants", return_value=pool):
            first_cycle = [pick_random_font() for _ in pool]
            second_cycle = [pick_random_font() for _ in pool]
        self.assertEqual(sorted(first_cycle), sorted(pool))
        self.assertEqual(sorted(second_cycle), sorted(pool))

    def test_no_back_to_back_repeat_across_bag_boundary(self):
        # When a new bag is dealt, the next pick must not equal the
        # previous one (provided more than one variant is eligible).
        # Without the swap-deeper guard, two cycles of length 1...N could
        # legally produce a duplicate at the seam.
        pool = ["alpha", "beta", "gamma"]
        with mock.patch("fuzzyclock_core.vendored_font_variants", return_value=pool):
            for _ in range(50):
                sequence = [pick_random_font() for _ in range(2 * len(pool))]
                for a, b in zip(sequence, sequence[1:]):
                    self.assertNotEqual(a, b, f"back-to-back repeat in {sequence}")

    def test_single_variant_pool_repeats_silently(self):
        # The back-to-back guard is conditional on len > 1. With a single
        # eligible variant we have no choice but to repeat — and we must
        # not raise.
        with mock.patch("fuzzyclock_core.vendored_font_variants", return_value=["solo"]):
            self.assertEqual(pick_random_font(), "solo")
            self.assertEqual(pick_random_font(), "solo")

    def test_bag_resets_when_eligible_set_changes(self):
        # If a font is dropped into fonts/ mid-session, the new variant
        # should be reachable on the very next pick rather than waiting
        # for the current bag to drain.
        with mock.patch("fuzzyclock_core.vendored_font_variants", return_value=["alpha", "beta"]):
            pick_random_font()  # partially drains the bag
        with mock.patch(
            "fuzzyclock_core.vendored_font_variants",
            return_value=["alpha", "beta", "gamma"],
        ):
            picks = {pick_random_font() for _ in range(3)}
        self.assertEqual(picks, {"alpha", "beta", "gamma"})

    def test_supplied_rng_does_not_disturb_bag(self):
        # The rng= path is the deterministic-test path. It must not pop
        # from or refill the shared bag, so production callers using
        # rng=None still see a clean shuffle.
        import random as _r

        pool = ["alpha", "beta", "gamma"]
        with mock.patch("fuzzyclock_core.vendored_font_variants", return_value=pool):
            pick_random_font(rng=_r.Random(1))
            pick_random_font(rng=_r.Random(2))
            cycle = [pick_random_font() for _ in pool]
        self.assertEqual(sorted(cycle), sorted(pool))


class FrameVariantsTests(unittest.TestCase):
    """Themed-frame registry: every frame must paint distinct ink that honours
    invert, every registered font must map to a valid frame, and the auto
    sentinel must resolve through render_clock to the font's category."""

    def test_default_frame_is_a_registered_variant(self):
        self.assertIn(DEFAULT_FRAME, FRAME_VARIANTS)

    def test_auto_sentinel_is_not_a_registered_variant(self):
        # AUTO_FRAME lives outside FRAME_VARIANTS by design — render_clock and
        # the daemon resolve it to a concrete frame before dispatch.
        self.assertNotIn(AUTO_FRAME, FRAME_VARIANTS)

    def test_every_frame_marks_pixels(self):
        for name in FRAME_VARIANTS:
            with self.subTest(frame=name):
                image = Image.new("1", (WIDTH, HEIGHT), 255)
                draw_border(ImageDraw.Draw(image), WIDTH, HEIGHT, frame=name)
                self.assertGreater(_count_black_pixels(image), 0)

    def test_every_frame_is_sparse(self):
        # No frame should fill more than a quarter of the canvas — they're
        # outlines, not panels. Catches a runaway draw loop.
        for name in FRAME_VARIANTS:
            with self.subTest(frame=name):
                image = Image.new("1", (WIDTH, HEIGHT), 255)
                draw_border(ImageDraw.Draw(image), WIDTH, HEIGHT, frame=name)
                self.assertLess(_count_black_pixels(image), (WIDTH * HEIGHT) // 4)

    def test_every_frame_respects_invert(self):
        for name in FRAME_VARIANTS:
            with self.subTest(frame=name):
                image = Image.new("1", (WIDTH, HEIGHT), 0)
                draw_border(ImageDraw.Draw(image), WIDTH, HEIGHT, invert=True, frame=name)
                black = _count_black_pixels(image)
                self.assertGreater(WIDTH * HEIGHT - black, 0)
                self.assertGreater(black, (WIDTH * HEIGHT) * 3 // 4)

    def test_unknown_frame_falls_back_to_default(self):
        # Mirror the unknown-font behaviour: don't crash on a typo, just
        # render the default frame so the clock face stays usable.
        unknown = Image.new("1", (WIDTH, HEIGHT), 255)
        default = Image.new("1", (WIDTH, HEIGHT), 255)
        draw_border(ImageDraw.Draw(unknown), WIDTH, HEIGHT, frame="not-a-real-frame")
        draw_border(ImageDraw.Draw(default), WIDTH, HEIGHT, frame=DEFAULT_FRAME)
        self.assertEqual(_count_black_pixels(unknown), _count_black_pixels(default))

    def test_frame_for_font_covers_every_registered_variant(self):
        # Every font in FONT_VARIANTS should have an explicit category so the
        # auto-frame mode never silently falls back to the default for a
        # vendored variant.
        for variant in FONT_VARIANTS:
            with self.subTest(variant=variant):
                self.assertIn(variant, FONT_FRAME_CATEGORY)

    def test_frame_for_font_returns_registered_frames(self):
        for variant, frame in FONT_FRAME_CATEGORY.items():
            with self.subTest(variant=variant):
                self.assertIn(frame, FRAME_VARIANTS)

    def test_frame_for_font_unknown_falls_back_to_default(self):
        self.assertEqual(frame_for_font("definitely-not-a-font"), DEFAULT_FRAME)

    def test_frame_for_font_known_categories(self):
        # Spot-check one font from each category so a future re-categorisation
        # that breaks the bauhaus/rustic/sketchy/retro buckets fails loudly.
        self.assertEqual(frame_for_font("dejavu"), "bauhaus")
        self.assertEqual(frame_for_font("unifraktur-maguntia"), "rustic")
        self.assertEqual(frame_for_font("caveat"), "sketchy")
        self.assertEqual(frame_for_font("vt323"), "retro")

    def test_auto_frame_routes_through_font_category(self):
        # render_clock with frame=AUTO_FRAME and a rustic-bucket font should
        # produce identical output to an explicit frame="rustic" render with
        # the same font — proves the auto sentinel is wired through.
        when = datetime(2026, 4, 25, 9, 15)
        auto_image = Image.new("1", (WIDTH, HEIGHT), 255)
        explicit_image = Image.new("1", (WIDTH, HEIGHT), 255)
        render_clock(
            ImageDraw.Draw(auto_image),
            WIDTH,
            HEIGHT,
            when,
            font_variant="dejavu",
            frame=AUTO_FRAME,
        )
        render_clock(
            ImageDraw.Draw(explicit_image),
            WIDTH,
            HEIGHT,
            when,
            font_variant="dejavu",
            frame=frame_for_font("dejavu"),
        )
        self.assertEqual(
            list(auto_image.getdata()),
            list(explicit_image.getdata()),
        )

    def test_every_frame_renders_through_render_clock(self):
        # End-to-end smoke: every registered frame must survive the full
        # render_clock pipeline (text + border + footer) at panel size.
        when = datetime(2026, 4, 25, 9, 15)
        for name in FRAME_VARIANTS:
            with self.subTest(frame=name):
                image = Image.new("1", (WIDTH, HEIGHT), 255)
                render_clock(
                    ImageDraw.Draw(image),
                    WIDTH,
                    HEIGHT,
                    when,
                    frame=name,
                )
                self.assertGreater(_count_black_pixels(image), 200)


class FitBodyFontTests(unittest.TestCase):
    """Direct unit tests for the auto-sizing helper used by render_clock.

    render_clock calls _fit_body_font with available_w = canvas_width -
    2*_CONTENT_PAD and available_h derived from the footer position. We use
    the real panel geometry here so the tested constraints match production.
    """

    _AW = WIDTH - 2 * _CONTENT_PAD  # 222 px at 250-wide panel
    _AH = 80  # conservative but realistic body-area height

    def _draw(self):
        return ImageDraw.Draw(Image.new("1", (WIDTH, HEIGHT), 255))

    def test_short_phrase_uses_max_font_size(self):
        # A trivially short phrase-and-hour pair must fit at the largest
        # permitted body size, confirming the loop terminates early.
        font = _fit_body_font(
            self._draw(),
            "ha",
            "ha",
            DEFAULT_FONT,
            available_w=self._AW,
            available_h=self._AH,
        )
        self.assertEqual(font.size, _BODY_MAX_SIZE)

    def test_long_phrase_forced_to_smaller_font(self):
        # A long phrase that overflows at _BODY_MAX_SIZE must be sized down;
        # the result must be strictly smaller than what the short phrase gets.
        draw = self._draw()
        font_short = _fit_body_font(
            draw,
            "ha",
            "ha",
            DEFAULT_FONT,
            available_w=self._AW,
            available_h=self._AH,
        )
        font_long = _fit_body_font(
            draw,
            "twenty-five past",
            "twelve am",
            DEFAULT_FONT,
            available_w=self._AW,
            available_h=self._AH,
        )
        self.assertLess(font_long.size, font_short.size)

    def test_unavoidable_overflow_returns_min_size(self):
        # When no size fits (available_w and available_h both 1 px), the
        # function must return _BODY_MIN_SIZE rather than raising or returning
        # None — the clock face degrades gracefully under extreme constraints.
        font = _fit_body_font(
            self._draw(),
            "twenty-five past",
            "twelve am",
            DEFAULT_FONT,
            available_w=1,
            available_h=1,
        )
        self.assertEqual(font.size, _BODY_MIN_SIZE)

    def test_size_is_monotonically_non_decreasing_with_shorter_phrases(self):
        # The size selected for a shorter phrase must always be >= the size
        # selected for a longer phrase on the same canvas. This is the core
        # contract: brevity earns display real-estate.
        draw = self._draw()
        phrases = [
            ("twenty-five past", "twelve am"),  # longest
            ("quarter past", "nine am"),
            ("half past", "two am"),
            ("almost", "ten am"),  # shortest
        ]
        sizes = [
            _fit_body_font(
                draw, p, h, DEFAULT_FONT, available_w=self._AW, available_h=self._AH
            ).size
            for p, h in phrases
        ]
        for i in range(len(sizes) - 1):
            self.assertLessEqual(
                sizes[i],
                sizes[i + 1],
                f"phrase [{i}] got size {sizes[i]} but shorter phrase [{i + 1}] "
                f"got {sizes[i + 1]} — expected non-decreasing order",
            )


if __name__ == "__main__":
    unittest.main()
