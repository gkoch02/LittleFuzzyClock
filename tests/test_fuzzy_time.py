"""Tests for fuzzyclock_core.fuzzy_time.

Run with: python3 -m unittest tests.test_fuzzy_time
"""

import unittest

from fuzzyclock_core import DIALECTS, fuzzy_time

# (hour, minute, phrase, hour_str) per dialect. Every dialect pins 9:58 and
# 23:58: the min(..., 11) cap must keep minutes 57-59 on "almost [next hour]".
CASES = {
    "classic": [
        (9, 0, "just after", "nine am"),
        (9, 15, "quarter past", "nine am"),
        (9, 30, "half past", "nine am"),
        (9, 45, "quarter to", "ten am"),
        (9, 57, "almost", "ten am"),
        (9, 59, "almost", "ten am"),
        (11, 45, "quarter to", "twelve pm"),
        (11, 58, "almost", "twelve pm"),
        (23, 58, "almost", "twelve am"),
        (0, 0, "just after", "twelve am"),
        (12, 0, "just after", "twelve pm"),
        (15, 30, "half past", "three pm"),
    ],
    "shakespeare": [
        (9, 0, "'tis just past", "nine of the clock"),
        (9, 15, "'tis a quarter past", "nine of the clock"),
        (9, 30, "'tis half past", "nine of the clock"),
        (9, 45, "a quarter 'fore", "ten of the clock"),
        (9, 58, "almost", "ten of the clock"),
        (23, 58, "almost", "twelve of the clock"),
    ],
    "klingon": [
        (9, 0, "newly forged", "Hut rep"),
        (9, 15, "quarter past", "Hut rep"),
        (9, 30, "half past", "Hut rep"),
        (9, 45, "quarter 'til", "wa'maH rep"),
        (9, 58, "battle nears", "wa'maH rep"),
        (23, 58, "battle nears", "wa'maH cha' rep"),
    ],
    "belter": [
        (9, 0, "just past", "nine bell, ya"),
        (9, 15, "quarter past", "nine bell, ya"),
        (9, 30, "half past", "nine bell, ya"),
        (9, 45, "quarter to da", "ten bell, ya"),
        (9, 58, "almost, ke", "ten bell, ya"),
        (23, 58, "almost, ke", "twelve bell, ya"),
    ],
    # hour_advance_at=5: "halb zehn" = 9:30, so 25-past onward names the next
    # hour. The bucket cliff sits at minute 23 (round(23/5) = 5).
    "german": [
        (9, 0, "kurz nach", "neun"),
        (9, 5, "fünf nach", "neun"),
        (9, 15, "viertel nach", "neun"),
        (9, 20, "zwanzig nach", "neun"),
        (9, 22, "zwanzig nach", "neun"),
        (9, 23, "fünf vor halb", "zehn"),
        (9, 25, "fünf vor halb", "zehn"),
        (9, 30, "halb", "zehn"),
        (9, 35, "fünf nach halb", "zehn"),
        (9, 45, "viertel vor", "zehn"),
        (9, 58, "kurz vor", "zehn"),
        (11, 30, "halb", "zwölf"),
        (0, 30, "halb", "eins"),
        (23, 58, "kurz vor", "zwölf"),
    ],
    # 24h numeric: 9:30 stays on 0900 (default advance), PM hours stay
    # distinct from AM, and 23:58 wraps to 0000.
    "hal": [
        (9, 0, "ON THE MARK", "0900 HOURS"),
        (9, 15, "T+15 MINUTES", "0900 HOURS"),
        (9, 30, "MIDPOINT", "0900 HOURS"),
        (9, 35, "T-25 MINUTES", "1000 HOURS"),
        (9, 45, "T-15 MINUTES", "1000 HOURS"),
        (9, 58, "IMMINENT", "1000 HOURS"),
        (21, 0, "ON THE MARK", "2100 HOURS"),
        (15, 30, "MIDPOINT", "1500 HOURS"),
        (12, 0, "ON THE MARK", "1200 HOURS"),
        (23, 58, "IMMINENT", "0000 HOURS"),
        (0, 0, "ON THE MARK", "0000 HOURS"),
    ],
    "cthulhu": [
        (9, 0, "newly woken", "the ninth hour"),
        (9, 15, "quarter past", "the ninth hour"),
        (9, 30, "the half-hour", "the ninth hour"),
        (9, 45, "quarter 'fore", "the tenth hour"),
        (9, 58, "the stars are right", "the tenth hour"),
        (10, 45, "quarter 'fore", "the eleventh hour"),
        (23, 58, "the stars are right", "the twelfth hour"),
    ],
    # Noon is p.m.; 23:58 rolls to midnight, which is a.m.
    "latin": [
        (9, 0, "modo post", "hora IX a.m."),
        (9, 15, "quadrans post", "hora IX a.m."),
        (9, 30, "media post", "hora IX a.m."),
        (9, 45, "quadrans ante", "hora X a.m."),
        (9, 58, "fere", "hora X a.m."),
        (15, 30, "media post", "hora III p.m."),
        (12, 0, "modo post", "hora XII p.m."),
        (23, 58, "fere", "hora XII a.m."),
    ],
}


class FuzzyTimeTableTests(unittest.TestCase):
    def test_cases(self):
        for dialect, cases in CASES.items():
            for h, m, phrase, hour_str in cases:
                with self.subTest(dialect=dialect, time=f"{h:02d}:{m:02d}"):
                    self.assertEqual(fuzzy_time(h, m, dialect), (phrase, hour_str))

    def test_every_dialect_is_covered(self):
        self.assertEqual(set(CASES), set(DIALECTS))

    def test_default_dialect_is_classic(self):
        self.assertEqual(fuzzy_time(9, 45), fuzzy_time(9, 45, "classic"))

    def test_hour_tables_are_pinned(self):
        # Guard against "fixing" IV -> IIII or "ninth" -> "9th".
        pins = {
            "latin": {4: "IV", 9: "IX", 12: "XII"},
            "cthulhu": {1: "first", 9: "ninth", 11: "eleventh", 12: "twelfth"},
        }
        for dialect, expected in pins.items():
            for hour, word in expected.items():
                with self.subTest(dialect=dialect, hour=hour):
                    self.assertEqual(DIALECTS[dialect]["hours"][hour], word)


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


class DialectValidatorTests(unittest.TestCase):
    def _spec(self, advance):
        return {
            "phrases": ["x"] * 12,
            "hours": {i: str(i) for i in range(1, 13)},
            "format_hour": lambda h, p: h,
            "hour_advance_at": advance,
        }

    def test_advance_below_one_is_rejected(self):
        from fuzzyclock.dialects import _validate_dialects

        with self.assertRaises(ValueError):
            _validate_dialects({"bad": self._spec(0)})

    def test_advance_above_eleven_is_rejected(self):
        from fuzzyclock.dialects import _validate_dialects

        with self.assertRaises(ValueError):
            _validate_dialects({"bad": self._spec(12)})

    def test_advance_at_boundaries_is_accepted(self):
        from fuzzyclock.dialects import _validate_dialects

        _validate_dialects({"a": self._spec(1), "b": self._spec(11)})  # must not raise


if __name__ == "__main__":
    unittest.main()
