"""Border frame styles and the font-to-frame mapping.

Self-contained: no dependency on any other fuzzyclock module. FONT_FRAME_CATEGORY
is keyed by font-variant name but holds only plain strings, so it lives here with
the frames it selects rather than with the font registry.
"""

import zlib

DEFAULT_FRAME = "bauhaus"

# Sentinel frame value for "match the active font's category". Not a key in
# FRAME_VARIANTS — callers resolve it to a concrete frame via frame_for_font()
# before passing it to draw_border().
AUTO_FRAME = "auto"

# Maps every registered font variant to a frame name from FRAME_VARIANTS.
# Unlisted variants (and the RANDOM_FONT sentinel) fall back to DEFAULT_FRAME
# via frame_for_font(). Buckets follow font character: clean sans/serif/mono
# get bauhaus, blackletter/horror get rustic, hand-drawn/script get sketchy,
# pixel/arcade/techno/deco get retro.
FONT_FRAME_CATEGORY = {
    # Clean sans/serif/geometric/mono → bauhaus
    "dejavu": "bauhaus",
    "dejavu-serif": "bauhaus",
    "liberation-serif": "bauhaus",
    "roboto-slab": "bauhaus",
    "cantarell": "bauhaus",
    "ubuntu": "bauhaus",
    "jetbrains-mono": "bauhaus",
    "bitter": "bauhaus",
    "literata": "bauhaus",
    "libertinus": "bauhaus",
    "charis-sil": "bauhaus",
    "playfair": "bauhaus",
    "comfortaa": "bauhaus",
    "nunito": "bauhaus",
    "jost": "bauhaus",
    "poppins": "bauhaus",
    "raleway": "bauhaus",
    "oswald": "bauhaus",
    "work-sans": "bauhaus",
    "cabin": "bauhaus",
    "fira-mono": "bauhaus",
    "courier-prime": "bauhaus",
    "bookerly": "bauhaus",
    "minion": "bauhaus",
    "livory": "bauhaus",
    "chaparral": "bauhaus",
    "arno": "bauhaus",
    "malabar": "bauhaus",
    "fredoka": "bauhaus",
    "lilita-one": "bauhaus",
    "righteous": "bauhaus",
    "alfa-slab-one": "bauhaus",
    "anton": "bauhaus",
    "staatliches": "bauhaus",
    "bangers": "bauhaus",
    "arvo": "bauhaus",
    "zilla-slab": "bauhaus",
    "rokkitt": "bauhaus",
    "crete-round": "bauhaus",
    "josefin-slab": "bauhaus",
    "forum": "bauhaus",
    "space-grotesk": "bauhaus",
    "modak": "bauhaus",
    "luckiest-guy": "bauhaus",
    "titan-one": "bauhaus",
    "boogaloo": "bauhaus",
    "shrikhand": "bauhaus",
    # Blackletter / medieval / horror / wild west → rustic
    "unifraktur-maguntia": "rustic",
    "medieval-sharp": "rustic",
    "pirata-one": "rustic",
    "creepster": "rustic",
    "pigeonette": "rustic",
    "astloch": "rustic",
    "nosifer": "rustic",
    "butcherman": "rustic",
    "eater": "rustic",
    "lacquer": "rustic",
    "jolly-lodger": "rustic",
    "sancreek": "rustic",
    "smokum": "rustic",
    "rye": "rustic",
    "cinzel-decorative": "rustic",
    "almendra-display": "rustic",
    # Hand-drawn / notebook / script → sketchy
    "caveat": "sketchy",
    "kalam": "sketchy",
    "architects-daughter": "sketchy",
    "indie-flower": "sketchy",
    "patrick-hand": "sketchy",
    "shadows-into-light": "sketchy",
    "gloria-hallelujah": "sketchy",
    "amatic-sc": "sketchy",
    "reenie-beanie": "sketchy",
    "homemade-apple": "sketchy",
    "dancing-script": "sketchy",
    "tangerine": "sketchy",
    "parisienne": "sketchy",
    "clicker-script": "sketchy",
    "yellowtail": "sketchy",
    "lobster": "sketchy",
    "pacifico": "sketchy",
    "permanent-marker": "sketchy",
    "special-elite": "sketchy",
    "akronim": "sketchy",
    "ribeye-marrow": "sketchy",
    "freckle-face": "sketchy",
    "splash": "sketchy",
    "henny-penny": "sketchy",
    "plaster": "sketchy",
    "rubik-dirt": "sketchy",
    "rubik-maze": "sketchy",
    "rubik-glitch": "sketchy",
    "rubik-wet-paint": "sketchy",
    "rubik-puddles": "sketchy",
    "rubik-beastly": "sketchy",
    "rubik-microbe": "sketchy",
    "rubik-spray-paint": "sketchy",
    "rubik-distressed": "sketchy",
    "rubik-iso": "sketchy",
    "tfoust": "sketchy",
    # Pixel / arcade / techno / deco → retro
    "vt323": "retro",
    "press-start-2p": "retro",
    "silkscreen": "retro",
    "share-tech-mono": "retro",
    "monoton": "retro",
    "audiowide": "retro",
    "orbitron": "retro",
    "bungee": "retro",
    "exo-2": "retro",
    "poiret-one": "retro",
    "syncopate": "retro",
    "limelight": "retro",
    "abril-fatface": "retro",
    "wallpoet": "retro",
    "atomic-age": "retro",
    "diplomata": "retro",
    "iceland": "retro",
    "megrim": "retro",
    "fascinate": "retro",
    "codystar": "retro",
    "rampart-one": "retro",
    "sixtyfour": "retro",
    "workbench": "retro",
    "faster-one": "retro",
    "bungee-shade": "retro",
    "foldit": "retro",
    "nabla": "retro",
    # New additions
    "chango": "bauhaus",
    "gravitas-one": "bauhaus",
    "oi": "rustic",
    "flamenco": "rustic",
    "emblema-one": "rustic",
    "mystery-quest": "retro",
    "baumans": "retro",
    "tourney": "retro",
    "kablammo": "sketchy",
    "unkempt": "sketchy",
    "jaro": "bauhaus",
    "shojumaru": "sketchy",
    "manufacturing-consent": "rustic",
    "balthazar": "bauhaus",
    "patrick-hand-sc": "sketchy",
}


