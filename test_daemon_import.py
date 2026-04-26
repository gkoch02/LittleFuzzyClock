"""Smoke-test: the daemon module imports cleanly without GPIO/EPD installed.

CI runs without gpiozero or waveshare_epd, so this catches accidental
top-level breakage in fuzzyclock_daemon.py (syntax errors, eager hardware
calls at module scope, missing imports) that the unit tests below wouldn't
otherwise notice. The import itself is the assertion.
"""

import unittest


class DaemonImportTests(unittest.TestCase):
    def test_imports_without_hardware(self):
        import fuzzyclock_daemon  # must not raise

        # A few public symbols we expect to still be available.
        self.assertTrue(callable(fuzzyclock_daemon.current_mode))
        self.assertTrue(callable(fuzzyclock_daemon._sleep_to_next_tick))
        self.assertIsNotNone(fuzzyclock_daemon.epd_lock)
        self.assertIsNotNone(fuzzyclock_daemon._stop_event)


if __name__ == "__main__":
    unittest.main()
