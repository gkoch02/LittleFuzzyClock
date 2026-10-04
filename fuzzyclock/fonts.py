"""Font registry, font loading, and the random-font shuffle bag.

Self-contained: no dependency on any other fuzzyclock module.
"""

import os
import random as _random
import threading as _threading

from PIL import ImageFont

# Repo-vendored fonts live under <repo>/fonts/ and are tried before any system path.
# ``__file__`` is <repo>/fuzzyclock/fonts.py, so walk up twice to reach <repo>/fonts.
_VENDORED_FONT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "fonts"
)


def _v(*filenames):
    return [os.path.join(_VENDORED_FONT_DIR, f) for f in filenames]


# macOS stock fonts: approximate fallbacks so dev renders work off-Pi.
_SUPP = "/System/Library/Fonts/Supplemental/"
_HELVETICA = "/System/Library/Fonts/Helvetica.ttc"
_MENLO = "/System/Library/Fonts/Menlo.ttc"
_IMPACT = _SUPP + "Impact.ttf"
_MARKER_FELT = _SUPP + "Marker Felt.ttc"
_BRADLEY = _SUPP + "Bradley Hand.ttc"
_SNELL = _SUPP + "Snell Roundhand.ttc"
_CHALKDUSTER = _SUPP + "Chalkduster.ttf"
_FUTURA = _SUPP + "Futura.ttc"
_GEORGIA = _SUPP + "Georgia Bold.ttf"
_TIMES = _SUPP + "Times New Roman Bold.ttf"
_ARIAL_ROUNDED = _SUPP + "Arial Rounded Bold.ttf"
_COURIER = _SUPP + "Courier New Bold.ttf"

_MAC_SERIF = [_TIMES, "/Library/Fonts/Times New Roman Bold.ttf"]
_MAC_GEORGIA = [_GEORGIA, "/Library/Fonts/Georgia Bold.ttf"]
_MAC_DISPLAY = [_IMPACT, _HELVETICA]
_MAC_GEOMETRIC = [_FUTURA, _HELVETICA]
_MAC_MONO = [_MENLO, "/System/Library/Fonts/Monaco.ttf"]
_MAC_SCRIPT = [_SNELL, _BRADLEY]
_MAC_ROUNDED = [_ARIAL_ROUNDED, _HELVETICA]
_MAC_MARKER = [_MARKER_FELT, _HELVETICA]
_MAC_CHALK = [_CHALKDUSTER, _IMPACT]

