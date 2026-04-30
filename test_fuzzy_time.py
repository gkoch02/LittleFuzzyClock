"""Tests for fuzzyclock_core.fuzzy_time.

Run with: python3 -m unittest test_fuzzy_time
"""

import unittest

from fuzzyclock_core import DIALECTS, fuzzy_time


class FuzzyTimeTests(unittest.TestCase):
    def test_on_the_hour(self):
        self.assertEqual(fuzzy_time(9, 0), ("just after", "nine am"))

    def test_quarter_past(self):
        self.assertEqual(fuzzy_time(9, 15), ("quarter past", "nine am"))

    def test_half_past(self):
        self.assertEqual(fuzzy_time(9, 30), ("half past", "nine am"))

    def test_quarter_to_advances_hour(self):
        self.assertEqual(fuzzy_time(9, 45), ("quarter to", "ten am"))

    def test_almost_next_hour(self):
        # Minutes 57-59 should round up into "almost [next hour]" and
        # NOT wrap back to "just after [current hour]" via % 12.
        self.assertEqual(fuzzy_time(9, 57), ("almost", "ten am"))
        self.assertEqual(fuzzy_time(9, 59), ("almost", "ten am"))

    def test_noon_rollover(self):
        self.assertEqual(fuzzy_time(11, 58), ("almost", "twelve pm"))

    def test_midnight_rollover(self):
        self.assertEqual(fuzzy_time(23, 58), ("almost", "twelve am"))

    def test_midnight(self):
        self.assertEqual(fuzzy_time(0, 0), ("just after", "twelve am"))

    def test_noon(self):
        self.assertEqual(fuzzy_time(12, 0), ("just after", "twelve pm"))

    def test_pm_suffix(self):
        self.assertEqual(fuzzy_time(15, 30), ("half past", "three pm"))

    def test_am_to_pm_boundary(self):
        # 11:45 rounds to "quarter to twelve pm"
        self.assertEqual(fuzzy_time(11, 45), ("quarter to", "twelve pm"))

    def test_every_minute_roundtrips(self):
        # Smoke test: every minute of every hour should produce a valid
        # (phrase, hour) tuple with no exceptions and known vocabulary.
        valid_phrases = {
            "just after", "a little past", "ten past", "quarter past",
            "twenty past", "twenty-five past", "half past",
            "twenty-five to", "twenty to", "quarter to", "ten to", "almost",
        }
        for h in range(24):
            for m in range(60):
                phrase, hour_str = fuzzy_time(h, m)
                self.assertIn(phrase, valid_phrases, f"{h:02d}:{m:02d}")
                self.assertTrue(hour_str.endswith(" am") or hour_str.endswith(" pm"))


class ShakespeareDialectTests(unittest.TestCase):
    def test_on_the_hour(self):
        self.assertEqual(
            fuzzy_time(9, 0, "shakespeare"),
            ("'tis just past", "nine of the clock"),
        )

    def test_quarter_past(self):
        self.assertEqual(
            fuzzy_time(9, 15, "shakespeare"),
            ("'tis a quarter past", "nine of the clock"),
        )

    def test_half_past(self):
        self.assertEqual(
            fuzzy_time(9, 30, "shakespeare"),
            ("'tis half past", "nine of the clock"),
        )

    def test_quarter_to_advances_hour(self):
        self.assertEqual(
            fuzzy_time(9, 45, "shakespeare"),
            ("a quarter 'fore", "ten of the clock"),
        )

    def test_almost_next_hour_does_not_wrap(self):
        # The min(..., 11) cap must hold for all dialects.
        self.assertEqual(
            fuzzy_time(9, 58, "shakespeare"),
            ("almost", "ten of the clock"),
        )

    def test_midnight_rollover(self):
        self.assertEqual(
            fuzzy_time(23, 58, "shakespeare"),
            ("almost", "twelve of the clock"),
        )


