"""Shared logic for the fuzzy clock — the stable public surface.

The implementation lives in focused modules under ``fuzzyclock/``:

* ``fuzzyclock.dialects`` — the phrasing tables and ``fuzzy_time``
* ``fuzzyclock.fonts``    — the font registry, ``load_font``, random-font bag
* ``fuzzyclock.frames``   — border styles and the font-to-frame mapping
* ``fuzzyclock.render``   — clock-face layout
* ``fuzzyclock.sun``      — the NOAA sunrise/sunset approximation

This module re-exports the public names so callers (the daemon,
fuzzyclock_preview.py, and the tests) have one stable import location.
Private names are deliberately *not* re-exported — import those from the
module that owns them, so their dependency stays visible.
"""

from fuzzyclock.dialects import (  # noqa: F401
    DEFAULT_DIALECT,
    DIALECTS,
    HOUR_WORDS,
    fuzzy_time,
)
from fuzzyclock.fonts import (  # noqa: F401
    DEFAULT_FONT,
    FONT_CANDIDATES,
    FONT_VARIANTS,
    RANDOM_FONT,
    load_font,
    pick_random_font,
    vendored_font_variants,
)
from fuzzyclock.frames import (  # noqa: F401
    AUTO_FRAME,
    DEFAULT_FRAME,
    FONT_FRAME_CATEGORY,
    FRAME_VARIANTS,
    draw_border,
    frame_for_font,
)
from fuzzyclock.render import render_clock  # noqa: F401
from fuzzyclock.sun import sun_times  # noqa: F401