def frame_for_font(variant):
    """Return the frame name that pairs with `variant`, defaulting to bauhaus.

    Used by render_clock() and the daemon's reset_base_image() when frame is
    AUTO_FRAME. Unknown variants (and the RANDOM_FONT sentinel itself, before
    it's resolved to a concrete font) fall back to DEFAULT_FRAME so callers
    never crash on unmapped fonts.
    """
    return FONT_FRAME_CATEGORY.get(variant, DEFAULT_FRAME)


_BORDER_MARGIN = 4  # border rectangle inset from canvas edge
_CORNER_R = 6  # corner decoration radius / side length
# Inner content boundary: one pixel beyond the corner decorations plus 2 px breathing room.
# Text must stay within this padding on all four sides so it never overlaps the decorations.
# Every frame in FRAME_VARIANTS keeps its outermost ink within this strip on all
# four sides, so _fit_body_font() can keep using it as the text exclusion zone.
_CONTENT_PAD = _BORDER_MARGIN + 2 + _CORNER_R + 2  # = 14


def _draw_frame_bauhaus(draw, width, height, margin, ink):
    """Default frame: 1px rectangle with circle/square corner brackets."""
    r = _CORNER_R
    draw.rectangle((margin, margin, width - margin, height - margin), outline=ink, width=1)
    # Corner brackets: top corners are circles, bottom corners are squares.
    tl = (margin + 2, margin + 2)
    tr = (width - margin - r - 2, margin + 2)
    bl = (margin + 2, height - margin - r - 2)
    br = (width - margin - r - 2, height - margin - r - 2)
    draw.ellipse((tl[0], tl[1], tl[0] + r, tl[1] + r), outline=ink)
    draw.ellipse((tr[0], tr[1], tr[0] + r, tr[1] + r), outline=ink)
    draw.rectangle((bl[0], bl[1], bl[0] + r, bl[1] + r), outline=ink)
    draw.rectangle((br[0], br[1], br[0] + r, br[1] + r), outline=ink)


def _draw_frame_rustic(draw, width, height, margin, ink):
    """Double rectangle with filled diamond ornaments. Pairs with blackletter."""
    inner = margin + 3
    draw.rectangle((margin, margin, width - margin, height - margin), outline=ink, width=1)
    draw.rectangle((inner, inner, width - inner, height - inner), outline=ink, width=1)
    # Filled diamond ornaments inset slightly past the inner rectangle so they
    # straddle both lines instead of crowding one. d controls the half-width.
    d = 4
    centers = (
        (margin + 2 + d, margin + 2 + d),
        (width - margin - 2 - d, margin + 2 + d),
        (margin + 2 + d, height - margin - 2 - d),
        (width - margin - 2 - d, height - margin - 2 - d),
    )
    for cx, cy in centers:
        draw.polygon(
            [(cx, cy - d), (cx + d, cy), (cx, cy + d), (cx - d, cy)],
            fill=ink,
        )


def _sketch_jitter(coord):
    """Deterministic ±1 px wobble keyed off pixel position.

    Random per-render jitter would change the border every partial refresh and
    leave visible flicker; keying off the coordinate makes the same canvas
    position always wobble the same way, so successive frames diff cleanly.
    crc32 rather than hash() because the latter is salted per process
    (PYTHONHASHSEED), which would re-roll the wobble on every daemon restart
    and make --dry-run previews non-reproducible across runs.
    """
    return zlib.crc32(str(coord).encode()) % 3 - 1


