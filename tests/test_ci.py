"""The Pillow floor job in CI tests the versions the code has to run on."""

import os
import re
import unittest

import yaml

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Debian Bookworm's python3-pil, which deploy.sh installs on the Pi.
_PI_PILLOW = "9.4.0"


def _floor_pins():
    with open(os.path.join(_REPO, ".github", "workflows", "test.yml")) as f:
        workflow = yaml.safe_load(f)
    return workflow["jobs"]["test-pillow-floor"]["strategy"]["matrix"]["pillow"]


def _requirements_floor():
    with open(os.path.join(_REPO, "requirements.txt")) as f:
        for line in f:
            match = re.match(r"Pillow>=([\d.]+)", line.strip())
            if match:
                return match.group(1)
    raise AssertionError("no Pillow>= line in requirements.txt")


class PillowFloorTests(unittest.TestCase):
    def test_floor_job_pins_each_supported_minimum(self):
        floor = _requirements_floor()
        # requirements.txt writes "13"; pip's exact pin is "13.0.0".
        floor = ".".join((floor.split(".") + ["0", "0"])[:3])
        for label, version in (("the Pi's apt Pillow", _PI_PILLOW), ("requirements.txt", floor)):
            with self.subTest(label):
                self.assertIn(version, _floor_pins())

    def test_test_job_has_no_pillow_axis(self):
        # The required contexts "test (3.11)" / "test (3.12)" need a
        # python-version-only matrix; see the comment above test-pillow-floor.
        with open(os.path.join(_REPO, ".github", "workflows", "test.yml")) as f:
            workflow = yaml.safe_load(f)
        self.assertEqual(list(workflow["jobs"]["test"]["strategy"]["matrix"]), ["python-version"])


if __name__ == "__main__":
    unittest.main()