class KlingonDialectTests(unittest.TestCase):
    def test_on_the_hour(self):
        self.assertEqual(fuzzy_time(9, 0, "klingon"), ("newly forged", "Hut rep"))

    def test_quarter_past(self):
        self.assertEqual(fuzzy_time(9, 15, "klingon"), ("quarter past", "Hut rep"))

    def test_half_past(self):
        self.assertEqual(fuzzy_time(9, 30, "klingon"), ("half past", "Hut rep"))

    def test_quarter_to_advances_hour(self):
        # 10 in Klingon is "wa'maH".
        self.assertEqual(fuzzy_time(9, 45, "klingon"), ("quarter 'til", "wa'maH rep"))

    def test_almost_next_hour_does_not_wrap(self):
        self.assertEqual(fuzzy_time(9, 58, "klingon"), ("battle nears", "wa'maH rep"))

    def test_midnight_rollover_uses_klingon_twelve(self):
        # 12 in Klingon is "wa'maH cha'".
        self.assertEqual(fuzzy_time(23, 58, "klingon"), ("battle nears", "wa'maH cha' rep"))


class BelterDialectTests(unittest.TestCase):
    def test_on_the_hour(self):
        self.assertEqual(fuzzy_time(9, 0, "belter"), ("just past", "nine bell, ya"))

    def test_quarter_past(self):
        self.assertEqual(fuzzy_time(9, 15, "belter"), ("quarter past", "nine bell, ya"))

    def test_half_past(self):
        self.assertEqual(fuzzy_time(9, 30, "belter"), ("half past", "nine bell, ya"))

    def test_quarter_to_advances_hour(self):
        self.assertEqual(fuzzy_time(9, 45, "belter"), ("quarter to da", "ten bell, ya"))

    def test_almost_next_hour_does_not_wrap(self):
        self.assertEqual(fuzzy_time(9, 58, "belter"), ("almost, ke", "ten bell, ya"))

    def test_midnight_rollover(self):
        self.assertEqual(fuzzy_time(23, 58, "belter"), ("almost, ke", "twelve bell, ya"))


class GermanDialectTests(unittest.TestCase):
    def test_on_the_hour(self):
        self.assertEqual(fuzzy_time(9, 0, "german"), ("kurz nach", "neun"))

    def test_five_past(self):
        self.assertEqual(fuzzy_time(9, 5, "german"), ("fünf nach", "neun"))

    def test_quarter_past(self):
        self.assertEqual(fuzzy_time(9, 15, "german"), ("viertel nach", "neun"))

    def test_twenty_past_keeps_current_hour(self):
        self.assertEqual(fuzzy_time(9, 20, "german"), ("zwanzig nach", "neun"))

    def test_twenty_five_past_advances_to_next_hour(self):
        # "fünf vor halb zehn" = five before half-ten = 9:25.
        self.assertEqual(fuzzy_time(9, 25, "german"), ("fünf vor halb", "zehn"))

    def test_half_advances_to_next_hour(self):
        # "halb zehn" = half-to-ten = 9:30; this is the defining quirk of
        # German time and the reason for the hour_advance_at=5 hook.
        self.assertEqual(fuzzy_time(9, 30, "german"), ("halb", "zehn"))

    def test_thirty_five_past_anchors_on_next_hour(self):
        self.assertEqual(fuzzy_time(9, 35, "german"), ("fünf nach halb", "zehn"))

    def test_quarter_to_advances_hour(self):
        self.assertEqual(fuzzy_time(9, 45, "german"), ("viertel vor", "zehn"))

    def test_almost_next_hour_does_not_wrap(self):
        self.assertEqual(fuzzy_time(9, 58, "german"), ("kurz vor", "zehn"))

    def test_half_past_eleven_rolls_into_twelve(self):
        # 11:30 is "halb zwölf" — uses the German word for twelve.
        self.assertEqual(fuzzy_time(11, 30, "german"), ("halb", "zwölf"))

    def test_midnight_rollover(self):
        self.assertEqual(fuzzy_time(23, 58, "german"), ("kurz vor", "zwölf"))


class AllDialectsRoundtripTests(unittest.TestCase):
    def test_every_minute_every_dialect(self):
        # Every dialect must produce a valid phrase from its own table for
        # every minute of every hour, with no exceptions.
        for dialect, spec in DIALECTS.items():
            valid = set(spec["phrases"])
            for h in range(24):
                for m in range(60):
                    phrase, hour_str = fuzzy_time(h, m, dialect)
                    self.assertIn(phrase, valid, f"{dialect} {h:02d}:{m:02d}")
                    self.assertTrue(hour_str, f"{dialect} {h:02d}:{m:02d}")

    def test_unknown_dialect_raises(self):
        with self.assertRaises(KeyError):
            fuzzy_time(9, 0, "esperanto")


if __name__ == "__main__":
    unittest.main()