FONT_CANDIDATES = [
    *_v("DejaVuSans-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    _SUPP + "Arial Bold.ttf",
    _HELVETICA,
]

# Variant name -> ordered candidate paths; load_font() uses the first that opens.
# Several variable fonts (sixtyfour, nabla, workbench, kablammo, jaro) have no
# "Bold" named instance and render at their default axis values.
FONT_VARIANTS = {
    "dejavu": FONT_CANDIDATES,
    "dejavu-serif": [
        *_v("DejaVuSerif-Bold.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        *_MAC_SERIF,
    ],
    "liberation-serif": [
        *_v("LiberationSerif-Bold.ttf"),
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        _TIMES,
    ],
    "roboto-slab": [
        *_v("RobotoSlab-Bold.otf"),
        "/usr/share/fonts/opentype/roboto/slab/RobotoSlab-Bold.otf",
        "/usr/share/fonts/truetype/roboto/slab/RobotoSlab-Bold.ttf",
        "/usr/share/fonts/truetype/roboto-slab/RobotoSlab-Bold.ttf",
        _COURIER,
    ],
    "cantarell": [
        *_v("Cantarell-Bold.otf"),
        "/usr/share/fonts/opentype/cantarell/Cantarell-Bold.otf",
        "/usr/share/fonts/cantarell/Cantarell-Bold.otf",
        "/System/Library/Fonts/Supplemental/Verdana Bold.ttf",
        _HELVETICA,
    ],
    "ubuntu": [
        *_v("Ubuntu-Bold.ttf"),
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/System/Library/Fonts/Supplemental/Trebuchet MS Bold.ttf",
    ],
    "jetbrains-mono": [
        *_v("JetBrainsMono-Bold.ttf"),
        "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",
        *_MAC_MONO,
    ],
    "fredoka": [
        *_v("Fredoka.ttf"),
        "/usr/share/fonts/truetype/fredoka/Fredoka-VariableFont_wdth,wght.ttf",
        "/usr/share/fonts/truetype/fredoka-one/FredokaOne-Regular.ttf",
        _ARIAL_ROUNDED,
    ],
    # Proprietary (no apt package): drop the file into fonts/ to enable.
    "bookerly": [*_v("Bookerly-Bold.ttf", "Bookerly.ttf"), *_MAC_GEORGIA],
    "minion": [*_v("MinionPro-Bold.otf", "MinionPro-Regular.otf"), *_MAC_SERIF],
    "livory": [*_v("Livory-Bold.otf", "Livory-Bold.ttf"), *_MAC_GEORGIA],
    "libertinus": [
        *_v("LibertinusSerif-Bold.otf"),
        "/usr/share/fonts/opentype/libertinus/LibertinusSerif-Bold.otf",
        "/usr/share/fonts/opentype/libertinus-font/LibertinusSerif-Bold.otf",
        *_MAC_SERIF,
    ],
    "chaparral": [*_v("ChaparralPro-Bold.otf", "ChaparralPro-Regular.otf"), *_MAC_GEORGIA],
    "charis-sil": [
        *_v("CharisSIL-Bold.ttf"),
        "/usr/share/fonts/truetype/charis/CharisSIL-Bold.ttf",
        *_MAC_GEORGIA,
    ],
    "bitter": [*_v("Bitter-Bold.ttf", "Bitter-Bold.otf"), *_MAC_GEORGIA],
    "literata": [*_v("Literata-Bold.ttf", "Literata-Bold.otf"), *_MAC_GEORGIA],
    "arno": [*_v("ArnoPro-Bold.otf", "ArnoPro-Regular.otf"), *_MAC_SERIF],
    "malabar": [*_v("Malabar-Bold.otf", "Malabar-Bold.ttf"), *_MAC_GEORGIA],
    "pigeonette": [
        *_v(
            "Pigeonette-Bold.otf",
            "Pigeonette-Bold.ttf",
            "Pigeonette-Regular.otf",
            "Pigeonette-Regular.ttf",
            "Pigeonette.otf",
            "Pigeonette.ttf",
        ),
        *_MAC_GEORGIA,
    ],
    "playfair": [*_v("PlayfairDisplay-Bold.ttf"), *_MAC_SERIF],
    "pacifico": [*_v("Pacifico-Regular.ttf"), *_MAC_ROUNDED],
    "lilita-one": [*_v("LilitaOne-Regular.ttf"), _ARIAL_ROUNDED],
    "modak": [*_v("Modak-Regular.ttf"), *_MAC_ROUNDED],
    "righteous": [*_v("Righteous-Regular.ttf"), *_MAC_GEOMETRIC],
    "comfortaa": [
        *_v("Comfortaa-Bold.ttf"),
        "/usr/share/fonts/truetype/comfortaa/Comfortaa-Bold.ttf",
        *_MAC_ROUNDED,
    ],
    "nunito": [*_v("Nunito-Bold.ttf"), *_MAC_ROUNDED],
    "jost": [*_v("Jost-Bold.ttf"), *_MAC_GEOMETRIC],
    "bangers": [*_v("Bangers-Regular.ttf"), _IMPACT],
    "vt323": [*_v("VT323-Regular.ttf"), *_MAC_MONO],
    "press-start-2p": [*_v("PressStart2P-Regular.ttf"), *_MAC_MONO],
    "silkscreen": [*_v("Silkscreen-Bold.ttf"), _MENLO],
    "monoton": [*_v("Monoton-Regular.ttf"), _IMPACT],
    "limelight": [*_v("Limelight-Regular.ttf"), _IMPACT],
    "abril-fatface": [*_v("AbrilFatface-Regular.ttf"), *_MAC_GEORGIA],
    "unifraktur-maguntia": [
        *_v("UnifrakturMaguntia-Book.ttf"),
        "/usr/share/fonts/truetype/unifrakturmaguntia/UnifrakturMaguntia-Book.ttf",
        _TIMES,
    ],
    "medieval-sharp": [*_v("MedievalSharp-Regular.ttf"), _GEORGIA],
    "pirata-one": [*_v("PirataOne-Regular.ttf"), _GEORGIA],
    "almendra-display": [*_v("AlmendraDisplay-Regular.ttf"), *_MAC_SERIF],
    "bungee": [*_v("Bungee-Regular.ttf"), _IMPACT],
    "alfa-slab-one": [*_v("AlfaSlabOne-Regular.ttf"), _GEORGIA],
    "anton": [
        *_v("Anton-Regular.ttf"),
        "/usr/share/fonts/truetype/anton/Anton-Regular.ttf",
        _IMPACT,
    ],
    "staatliches": [*_v("Staatliches-Regular.ttf"), _IMPACT],
    "special-elite": [*_v("SpecialElite-Regular.ttf"), _COURIER],
    "permanent-marker": [*_v("PermanentMarker-Regular.ttf"), _MARKER_FELT],
    "creepster": [*_v("Creepster-Regular.ttf"), _CHALKDUSTER],
    "audiowide": [*_v("Audiowide-Regular.ttf"), _FUTURA],
    "orbitron": [*_v("Orbitron-VF.ttf"), *_MAC_GEOMETRIC],
    "lobster": [*_v("Lobster-Regular.ttf"), _SNELL, _HELVETICA],
    "caveat": [*_v("Caveat-Bold.ttf"), _BRADLEY, _SNELL],
    "kalam": [*_v("Kalam-Bold.ttf"), _BRADLEY],
    "architects-daughter": [*_v("ArchitectsDaughter-Regular.ttf"), _MARKER_FELT],
    "indie-flower": [*_v("IndieFlower-Regular.ttf"), _MARKER_FELT],
    "patrick-hand": [*_v("PatrickHand-Regular.ttf"), _MARKER_FELT],
    "shadows-into-light": [*_v("ShadowsIntoLight-Regular.ttf"), _BRADLEY],
    "gloria-hallelujah": [*_v("GloriaHallelujah-Regular.ttf"), _MARKER_FELT],
    "amatic-sc": [*_v("AmaticSC-Bold.ttf"), _BRADLEY],
    "reenie-beanie": [*_v("ReenieBeanie-Regular.ttf"), _BRADLEY],
    "homemade-apple": [*_v("HomemadeApple-Regular.ttf"), *_MAC_SCRIPT],
    "dancing-script": [*_v("DancingScript-Bold.ttf"), *_MAC_SCRIPT],
    "tangerine": [*_v("Tangerine-Bold.ttf"), _SNELL],
    "parisienne": [*_v("Parisienne-Regular.ttf"), *_MAC_SCRIPT],
    "clicker-script": [*_v("ClickerScript-Regular.ttf"), *_MAC_SCRIPT],
    "yellowtail": [*_v("Yellowtail-Regular.ttf"), *_MAC_SCRIPT],
    "poppins": [*_v("Poppins-Bold.ttf"), *_MAC_GEOMETRIC],
    "raleway": [*_v("Raleway-VF.ttf"), *_MAC_GEOMETRIC],
    "oswald": [*_v("Oswald-VF.ttf"), *_MAC_DISPLAY],
    "work-sans": [*_v("WorkSans-VF.ttf"), *_MAC_GEOMETRIC],
    "cabin": [*_v("Cabin-VF.ttf"), *_MAC_GEOMETRIC],
    "space-grotesk": [*_v("SpaceGrotesk-Bold.ttf"), *_MAC_GEOMETRIC],
    "arvo": [*_v("Arvo-Bold.ttf"), *_MAC_GEORGIA],
    "zilla-slab": [*_v("ZillaSlab-Bold.ttf"), *_MAC_GEORGIA],
    "rokkitt": [*_v("Rokkitt-VF.ttf"), *_MAC_GEORGIA],
    "crete-round": [*_v("CreteRound-Regular.ttf"), *_MAC_GEORGIA],
    "josefin-slab": [*_v("JosefinSlab-VF.ttf"), *_MAC_GEORGIA],
    "fira-mono": [*_v("FiraMono-Bold.ttf"), *_MAC_MONO],
    "courier-prime": [*_v("CourierPrime-Bold.ttf"), _COURIER, _MENLO],
    "share-tech-mono": [*_v("ShareTechMono-Regular.ttf"), *_MAC_MONO],
    "poiret-one": [*_v("PoiretOne-Regular.ttf"), *_MAC_GEOMETRIC],
    "syncopate": [*_v("Syncopate-Bold.ttf"), _FUTURA, _IMPACT],
    "exo-2": [*_v("Exo2-VF.ttf"), *_MAC_GEOMETRIC],
    "luckiest-guy": [*_v("LuckiestGuy-Regular.ttf"), *_MAC_DISPLAY],
    "titan-one": [*_v("TitanOne-Regular.ttf"), *_MAC_DISPLAY],
    "boogaloo": [*_v("Boogaloo-Regular.ttf"), *_MAC_DISPLAY],
    "bungee-shade": [*_v("BungeeShade-Regular.ttf"), *_MAC_DISPLAY],
    "faster-one": [*_v("FasterOne-Regular.ttf"), *_MAC_DISPLAY],
    "shrikhand": [*_v("Shrikhand-Regular.ttf"), *_MAC_DISPLAY],
    "henny-penny": [*_v("HennyPenny-Regular.ttf"), *_MAC_GEORGIA],
    "freckle-face": [*_v("FrekleFace-Regular.ttf"), *_MAC_DISPLAY],
    "rye": [*_v("Rye-Regular.ttf"), *_MAC_SERIF],
    "rubik-dirt": [*_v("RubikDirt-Regular.ttf"), *_MAC_DISPLAY],
    "rubik-maze": [*_v("RubikMaze-Regular.ttf"), *_MAC_DISPLAY],
    "rubik-glitch": [*_v("RubikGlitch-Regular.ttf"), *_MAC_DISPLAY],
    "rubik-wet-paint": [*_v("RubikWetPaint-Regular.ttf"), *_MAC_DISPLAY],
    "rubik-puddles": [*_v("RubikPuddles-Regular.ttf"), *_MAC_DISPLAY],
    "rubik-beastly": [*_v("RubikBeastly-Regular.ttf"), *_MAC_DISPLAY],
    "rubik-microbe": [*_v("RubikMicrobe-Regular.ttf"), *_MAC_DISPLAY],
    "rubik-spray-paint": [*_v("RubikSprayPaint-Regular.ttf"), *_MAC_DISPLAY],
    "rubik-distressed": [*_v("RubikDistressed-Regular.ttf"), *_MAC_DISPLAY],
    "rubik-iso": [*_v("RubikIso-Regular.ttf"), *_MAC_DISPLAY],
    "splash": [*_v("Splash-Regular.ttf"), _BRADLEY, _MARKER_FELT],
    "sixtyfour": [*_v("Sixtyfour-VF.ttf"), *_MAC_MONO],
    "rampart-one": [*_v("RampartOne-Regular.ttf"), *_MAC_DISPLAY],
    "codystar": [*_v("Codystar-Regular.ttf"), *_MAC_DISPLAY],
    "plaster": [*_v("Plaster-Regular.ttf"), *_MAC_DISPLAY],
    "nosifer": [*_v("Nosifer-Regular.ttf"), *_MAC_CHALK],
    "butcherman": [*_v("Butcherman-Regular.ttf"), *_MAC_CHALK],
    "eater": [*_v("Eater-Regular.ttf"), *_MAC_CHALK],
    "lacquer": [*_v("Lacquer-Regular.ttf"), _CHALKDUSTER, _MARKER_FELT],
    "atomic-age": [*_v("AtomicAge-Regular.ttf"), *_MAC_GEOMETRIC],
    "diplomata": [*_v("Diplomata-Regular.ttf"), *_MAC_SERIF],
    "iceland": [*_v("Iceland-Regular.ttf"), *_MAC_GEOMETRIC],
    # Designer ships it as Megrim.ttf, with no -Regular suffix.
    "megrim": [*_v("Megrim.ttf"), *_MAC_GEOMETRIC],
    "cinzel-decorative": [*_v("CinzelDecorative-Regular.ttf"), *_MAC_SERIF],
    "fascinate": [*_v("Fascinate-Regular.ttf"), *_MAC_DISPLAY],
    "forum": [*_v("Forum-Regular.ttf"), *_MAC_SERIF],
    "nabla": [*_v("Nabla-VF.ttf"), *_MAC_DISPLAY],
    "foldit": [*_v("Foldit-VF.ttf"), *_MAC_DISPLAY],
    "workbench": [*_v("Workbench-VF.ttf"), *_MAC_MONO],
    "sancreek": [*_v("Sancreek-Regular.ttf"), *_MAC_SERIF],
    "smokum": [*_v("Smokum-Regular.ttf"), *_MAC_DISPLAY],
    "jolly-lodger": [*_v("JollyLodger-Regular.ttf"), *_MAC_CHALK],
    "akronim": [*_v("Akronim-Regular.ttf"), _MARKER_FELT, _IMPACT],
    "ribeye-marrow": [*_v("RibeyeMarrow-Regular.ttf"), *_MAC_SERIF],
    "astloch": [*_v("Astloch-Bold.ttf"), *_MAC_SERIF],
    "wallpoet": [*_v("Wallpoet-Regular.ttf"), *_MAC_DISPLAY],
    "chango": [*_v("Chango-Regular.ttf"), *_MAC_DISPLAY],
    "gravitas-one": [*_v("GravitasOne-Regular.ttf"), *_MAC_DISPLAY],
    "oi": [*_v("Oi-Regular.ttf"), *_MAC_SERIF],
    "flamenco": [*_v("Flamenco-Regular.ttf"), *_MAC_SERIF],
    "emblema-one": [*_v("EmblemaOne-Regular.ttf"), *_MAC_SERIF],
    "mystery-quest": [*_v("MysteryQuest-Regular.ttf"), *_MAC_GEOMETRIC],
    "baumans": [*_v("Baumans-Regular.ttf"), *_MAC_GEOMETRIC],
    "tourney": [*_v("Tourney-VF.ttf"), *_MAC_DISPLAY],
    "kablammo": [*_v("Kablammo-VF.ttf"), *_MAC_MARKER],
    "unkempt": [*_v("Unkempt-Bold.ttf"), *_MAC_MARKER],
    "jaro": [*_v("Jaro-VF.ttf"), *_MAC_DISPLAY],
    "shojumaru": [*_v("Shojumaru-Regular.ttf"), _MARKER_FELT, _CHALKDUSTER],
    "manufacturing-consent": [*_v("ManufacturingConsent-Regular.ttf"), *_MAC_SERIF],
    "balthazar": [*_v("Balthazar-Regular.ttf"), *_MAC_SERIF],
    "patrick-hand-sc": [*_v("PatrickHandSC-Regular.ttf"), *_MAC_MARKER],
}

DEFAULT_FONT = "dejavu"

# Sentinel font value for "pick a vendored variant per phrase change". Not a
# key in FONT_VARIANTS — callers resolve it to a concrete variant via
# pick_random_font() before passing it to load_font() / render_clock().
RANDOM_FONT = "random"


def _vendored_font_paths(variant):
    """Return every path in `variant`'s candidate list that lies under fonts/."""
    return [p for p in FONT_VARIANTS[variant] if p.startswith(_VENDORED_FONT_DIR)]


def vendored_font_variants():
    """Variants with at least one vendored file present in fonts/.

    Any vendored candidate counts, not just the first. Used by the random-font
    mode so a roll never lands on a variant that load_font() can't open.
    """
    available = []
    for variant in FONT_VARIANTS:
        if any(os.path.exists(p) for p in _vendored_font_paths(variant)):
            available.append(variant)
    return available


# Shuffle-bag state for pick_random_font(). Calls with rng=None deal one
# variant at a time from _random_font_bag; when it empties we reshuffle the
# eligible set, so the user sees every vendored font before any repeats
# (music-shuffle semantics rather than uniform i.i.d.). _last_random_font_pick
# is kept so we can avoid back-to-back duplicates across bag boundaries.
# _random_font_bag_source is the frozenset the current bag was built from —
# if the eligible set changes (font dropped in or removed) we discard the bag
# so the new variant gets a fair turn instead of waiting until the next cycle.
_random_font_bag = []
_random_font_bag_source = None
_last_random_font_pick = None
_random_font_bag_lock = _threading.Lock()


def _reset_random_font_bag():
    """Clear shuffle-bag state. Tests call this so bag carryover between
    cases doesn't leak; production never needs it — refill is automatic
    when the bag empties or the eligible set changes."""
    global _random_font_bag_source, _last_random_font_pick
    with _random_font_bag_lock:
        _random_font_bag.clear()
        _random_font_bag_source = None
        _last_random_font_pick = None


def pick_random_font(rng=None):
    """Pick a vendored font variant.

    With `rng=None` (the production path) uses a shuffle bag: deals each
    vendored variant once before reshuffling, so the user sees every font
    before any repeats. Across bag boundaries the next pick is swapped
    deeper if it matches the previous return, avoiding visible back-to-back
    duplicates whenever the eligible set has at least two entries.

    With `rng` supplied (deterministic test path) bypasses the bag and does
    an isolated `rng.choice` — same seed yields the same pick and leaves
    module bag state undisturbed.

    Falls back to DEFAULT_FONT if no vendored variant is present on disk
    (degraded environment) so callers always get a usable variant key.
    """
    available = vendored_font_variants()
    if not available:
        return DEFAULT_FONT
    if rng is not None:
        return rng.choice(available)
    global _random_font_bag_source, _last_random_font_pick
    available_set = frozenset(available)
    with _random_font_bag_lock:
        if not _random_font_bag or _random_font_bag_source != available_set:
            _random_font_bag[:] = list(available)
            _random.shuffle(_random_font_bag)
            _random_font_bag_source = available_set
            if (
                len(_random_font_bag) > 1
                and _last_random_font_pick is not None
                and _random_font_bag[-1] == _last_random_font_pick
            ):
                swap_idx = _random.randrange(len(_random_font_bag) - 1)
                _random_font_bag[-1], _random_font_bag[swap_idx] = (
                    _random_font_bag[swap_idx],
                    _random_font_bag[-1],
                )
        pick = _random_font_bag.pop()
        _last_random_font_pick = pick
        return pick


def load_font(size, variant=None):
    """Load a TrueType/OpenType font at `size` from a registered variant.

    `variant=None` walks FONT_CANDIDATES (DejaVu Sans Bold + macOS fallbacks).
    A named variant must exist in FONT_VARIANTS; unknown keys raise KeyError
    (user input is validated in fuzzyclock_daemon._load_config).

    For variable fonts (e.g. Fredoka.ttf, which carries a wght axis), we
    activate the "Bold" named instance so weight matches the static-Bold
    static fonts the other variants ship as — otherwise PIL renders at the
    default axis values (Light/Regular), which looks wispy on e-ink and
    hides the variant's character. Static fonts raise OSError on the call
    and we silently skip it; variable fonts without a "Bold" named instance
    (e.g. Sixtyfour, whose axes are BLED/SCAN) raise ValueError, also
    silently skipped — they render at their default axis values.

    Raises SystemExit listing the variant's tried paths when none load. We
    fail loud rather than letting PIL silently fall back to its default
    bitmap font, which would render a subtly-wrong clock face.
    """
    if variant is None:
        candidates = FONT_CANDIDATES
        label = "default"
    else:
        candidates = FONT_VARIANTS[variant]
        label = variant
    for path in candidates:
        try:
            font = ImageFont.truetype(path, size)
        except OSError:
            continue
        try:
            font.set_variation_by_name("Bold")
        except (OSError, AttributeError, ValueError):
            # ValueError: variable font without a "Bold" named instance
            # (e.g. Sixtyfour ships BLED/SCAN axes only). Static fonts raise
            # OSError; non-FreeType backends raise AttributeError.
            pass
        return font
    raise SystemExit(
        f"No usable font found for variant {label!r}. Tried:\n"
        + "\n".join(f"  {p}" for p in candidates)
    )
