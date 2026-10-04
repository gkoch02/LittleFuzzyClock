"""Importing the daemon must have no side effects: no font loads, no config read.

Runs in a fresh interpreter so the result can't depend on what other tests
already did to the shared module. A plain import failure is caught anyway by
test_daemon.py failing to load.
"""

import os
import subprocess
import sys
import unittest

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_PROBE = """
import fuzzyclock.fonts as fonts

def _forbidden(*a, **k):
    raise AssertionError("font work at import time")

fonts.load_font = _forbidden
fonts.pick_random_font = _forbidden
import builtins
_open = builtins.open

def _no_config(path, *a, **k):
    if str(path).endswith("fuzzyclock_config.yaml"):
        raise AssertionError("config read at import time")
    return _open(path, *a, **k)

builtins.open = _no_config
import fuzzyclock_daemon as d
assert d._fonts_ready is False
"""


class DaemonImportTests(unittest.TestCase):
    def test_import_has_no_font_or_config_side_effects(self):
        result = subprocess.run(
            [sys.executable, "-c", _PROBE],
            cwd=_REPO,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