def _draw_frame_sketchy(draw, width, height, margin, ink):
    """Hand-drawn jittered rectangle with small open-circle corner ornaments."""
    step = 8
    # Top edge.
    x = margin
    while x < width - margin:
        nx = min(x + step, width - margin)
        draw.line(
            (x, margin + _sketch_jitter(x), nx, margin + _sketch_jitter(nx)),
            fill=ink,
            width=1,
        )
        x = nx
    # Bottom edge.
    x = margin
    while x < width - margin:
        nx = min(x + step, width - margin)
        draw.line(
            (
                x,
                height - margin + _sketch_jitter(x + 1000),
                nx,
                height - margin + _sketch_jitter(nx + 1000),
            ),
            fill=ink,
            width=1,
        )
        x = nx
    # Left edge.
    y = margin
    while y < height - margin:
        ny = min(y + step, height - margin)
        draw.line(
            (margin + _sketch_jitter(y + 2000), y, margin + _sketch_jitter(ny + 2000), ny),
            fill=ink,
            width=1,
        )
        y = ny
    # Right edge.
    y = margin
    while y < height - margin:
        ny = min(y + step, height - margin)
        draw.line(
            (
                width - margin + _sketch_jitter(y + 3000),
                y,
                width - margin + _sketch_jitter(ny + 3000),
                ny,
            ),
            fill=ink,
            width=1,
        )
        y = ny
    # Open-circle corner ornaments.
    r = _CORNER_R
    corners = (
        (margin + 2, margin + 2),
        (width - margin - r - 2, margin + 2),
        (margin + 2, height - margin - r - 2),
        (width - margin - r - 2, height - margin - r - 2),
    )
    for ox, oy in corners:
        draw.ellipse((ox, oy, ox + r, oy + r), outline=ink)


def _draw_frame_retro(draw, width, height, margin, ink):
    """Stair-stepped pixel-art border with chunky L-block corners."""
    step_len = 12
    step_h = 2
    inner = margin + step_h
    # Top edge: alternating outer/inner segments forming a stair.
    x = margin
    on_outer = True
    while x < width - margin:
        nx = min(x + step_len, width - margin)
        y = margin if on_outer else inner
        draw.line((x, y, nx, y), fill=ink, width=1)
        if nx < width - margin:
            draw.line((nx, margin, nx, inner), fill=ink, width=1)
        on_outer = not on_outer
        x = nx
    # Bottom edge mirrors the top.
    x = margin
    on_outer = True
    while x < width - margin:
        nx = min(x + step_len, width - margin)
        y = height - margin if on_outer else height - inner
        draw.line((x, y, nx, y), fill=ink, width=1)
        if nx < width - margin:
            draw.line((nx, height - margin, nx, height - inner), fill=ink, width=1)
        on_outer = not on_outer
        x = nx
    # Left and right edges: same logic rotated 90°.
    y = margin
    on_outer = True
    while y < height - margin:
        ny = min(y + step_len, height - margin)
        x = margin if on_outer else inner
        draw.line((x, y, x, ny), fill=ink, width=1)
        if ny < height - margin:
            draw.line((margin, ny, inner, ny), fill=ink, width=1)
        on_outer = not on_outer
        y = ny
    y = margin
    on_outer = True
    while y < height - margin:
        ny = min(y + step_len, height - margin)
        x = width - margin if on_outer else width - inner
        draw.line((x, y, x, ny), fill=ink, width=1)
        if ny < height - margin:
            draw.line((width - margin, ny, width - inner, ny), fill=ink, width=1)
        on_outer = not on_outer
        y = ny
    # Filled L-block corner ornaments.
    b = 3  # block size
    corners = (
        (margin + 3, margin + 3),
        (width - margin - 3 - 2 * b, margin + 3),
        (margin + 3, height - margin - 3 - 2 * b),
        (width - margin - 3 - 2 * b, height - margin - 3 - 2 * b),
    )
    for ox, oy in corners:
        draw.rectangle((ox, oy, ox + 2 * b, oy + b), fill=ink)
        draw.rectangle((ox, oy + b, ox + b, oy + 2 * b), fill=ink)


FRAME_VARIANTS = {
    "bauhaus": _draw_frame_bauhaus,
    "rustic": _draw_frame_rustic,
    "sketchy": _draw_frame_sketchy,
    "retro": _draw_frame_retro,
}


def draw_border(draw, width, height, margin=_BORDER_MARGIN, invert=False, frame=DEFAULT_FRAME):
    ink = 255 if invert else 0
    drawer = FRAME_VARIANTS.get(frame, FRAME_VARIANTS[DEFAULT_FRAME])
    drawer(draw, width, height, margin, ink)
