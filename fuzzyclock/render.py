"""Clock-face layout: body-font auto-sizing and render_clock().

The integration point of the package — the only module that depends on the
others (fonts, frames, dialects).
"""

from fuzzyclock.dialects import DEFAULT_DIALECT, fuzzy_time
from fuzzyclock.fonts import DEFAULT_FONT, load_font
from fuzzyclock.frames import (
    _CONTENT_PAD,
    AUTO_FRAME,
    draw_border,
    frame_for_font,
)

_TINY_SIZE = 14
_BODY_MAX_SIZE = 40
_BODY_MIN_SIZE = 14
# Vertical gap between the phrase line and the hour line. Shared by
# _fit_body_font's height check and render_clock's actual layout so the
# size that "fits" matches what gets drawn — keep them reading the same value.
_LINE_GAP = 4


def _fit_body_font(draw, phrase, hour_str, variant, available_w, available_h):
    """Return the largest font where both text lines fit within the constraints.

    Tries sizes from _BODY_MAX_SIZE down to _BODY_MIN_SIZE. Both the width of
    each line and the total two-line ink height are checked, so the chosen size
    fits on the e-ink canvas regardless of phrase length or font metrics.
    """
    for size in range(_BODY_MAX_SIZE, _BODY_MIN_SIZE - 1, -1):
        font = load_font(size, variant=variant)
        if (
            draw.textlength(phrase, font=font) <= available_w
            and draw.textlength(hour_str, font=font) <= available_w
        ):
            pb = draw.textbbox((0, 0), phrase, font=font)
            hb = draw.textbbox((0, 0), hour_str, font=font)
            if (pb[3] - pb[1]) + _LINE_GAP + (hb[3] - hb[1]) <= available_h:
                return font
    return load_font(_BODY_MIN_SIZE, variant=variant)


def render_clock(
    draw,
    width,
    height,
    now,
    font_variant=DEFAULT_FONT,
    dialect=DEFAULT_DIALECT,
    invert=False,
    frame=AUTO_FRAME,
):
    """Draw the full clock face (border + phrase + hour + day line) onto `draw`.

    Body font size is chosen automatically: the largest size (up to
    _BODY_MAX_SIZE pt) at which both text lines fit within the canvas width and
    the two-line block fits above the footer. Short phrases like "almost" render
    noticeably larger than long ones like "twenty-five past".

    When `invert` is True the foreground is white (255) instead of black; the
    caller is responsible for filling the canvas with the matching background
    colour before calling this helper.

    `frame` selects the border style (a key in FRAME_VARIANTS, or AUTO_FRAME
    to derive one from `font_variant` via frame_for_font()). The default
    AUTO_FRAME pairs each font with a complementary border without any extra
    config from the caller.
    """
    ink = 255 if invert else 0
    phrase, hour_str = fuzzy_time(now.hour, now.minute, dialect)
    day_line = now.strftime("%A, %b %d")

    font_tiny = load_font(_TINY_SIZE, variant=font_variant)
    day_bbox = draw.textbbox((0, 0), day_line, font=font_tiny)

    # Footer: pin ink bottom at _CONTENT_PAD above canvas bottom so it clears
    # the corner decorations (which extend _CONTENT_PAD - 2 px from each edge).
    day_draw_y = height - _CONTENT_PAD - day_bbox[3]
    footer_ink_top = day_draw_y + day_bbox[1]

    # Auto-size the body font: keep all text within _CONTENT_PAD on every side
    # so neither the phrase nor hour line overlaps the corner decorations.
    body_font = _fit_body_font(
        draw,
        phrase,
        hour_str,
        font_variant,
        available_w=width - 2 * _CONTENT_PAD,
        available_h=footer_ink_top - _CONTENT_PAD,
    )

    phrase_bbox = draw.textbbox((0, 0), phrase, font=body_font)
    hour_bbox = draw.textbbox((0, 0), hour_str, font=body_font)

    # Visual ink heights (excludes internal font leading stored in bbox[1]).
    phrase_ink_h = phrase_bbox[3] - phrase_bbox[1]
    hour_ink_h = hour_bbox[3] - hour_bbox[1]

    # Phrase + hour block: center their ink in the space between the top
    # _CONTENT_PAD strip and the footer ink top. Centering in [_CONTENT_PAD,
    # footer_ink_top] (not [0, footer_ink_top]) keeps the top edge inside
    # _CONTENT_PAD even when the body fills the entire available height —
    # matches _fit_body_font's exclusion zone on both the top and bottom.
    # Working in ink coordinates avoids bbox[1] artefacts shifting the visual
    # centre — fonts like Pacifico or Charis SIL carry large top offsets that
    # would otherwise push the block up or compress the inter-line gap.
    LINE_GAP = _LINE_GAP
    block_ink_h = phrase_ink_h + LINE_GAP + hour_ink_h
    phrase_ink_y = _CONTENT_PAD + (footer_ink_top - _CONTENT_PAD - block_ink_h) // 2

    # Back-calculate draw positions from desired ink positions.
    phrase_draw_y = phrase_ink_y - phrase_bbox[1]
    hour_draw_y = phrase_ink_y + phrase_ink_h + LINE_GAP - hour_bbox[1]

    effective_frame = frame_for_font(font_variant) if frame == AUTO_FRAME else frame
    draw_border(draw, width, height, invert=invert, frame=effective_frame)
    draw.text(
        ((width - (phrase_bbox[2] - phrase_bbox[0])) // 2, phrase_draw_y),
        phrase,
        font=body_font,
        fill=ink,
    )
    draw.text(
        ((width - (hour_bbox[2] - hour_bbox[0])) // 2, hour_draw_y),
        hour_str,
        font=body_font,
        fill=ink,
    )
    draw.text(
        ((width - (day_bbox[2] - day_bbox[0])) // 2, day_draw_y),
        day_line,
        font=font_tiny,
        fill=ink,
    )
