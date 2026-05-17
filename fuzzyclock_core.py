"""Shared rendering logic for the fuzzy clock."""

import math
import os
import random as _random
from datetime import datetime, timedelta, timezone

from PIL import ImageFont

# Repo-vendored fonts live under <repo>/fonts/. Variants can prefix this onto
# their candidate list to let users drop a custom .ttf in without touching apt.
_VENDORED_FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

FONT_CANDIDATES = [
    os.path.join(_VENDORED_FONT_DIR, "DejaVuSans-Bold.ttf"),  # vendored
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Raspberry Pi / Debian
    "/Library/Fonts/Arial Bold.ttf",  # macOS
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",  # macOS (Ventura+)
    "/System/Library/Fonts/Helvetica.ttc",  # macOS fallback
]

# Selectable display fonts. Each variant maps to an ordered list of candidate
# paths: load_font() walks them and uses the first that PIL can open. Pi-side
# paths come first; macOS fallbacks (the closest stock equivalent) keep dev
# renders working off-Pi for every variant. The `dejavu` variant aliases the
# legacy `FONT_CANDIDATES` list so existing imports stay byte-identical.
FONT_VARIANTS = {
    "dejavu": FONT_CANDIDATES,
    "dejavu-serif": [
        os.path.join(_VENDORED_FONT_DIR, "DejaVuSerif-Bold.ttf"),  # vendored
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    "liberation-serif": [
        os.path.join(_VENDORED_FONT_DIR, "LiberationSerif-Bold.ttf"),  # vendored
        "/usr/share/fonts/truetype/liberation2/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",  # older Debian layout
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    ],
    "roboto-slab": [
        os.path.join(_VENDORED_FONT_DIR, "RobotoSlab-Bold.otf"),  # vendored
        "/usr/share/fonts/opentype/roboto/slab/RobotoSlab-Bold.otf",
        "/usr/share/fonts/truetype/roboto/slab/RobotoSlab-Bold.ttf",
        "/usr/share/fonts/truetype/roboto-slab/RobotoSlab-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
    ],
    "cantarell": [
        os.path.join(_VENDORED_FONT_DIR, "Cantarell-Bold.otf"),  # vendored
        "/usr/share/fonts/opentype/cantarell/Cantarell-Bold.otf",
        "/usr/share/fonts/cantarell/Cantarell-Bold.otf",  # older Debian
        "/System/Library/Fonts/Supplemental/Verdana Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "ubuntu": [
        os.path.join(_VENDORED_FONT_DIR, "Ubuntu-Bold.ttf"),  # vendored
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/System/Library/Fonts/Supplemental/Trebuchet MS Bold.ttf",
    ],
    "jetbrains-mono": [
        os.path.join(_VENDORED_FONT_DIR, "JetBrainsMono-Bold.ttf"),  # vendored
        "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
    ],
    "fredoka": [
        # Vendored first so users can drop a custom Fredoka.ttf under fonts/
        # without waiting on apt or upstream variants.
        os.path.join(_VENDORED_FONT_DIR, "Fredoka.ttf"),
        "/usr/share/fonts/truetype/fredoka/Fredoka-VariableFont_wdth,wght.ttf",  # fonts-fredoka
        "/usr/share/fonts/truetype/fredoka-one/FredokaOne-Regular.ttf",  # fonts-fredoka-one (older)
        "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    ],
    # Proprietary fonts with no apt package: drop the Bold .ttf/.otf into
    # fonts/ and it will be found ahead of the macOS system fallback.
    "bookerly": [
        os.path.join(_VENDORED_FONT_DIR, "Bookerly-Bold.ttf"),
        os.path.join(_VENDORED_FONT_DIR, "Bookerly.ttf"),
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    "minion": [
        os.path.join(_VENDORED_FONT_DIR, "MinionPro-Bold.otf"),
        os.path.join(_VENDORED_FONT_DIR, "MinionPro-Regular.otf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    "livory": [
        os.path.join(_VENDORED_FONT_DIR, "Livory-Bold.otf"),
        os.path.join(_VENDORED_FONT_DIR, "Livory-Bold.ttf"),
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    "libertinus": [
        # Vendored v7.051 OTF ships in fonts/; apt path kept as system fallback.
        os.path.join(_VENDORED_FONT_DIR, "LibertinusSerif-Bold.otf"),
        "/usr/share/fonts/opentype/libertinus/LibertinusSerif-Bold.otf",  # fonts-libertinus
        "/usr/share/fonts/opentype/libertinus-font/LibertinusSerif-Bold.otf",
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    "chaparral": [
        os.path.join(_VENDORED_FONT_DIR, "ChaparralPro-Bold.otf"),
        os.path.join(_VENDORED_FONT_DIR, "ChaparralPro-Regular.otf"),
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    "charis-sil": [
        os.path.join(_VENDORED_FONT_DIR, "CharisSIL-Bold.ttf"),  # vendored
        "/usr/share/fonts/truetype/charis/CharisSIL-Bold.ttf",
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    "bitter": [
        os.path.join(_VENDORED_FONT_DIR, "Bitter-Bold.ttf"),
        os.path.join(_VENDORED_FONT_DIR, "Bitter-Bold.otf"),
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    "literata": [
        os.path.join(_VENDORED_FONT_DIR, "Literata-Bold.ttf"),
        os.path.join(_VENDORED_FONT_DIR, "Literata-Bold.otf"),
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    "arno": [
        os.path.join(_VENDORED_FONT_DIR, "ArnoPro-Bold.otf"),
        os.path.join(_VENDORED_FONT_DIR, "ArnoPro-Regular.otf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    "malabar": [
        os.path.join(_VENDORED_FONT_DIR, "Malabar-Bold.otf"),
        os.path.join(_VENDORED_FONT_DIR, "Malabar-Bold.ttf"),
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    "pigeonette": [
        os.path.join(_VENDORED_FONT_DIR, "Pigeonette-Bold.otf"),
        os.path.join(_VENDORED_FONT_DIR, "Pigeonette-Bold.ttf"),
        os.path.join(_VENDORED_FONT_DIR, "Pigeonette-Regular.otf"),
        os.path.join(_VENDORED_FONT_DIR, "Pigeonette-Regular.ttf"),
        os.path.join(_VENDORED_FONT_DIR, "Pigeonette.otf"),
        os.path.join(_VENDORED_FONT_DIR, "Pigeonette.ttf"),
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    # Playful / display fonts — all OFL, vendored in fonts/
    "playfair": [
        os.path.join(_VENDORED_FONT_DIR, "PlayfairDisplay-Bold.ttf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    "pacifico": [
        os.path.join(_VENDORED_FONT_DIR, "Pacifico-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "lilita-one": [
        os.path.join(_VENDORED_FONT_DIR, "LilitaOne-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
    ],
    "modak": [
        os.path.join(_VENDORED_FONT_DIR, "Modak-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "righteous": [
        os.path.join(_VENDORED_FONT_DIR, "Righteous-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "comfortaa": [
        # Variable font vendored first; apt static Bold used as fallback.
        os.path.join(_VENDORED_FONT_DIR, "Comfortaa-Bold.ttf"),
        "/usr/share/fonts/truetype/comfortaa/Comfortaa-Bold.ttf",  # fonts-comfortaa
        "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "nunito": [
        os.path.join(_VENDORED_FONT_DIR, "Nunito-Bold.ttf"),
        "/System/Library/Fonts/Supplemental/Arial Rounded Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "jost": [
        os.path.join(_VENDORED_FONT_DIR, "Jost-Bold.ttf"),
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "bangers": [
        os.path.join(_VENDORED_FONT_DIR, "Bangers-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
    ],
    # Display / themed — all OFL or Apache 2.0, vendored in fonts/. macOS
    # fallbacks are deliberately approximate; the personality of these faces
    # only really comes through with the vendored file present.
    "vt323": [
        os.path.join(_VENDORED_FONT_DIR, "VT323-Regular.ttf"),
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
    ],
    "press-start-2p": [
        os.path.join(_VENDORED_FONT_DIR, "PressStart2P-Regular.ttf"),
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
    ],
    "silkscreen": [
        os.path.join(_VENDORED_FONT_DIR, "Silkscreen-Bold.ttf"),
        "/System/Library/Fonts/Menlo.ttc",
    ],
    "monoton": [
        os.path.join(_VENDORED_FONT_DIR, "Monoton-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
    ],
    "limelight": [
        os.path.join(_VENDORED_FONT_DIR, "Limelight-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
    ],
    "abril-fatface": [
        os.path.join(_VENDORED_FONT_DIR, "AbrilFatface-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    "unifraktur-maguntia": [
        os.path.join(_VENDORED_FONT_DIR, "UnifrakturMaguntia-Book.ttf"),
        "/usr/share/fonts/truetype/unifrakturmaguntia/UnifrakturMaguntia-Book.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
    ],
    "medieval-sharp": [
        os.path.join(_VENDORED_FONT_DIR, "MedievalSharp-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    ],
    "pirata-one": [
        os.path.join(_VENDORED_FONT_DIR, "PirataOne-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    ],
    "almendra-display": [
        os.path.join(_VENDORED_FONT_DIR, "AlmendraDisplay-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    "bungee": [
        os.path.join(_VENDORED_FONT_DIR, "Bungee-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
    ],
    "alfa-slab-one": [
        os.path.join(_VENDORED_FONT_DIR, "AlfaSlabOne-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
    ],
    "anton": [
        os.path.join(_VENDORED_FONT_DIR, "Anton-Regular.ttf"),
        "/usr/share/fonts/truetype/anton/Anton-Regular.ttf",  # fonts-anton
        "/System/Library/Fonts/Supplemental/Impact.ttf",
    ],
    "staatliches": [
        os.path.join(_VENDORED_FONT_DIR, "Staatliches-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
    ],
    "special-elite": [
        os.path.join(_VENDORED_FONT_DIR, "SpecialElite-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
    ],
    "permanent-marker": [
        os.path.join(_VENDORED_FONT_DIR, "PermanentMarker-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
    ],
    "creepster": [
        os.path.join(_VENDORED_FONT_DIR, "Creepster-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Chalkduster.ttf",
    ],
    "audiowide": [
        os.path.join(_VENDORED_FONT_DIR, "Audiowide-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Futura.ttc",
    ],
    "orbitron": [
        os.path.join(_VENDORED_FONT_DIR, "Orbitron-VF.ttf"),
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "lobster": [
        os.path.join(_VENDORED_FONT_DIR, "Lobster-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Snell Roundhand.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Hand-drawn / notebook handwriting — OFL/Apache, vendored in fonts/.
    # macOS fallbacks are deliberately approximate; the personality only
    # reads with the vendored file present.
    "caveat": [
        os.path.join(_VENDORED_FONT_DIR, "Caveat-Bold.ttf"),
        "/System/Library/Fonts/Supplemental/Bradley Hand.ttc",
        "/System/Library/Fonts/Supplemental/Snell Roundhand.ttc",
    ],
    "kalam": [
        os.path.join(_VENDORED_FONT_DIR, "Kalam-Bold.ttf"),
        "/System/Library/Fonts/Supplemental/Bradley Hand.ttc",
    ],
    "architects-daughter": [
        os.path.join(_VENDORED_FONT_DIR, "ArchitectsDaughter-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
    ],
    "indie-flower": [
        os.path.join(_VENDORED_FONT_DIR, "IndieFlower-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
    ],
    "patrick-hand": [
        os.path.join(_VENDORED_FONT_DIR, "PatrickHand-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
    ],
    "shadows-into-light": [
        os.path.join(_VENDORED_FONT_DIR, "ShadowsIntoLight-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Bradley Hand.ttc",
    ],
    "gloria-hallelujah": [
        os.path.join(_VENDORED_FONT_DIR, "GloriaHallelujah-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
    ],
    "amatic-sc": [
        os.path.join(_VENDORED_FONT_DIR, "AmaticSC-Bold.ttf"),
        "/System/Library/Fonts/Supplemental/Bradley Hand.ttc",
    ],
    "reenie-beanie": [
        os.path.join(_VENDORED_FONT_DIR, "ReenieBeanie-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Bradley Hand.ttc",
    ],
    "homemade-apple": [
        os.path.join(_VENDORED_FONT_DIR, "HomemadeApple-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Snell Roundhand.ttc",
        "/System/Library/Fonts/Supplemental/Bradley Hand.ttc",
    ],
    # Flowing script & calligraphy — OFL/Apache 2.0, vendored in fonts/.
    # Connected cursives and formal calligraphic scripts. macOS fallbacks
    # point to Snell Roundhand (closest stock connected script); the
    # personality only reads with the vendored file present.
    "dancing-script": [
        os.path.join(_VENDORED_FONT_DIR, "DancingScript-Bold.ttf"),  # vendored, variable
        "/System/Library/Fonts/Supplemental/Snell Roundhand.ttc",
        "/System/Library/Fonts/Supplemental/Bradley Hand.ttc",
    ],
    "tangerine": [
        os.path.join(_VENDORED_FONT_DIR, "Tangerine-Bold.ttf"),  # vendored
        "/System/Library/Fonts/Supplemental/Snell Roundhand.ttc",
    ],
    "parisienne": [
        os.path.join(_VENDORED_FONT_DIR, "Parisienne-Regular.ttf"),  # vendored
        "/System/Library/Fonts/Supplemental/Snell Roundhand.ttc",
        "/System/Library/Fonts/Supplemental/Bradley Hand.ttc",
    ],
    "clicker-script": [
        os.path.join(_VENDORED_FONT_DIR, "ClickerScript-Regular.ttf"),  # vendored
        "/System/Library/Fonts/Supplemental/Snell Roundhand.ttc",
        "/System/Library/Fonts/Supplemental/Bradley Hand.ttc",
    ],
    "yellowtail": [
        os.path.join(_VENDORED_FONT_DIR, "Yellowtail-Regular.ttf"),  # vendored
        "/System/Library/Fonts/Supplemental/Snell Roundhand.ttc",
        "/System/Library/Fonts/Supplemental/Bradley Hand.ttc",
    ],
    # Geometric & condensed sans — OFL, vendored in fonts/. Clean geometric
    # proportions; Oswald is condensed for fitting long e-ink phrases.
    "poppins": [
        os.path.join(_VENDORED_FONT_DIR, "Poppins-Bold.ttf"),  # vendored
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "raleway": [
        os.path.join(_VENDORED_FONT_DIR, "Raleway-VF.ttf"),  # vendored, variable
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "oswald": [
        os.path.join(_VENDORED_FONT_DIR, "Oswald-VF.ttf"),  # vendored, variable
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "work-sans": [
        os.path.join(_VENDORED_FONT_DIR, "WorkSans-VF.ttf"),  # vendored, variable
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "cabin": [
        os.path.join(_VENDORED_FONT_DIR, "Cabin-VF.ttf"),  # vendored, variable
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "space-grotesk": [
        os.path.join(_VENDORED_FONT_DIR, "SpaceGrotesk-Bold.ttf"),  # vendored
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Slab serif — OFL, vendored in fonts/. Sturdy bracketed serifs across the
    # full personality range: geometric precision to humanist warmth. macOS
    # fallback uses Georgia Bold (the closest stock slab-adjacent serif); the
    # character of each face only reads with the vendored file present.
    "arvo": [
        os.path.join(_VENDORED_FONT_DIR, "Arvo-Bold.ttf"),  # vendored
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    "zilla-slab": [
        os.path.join(_VENDORED_FONT_DIR, "ZillaSlab-Bold.ttf"),  # vendored
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    "rokkitt": [
        os.path.join(_VENDORED_FONT_DIR, "Rokkitt-VF.ttf"),  # vendored, variable
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    "crete-round": [
        os.path.join(_VENDORED_FONT_DIR, "CreteRound-Regular.ttf"),  # vendored
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    "josefin-slab": [
        os.path.join(_VENDORED_FONT_DIR, "JosefinSlab-VF.ttf"),  # vendored, variable
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    # Monospace additions — OFL, vendored in fonts/. Refined coding/terminal
    # mono faces to complement the pixel/bitmap retro set. macOS fallbacks
    # are Menlo/Courier; personality only reads with the vendored file.
    "fira-mono": [
        os.path.join(_VENDORED_FONT_DIR, "FiraMono-Bold.ttf"),  # vendored
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
    ],
    "courier-prime": [
        os.path.join(_VENDORED_FONT_DIR, "CourierPrime-Bold.ttf"),  # vendored
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
        "/System/Library/Fonts/Menlo.ttc",
    ],
    "share-tech-mono": [
        os.path.join(_VENDORED_FONT_DIR, "ShareTechMono-Regular.ttf"),  # vendored
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
    ],
    # Art deco & techno additions — OFL/Apache 2.0, vendored in fonts/.
    # Extends the vintage/futuristic section. macOS fallbacks are Futura
    # (closest geometric sans) then Helvetica; personality only reads with
    # the vendored file present.
    "poiret-one": [
        os.path.join(_VENDORED_FONT_DIR, "PoiretOne-Regular.ttf"),  # vendored
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "syncopate": [
        os.path.join(_VENDORED_FONT_DIR, "Syncopate-Bold.ttf"),  # vendored
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
    ],
    "exo-2": [
        os.path.join(_VENDORED_FONT_DIR, "Exo2-VF.ttf"),  # vendored, variable
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Heavy display / cartoon — OFL, vendored in fonts/. Bold, chunky, or
    # retro-comic personalities. macOS fallbacks are Impact/Helvetica; the
    # full personality only reads with the vendored file present.
    "luckiest-guy": [
        os.path.join(_VENDORED_FONT_DIR, "LuckiestGuy-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "titan-one": [
        os.path.join(_VENDORED_FONT_DIR, "TitanOne-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "boogaloo": [
        os.path.join(_VENDORED_FONT_DIR, "Boogaloo-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Artistic & unique display — OFL, vendored in fonts/. Chosen for visual
    # impact over legibility. macOS fallbacks are approximate; personality only
    # reads with the vendored file present.
    "bungee-shade": [
        os.path.join(_VENDORED_FONT_DIR, "BungeeShade-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "faster-one": [
        os.path.join(_VENDORED_FONT_DIR, "FasterOne-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "shrikhand": [
        os.path.join(_VENDORED_FONT_DIR, "Shrikhand-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "henny-penny": [
        os.path.join(_VENDORED_FONT_DIR, "HennyPenny-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
    ],
    "freckle-face": [
        os.path.join(_VENDORED_FONT_DIR, "FrekleFace-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "rye": [
        os.path.join(_VENDORED_FONT_DIR, "Rye-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    # Textured / experimental — OFL, vendored in fonts/. Letterforms filled
    # with dirt, mazes, drips, microbes, puddles, scanlines, bricks, stars, or
    # sprayed-on paint; renders as textured fills on e-ink. The wider Rubik
    # Filtered family ships separate weirdness modes from the same chassis.
    "rubik-dirt": [
        os.path.join(_VENDORED_FONT_DIR, "RubikDirt-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "rubik-maze": [
        os.path.join(_VENDORED_FONT_DIR, "RubikMaze-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "rubik-glitch": [
        os.path.join(_VENDORED_FONT_DIR, "RubikGlitch-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "rubik-wet-paint": [
        os.path.join(_VENDORED_FONT_DIR, "RubikWetPaint-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "rubik-puddles": [
        os.path.join(_VENDORED_FONT_DIR, "RubikPuddles-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "rubik-beastly": [
        os.path.join(_VENDORED_FONT_DIR, "RubikBeastly-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "rubik-microbe": [
        os.path.join(_VENDORED_FONT_DIR, "RubikMicrobe-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "rubik-spray-paint": [
        os.path.join(_VENDORED_FONT_DIR, "RubikSprayPaint-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "rubik-distressed": [
        os.path.join(_VENDORED_FONT_DIR, "RubikDistressed-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "rubik-iso": [
        os.path.join(_VENDORED_FONT_DIR, "RubikIso-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Outlined letterforms with knobbly burst-shaped growths riding every
    # stroke — hollow centres, prickly silhouette. Internal name is
    # "TFoustScript" despite not being a connected script.
    "tfoust": [
        os.path.join(_VENDORED_FONT_DIR, "TFoust.ttf"),
        "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
        "/System/Library/Fonts/Supplemental/Chalkduster.ttf",
    ],
    "splash": [
        os.path.join(_VENDORED_FONT_DIR, "Splash-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Bradley Hand.ttc",
        "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
    ],
    "sixtyfour": [
        # Variable axes (BLED, SCAN) — load_font's set_variation_by_name("Bold")
        # call silently no-ops since this face has no Bold instance.
        os.path.join(_VENDORED_FONT_DIR, "Sixtyfour-VF.ttf"),
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
    ],
    "rampart-one": [
        os.path.join(_VENDORED_FONT_DIR, "RampartOne-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "codystar": [
        os.path.join(_VENDORED_FONT_DIR, "Codystar-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "plaster": [
        os.path.join(_VENDORED_FONT_DIR, "Plaster-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Horror & macabre — OFL, vendored in fonts/. Drippy, bitten, blood-spattered
    # letterforms; the goth/halloween/horror corner of the gallery. macOS
    # fallbacks lean on Chalkduster / Marker Felt for similar ragged energy.
    "nosifer": [
        os.path.join(_VENDORED_FONT_DIR, "Nosifer-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Chalkduster.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
    ],
    "butcherman": [
        os.path.join(_VENDORED_FONT_DIR, "Butcherman-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Chalkduster.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
    ],
    "eater": [
        os.path.join(_VENDORED_FONT_DIR, "Eater-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Chalkduster.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
    ],
    "lacquer": [
        os.path.join(_VENDORED_FONT_DIR, "Lacquer-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Chalkduster.ttf",
        "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
    ],
    # Vintage display oddities — OFL, vendored in fonts/. Outlined inline
    # (atomic-age), heavily ornamented Art Deco (diplomata), Nordic geometric
    # rune-like (iceland), and constructed thin-stroke Art Nouveau (megrim).
    # macOS fallbacks are Futura/Impact/Times; personality only reads with the
    # vendored file present.
    "atomic-age": [
        os.path.join(_VENDORED_FONT_DIR, "AtomicAge-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "diplomata": [
        os.path.join(_VENDORED_FONT_DIR, "Diplomata-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    "iceland": [
        os.path.join(_VENDORED_FONT_DIR, "Iceland-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "megrim": [
        # Filename has no -Regular suffix; designer shipped it as Megrim.ttf.
        os.path.join(_VENDORED_FONT_DIR, "Megrim.ttf"),
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Ornate / Art Nouveau — OFL, vendored in fonts/. Decorative Roman caps,
    # Art Deco inline, and calligraphic elegance. macOS fallbacks are Georgia/
    # Times; personality only reads with the vendored file present.
    "cinzel-decorative": [
        os.path.join(_VENDORED_FONT_DIR, "CinzelDecorative-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    "fascinate": [
        os.path.join(_VENDORED_FONT_DIR, "Fascinate-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "forum": [
        os.path.join(_VENDORED_FONT_DIR, "Forum-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    # Weird & unique — OFL/Apache 2.0, vendored in fonts/. The deeper end of the
    # gallery: 3D faceted gradients, origami folds, machined-metal axes, Wild
    # West cracked engravings, smoke-marquee, skeletal carnival, frantic
    # outlines, hollow inline serifs, runic medieval geometry, chiselled stone.
    # macOS fallbacks are deliberately approximate; the personality of these
    # faces only really comes through with the vendored file present.
    "nabla": [
        # Variable axes (EDPT, EHLT) — Bold named instance is a no-op; renders
        # at default axis values: 3D faceted extrusion with internal highlights.
        # COLR/CPAL color-font tables are ignored by PIL and the e-ink panel,
        # so the glyphs come through as nested outlined geometry.
        os.path.join(_VENDORED_FONT_DIR, "Nabla-VF.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "foldit": [
        # Variable wght axis — Bold named instance is honoured: heavier folds.
        # Letters look like creased paper at every weight.
        os.path.join(_VENDORED_FONT_DIR, "Foldit-VF.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "workbench": [
        # Variable axes (BLED, SCAN) — same gotcha as sixtyfour: no Bold named
        # instance, set_variation_by_name silently no-ops, renders at defaults.
        os.path.join(_VENDORED_FONT_DIR, "Workbench-VF.ttf"),
        "/System/Library/Fonts/Menlo.ttc",
        "/System/Library/Fonts/Monaco.ttf",
    ],
    "sancreek": [
        os.path.join(_VENDORED_FONT_DIR, "Sancreek-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    "smokum": [
        os.path.join(_VENDORED_FONT_DIR, "Smokum-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    "jolly-lodger": [
        os.path.join(_VENDORED_FONT_DIR, "JollyLodger-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Chalkduster.ttf",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
    ],
    "akronim": [
        os.path.join(_VENDORED_FONT_DIR, "Akronim-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
        "/System/Library/Fonts/Supplemental/Impact.ttf",
    ],
    "ribeye-marrow": [
        os.path.join(_VENDORED_FONT_DIR, "RibeyeMarrow-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    "astloch": [
        os.path.join(_VENDORED_FONT_DIR, "Astloch-Bold.ttf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    "wallpoet": [
        os.path.join(_VENDORED_FONT_DIR, "Wallpoet-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # --- New artistic / strange additions ---
    # Ultra-heavy condensed Latin display — single weight, fills space with presence.
    "chango": [
        os.path.join(_VENDORED_FONT_DIR, "Chango-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Single-weight ultra-heavy display serif — maximum ink, ink traps, immovable gravity.
    "gravitas-one": [
        os.path.join(_VENDORED_FONT_DIR, "GravitasOne-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Victorian ornamental display — elaborate swash caps with inline decorations.
    "oi": [
        os.path.join(_VENDORED_FONT_DIR, "Oi-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    # Art Nouveau calligraphic display — letterforms with organic curved spurs.
    "flamenco": [
        os.path.join(_VENDORED_FONT_DIR, "Flamenco-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    # Outlined decorative display — inline channels through bold exotic caps.
    "emblema-one": [
        os.path.join(_VENDORED_FONT_DIR, "EmblemaOne-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    # Alien sci-fi display — letterforms with UFO/mystery-zone cut-outs and strange angles.
    "mystery-quest": [
        os.path.join(_VENDORED_FONT_DIR, "MysteryQuest-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Techno-mechanical constructed — built from circles and straight lines; hi-fi gear vibes.
    "baumans": [
        os.path.join(_VENDORED_FONT_DIR, "Baumans-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Futura.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Variable racing/championship — extreme condensed wdth axis; spoiler, chequered flag.
    "tourney": [
        # Variable wdth + wght axes — Bold named instance narrows glyphs further.
        os.path.join(_VENDORED_FONT_DIR, "Tourney-VF.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Inflated balloon variable font — MORF axis bloats letters into pressurised bubbles.
    "kablammo": [
        # Variable MORF axis — no Bold named instance; renders at default inflation.
        os.path.join(_VENDORED_FONT_DIR, "Kablammo-VF.ttf"),
        "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Scrawly asymmetric handwriting — deliberately unkempt, uneven baseline, wild loops.
    "unkempt": [
        os.path.join(_VENDORED_FONT_DIR, "Unkempt-Bold.ttf"),
        "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Global display sans inspired by Jaroslav Benda — heavy geometric caps with
    # quirky terminals. Variable opsz axis only (no Bold instance), so
    # set_variation_by_name("Bold") silently no-ops and the font renders at its
    # default optical size.
    "jaro": [
        os.path.join(_VENDORED_FONT_DIR, "Jaro-VF.ttf"),
        "/System/Library/Fonts/Supplemental/Impact.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ],
    # Brushed sumi-e display — thick rounded strokes with sharp tapered terminals,
    # Japanese brush-calligraphy interpretation of Latin caps.
    "shojumaru": [
        os.path.join(_VENDORED_FONT_DIR, "Shojumaru-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Marker Felt.ttc",
        "/System/Library/Fonts/Supplemental/Chalkduster.ttf",
    ],
    # NYT-masthead-style Fraktur blackletter — forked from Chomsky, named after
    # the Chomsky/Herman book. Authoritative editorial gravitas.
    "manufacturing-consent": [
        os.path.join(_VENDORED_FONT_DIR, "ManufacturingConsent-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
    # Copperplate-Gothic-inspired bistro serif — high x-height, diagonal stress,
    # delicate serifs, NYC/Paris menu vibe.
    "balthazar": [
        os.path.join(_VENDORED_FONT_DIR, "Balthazar-Regular.ttf"),
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/Library/Fonts/Times New Roman Bold.ttf",
    ],
}

DEFAULT_FONT = "dejavu"

# Sentinel font value for "pick a vendored variant per phrase change". Not a
# key in FONT_VARIANTS — callers resolve it to a concrete variant via
# pick_random_font() before passing it to load_font() / render_clock().
RANDOM_FONT = "random"

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
}


def frame_for_font(variant):
    """Return the frame name that pairs with `variant`, defaulting to bauhaus.

    Used by render_clock() and the daemon's reset_base_image() when frame is
    AUTO_FRAME. Unknown variants (and the RANDOM_FONT sentinel itself, before
    it's resolved to a concrete font) fall back to DEFAULT_FRAME so callers
    never crash on unmapped fonts.
    """
    return FONT_FRAME_CATEGORY.get(variant, DEFAULT_FRAME)


def _vendored_font_paths(variant):
    """Yield every vendored-fonts-dir path in `variant`'s candidate list.

    Each FONT_VARIANTS entry is an ordered list of paths; the vendored ones
    live under fonts/ at the repo root and are how we tell "we ship this
    font" from "system fallback only". Some variants list multiple vendored
    fallbacks (e.g. pigeonette accepts Bold/Regular/plain) so callers must
    consider all of them, not just the first — load_font() walks the whole
    list at runtime, and the random-font filter would otherwise exclude
    variants whose first preferred filename happens to be missing.
    """
    return [p for p in FONT_VARIANTS[variant] if p.startswith(_VENDORED_FONT_DIR)]


def vendored_font_variants():
    """Variants with at least one vendored TTF/OTF actually present in fonts/.

    Used by the random-font mode so a roll only lands on a font we ship.
    Mirrors load_font()'s "first-that-opens wins" semantics: a variant is
    eligible if any of its vendored paths exists on disk, not just the first.
    Filtering by file existence keeps a clean Pi (no commercial fonts dropped
    in) from rendering with PIL's default bitmap fallback when the random
    pick happens to be `bookerly` etc. — load_font would SystemExit.
    """
    available = []
    for variant in FONT_VARIANTS:
        if any(os.path.exists(p) for p in _vendored_font_paths(variant)):
            available.append(variant)
    return available


def pick_random_font(rng=None):
    """Pick a vendored font variant at random.

    `rng` defaults to the module's `random` instance; tests pass a seeded
    `random.Random` for determinism. Falls back to DEFAULT_FONT if nothing
    is vendored on disk (degraded environment) so callers always get a
    usable variant key.
    """
    available = vendored_font_variants()
    if not available:
        return DEFAULT_FONT
    rng = rng if rng is not None else _random
    return rng.choice(available)


HOUR_WORDS = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
}

DIALECTS = {
    "classic": {
        "phrases": [
            "just after",
            "a little past",
            "ten past",
            "quarter past",
            "twenty past",
            "twenty-five past",
            "half past",
            "twenty-five to",
            "twenty to",
            "quarter to",
            "ten to",
            "almost",
        ],
        "hours": HOUR_WORDS,
        "format_hour": lambda hour_word, is_pm: f"{hour_word} {'pm' if is_pm else 'am'}",
    },
    "shakespeare": {
        "phrases": [
            "'tis just past",
            "a moment past",
            "ten past",
            "'tis a quarter past",
            "twenty past",
            "twenty-five past",
            "'tis half past",
            "twenty-five 'fore",
            "twenty 'fore",
            "a quarter 'fore",
            "ten 'fore",
            "almost",
        ],
        "hours": HOUR_WORDS,
        # AM/PM is anachronistic; "of the clock" reads right at any hour.
        "format_hour": lambda hour_word, is_pm: f"{hour_word} of the clock",
    },
    "klingon": {
        "phrases": [
            "newly forged",
            "moments past",
            "ten past",
            "quarter past",
            "twenty past",
            "twenty-five past",
            "half past",
            "twenty-five 'til",
            "twenty 'til",
            "quarter 'til",
            "ten 'til",
            "battle nears",
        ],
        # Actual tlhIngan Hol numerals; "rep" is Klingon for "hour".
        "hours": {
            1: "wa'",
            2: "cha'",
            3: "wej",
            4: "loS",
            5: "vagh",
            6: "jav",
            7: "Soch",
            8: "chorgh",
            9: "Hut",
            10: "wa'maH",
            11: "wa'maH wa'",
            12: "wa'maH cha'",
        },
        "format_hour": lambda hour_word, is_pm: f"{hour_word} rep",
    },
    "belter": {
        # Lang Belta creole: "to da" for "to the", "ke" as a sentence tag,
        # "savvy" for "you understand?". Belters keep maritime "bell" for time.
        "phrases": [
            "just past",
            "showxa pasa",
            "ten past",
            "quarter past",
            "twenty past",
            "twenty-five past",
            "half past",
            "twenty-five to da",
            "twenty to da",
            "quarter to da",
            "ten to da",
            "almost, ke",
        ],
        "hours": HOUR_WORDS,
        "format_hour": lambda hour_word, is_pm: f"{hour_word} bell, ya",
    },
    "german": {
        # Standard High German fuzzy time. "halb [hour]" means "half-to
        # [hour]" — 9:30 reads "halb zehn" (half ten), referencing the *next*
        # hour. The 25-past and 35-past slots ("fünf vor halb", "fünf nach
        # halb") share the same anchor, so this dialect bumps
        # `hour_advance_at` down to 5 to advance the displayed hour starting
        # at index 5 instead of 7.
        # Regional variants (Swiss "viertel ab", Austrian etc.) intentionally
        # not applied — keep this entry as the de-DE/standard form.
        "phrases": [
            "kurz nach",
            "fünf nach",
            "zehn nach",
            "viertel nach",
            "zwanzig nach",
            "fünf vor halb",
            "halb",
            "fünf nach halb",
            "zwanzig vor",
            "viertel vor",
            "zehn vor",
            "kurz vor",
        ],
        "hours": {
            1: "eins",
            2: "zwei",
            3: "drei",
            4: "vier",
            5: "fünf",
            6: "sechs",
            7: "sieben",
            8: "acht",
            9: "neun",
            10: "zehn",
            11: "elf",
            12: "zwölf",
        },
        "hour_advance_at": 5,
        "format_hour": lambda hour_word, is_pm: hour_word,
    },
    "hal": {
        # HAL 9000 — terse, all-caps, mission-control T-minus cadence.
        # "MIDPOINT" and "IMMINENT" replace the T±N readout at the half-hour
        # and top-of-hour for the same reason HAL drops into clipped
        # declaratives in 2001: it sounds more inevitable that way.
        # Hours render as 24h numeric ("0900 HOURS" / "2100 HOURS") so the
        # mission-control voice stays consistent and the AM/PM signal isn't
        # silently dropped — important for a dialect that's explicitly
        # military timekeeping.
        "phrases": [
            "ON THE MARK",
            "T+5 MINUTES",
            "T+10 MINUTES",
            "T+15 MINUTES",
            "T+20 MINUTES",
            "T+25 MINUTES",
            "MIDPOINT",
            "T-25 MINUTES",
            "T-20 MINUTES",
            "T-15 MINUTES",
            "T-10 MINUTES",
            "IMMINENT",
        ],
        "hours": {i: str(i) for i in range(1, 13)},
        "format_hour": lambda hour_word, is_pm: (
            f"{((int(hour_word) % 12) + (12 if is_pm else 0)):02d}00 HOURS"
        ),
    },
    "cthulhu": {
        # Lovecraftian dread. The atmosphere lives on the hour line — every
        # reading is "the [ordinal] hour" — and on two flavor phrases:
        # "newly woken" / "moments past" at the start of an hour, and the
        # iconic "the stars are right" at the top of the next one (the
        # Lovecraft phrase precedes Cthulhu's awakening from R'lyeh).
        # The middle indices stay generic so the dread accents land where
        # they matter; "the eleventh hour" doubles as the idiom for "too
        # late" on every 10:30+ reading.
        "phrases": [
            "newly woken",
            "moments past",
            "ten past",
            "quarter past",
            "twenty past",
            "twenty-five past",
            "the half-hour",
            "twenty-five 'fore",
            "twenty 'fore",
            "quarter 'fore",
            "ten 'fore",
            "the stars are right",
        ],
        "hours": {
            1: "first",
            2: "second",
            3: "third",
            4: "fourth",
            5: "fifth",
            6: "sixth",
            7: "seventh",
            8: "eighth",
            9: "ninth",
            10: "tenth",
            11: "eleventh",
            12: "twelfth",
        },
        "format_hour": lambda hour_word, is_pm: f"the {hour_word} hour",
    },
    "latin": {
        # Latin-inspired fuzzy time. Hours render as Roman numerals — the
        # iconic clock-face form — with the literal "a.m."/"p.m." (ante/post
        # meridiem) abbreviations as an etymology Easter egg. Phrases use
        # Latin time prepositions: "post" (after), "ante" (before), "fere"
        # (almost), "modo" (just/recently). Grammar is loose because Latin
        # word order resists the phrase/hour split, but every word is real.
        # (We use IV not IIII; the latter is a clock-face convention, not a
        # general Roman numeral one.)
        "phrases": [
            "modo post",
            "quinque post",
            "decem post",
            "quadrans post",
            "viginti post",
            "viginti quinque post",
            "media post",
            "viginti quinque ante",
            "viginti ante",
            "quadrans ante",
            "decem ante",
            "fere",
        ],
        "hours": {
            1: "I",
            2: "II",
            3: "III",
            4: "IV",
            5: "V",
            6: "VI",
            7: "VII",
            8: "VIII",
            9: "IX",
            10: "X",
            11: "XI",
            12: "XII",
        },
        "format_hour": lambda hw, is_pm: f"hora {hw} {'p.m.' if is_pm else 'a.m.'}",
    },
}

DEFAULT_DIALECT = "classic"


def _validate_dialects(dialects):
    """Reject dialects with an out-of-range `hour_advance_at`.

    `hour_advance_at` controls when the displayed hour flips from current to
    next. It must stay <= 11 so the index-11 ("almost") slot still advances —
    otherwise minutes 57-59 wrap back to "almost [current hour]" via % 12,
    which is the bug the min(..., 11) cap in fuzzy_time exists to prevent.
    """
    for name, spec in dialects.items():
        adv = spec.get("hour_advance_at", 7)
        if not 1 <= adv <= 11:
            raise ValueError(
                f"Dialect {name!r} has invalid hour_advance_at={adv}; "
                "must be in 1..11 to preserve the almost-next-hour invariant."
            )


_validate_dialects(DIALECTS)


def load_font(size, variant=None):
    """Load a TrueType/OpenType font at `size` from a registered variant.

    `variant=None` walks the legacy FONT_CANDIDATES list (DejaVu Sans Bold +
    macOS fallbacks) — preserved for backward compat with code that doesn't
    care which variant. A named variant must exist in FONT_VARIANTS; unknown
    keys raise KeyError (programming-bug guard — the daemon validates upstream
    via _resolve_font and falls back gracefully on user input).

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


def fuzzy_time(hour, minute, dialect=DEFAULT_DIALECT):
    spec = DIALECTS[dialect]
    # Cap at 11 so minutes 57-59 stay as "almost [next hour]" rather than
    # wrapping back to index 0 ("just after [current hour]") via % 12.
    rounded = min(int(round(minute / 5.0)), 11)
    word = spec["phrases"][rounded]
    # Most dialects flip to the next hour at 35-past ("twenty-five to ten");
    # German flips at 25-past so "halb zehn" / "fünf vor halb zehn" anchor on
    # the upcoming hour as native speakers expect.
    advance_at = spec.get("hour_advance_at", 7)
    display_hour = hour if rounded < advance_at else (hour + 1) % 24
    hour_12 = display_hour % 12 or 12
    is_pm = display_hour >= 12
    return word, spec["format_hour"](spec["hours"][hour_12], is_pm)


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
    """
    return (hash(("sketch", coord)) % 3) - 1


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


_TINY_SIZE = 14
_BODY_MAX_SIZE = 40
_BODY_MIN_SIZE = 14


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
            if (pb[3] - pb[1]) + 4 + (hb[3] - hb[1]) <= available_h:
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

    # Phrase + hour block: center their ink in the space above the footer.
    # Working in ink coordinates avoids bbox[1] artefacts shifting the visual
    # centre — fonts like Pacifico or Charis SIL carry large top offsets that
    # would otherwise push the block up or compress the inter-line gap.
    LINE_GAP = 4
    block_ink_h = phrase_ink_h + LINE_GAP + hour_ink_h
    phrase_ink_y = (footer_ink_top - block_ink_h) // 2

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


def sun_times(date, latitude, longitude):
    """Approximate sunrise and sunset for `date` at (latitude, longitude).

    Returns aware UTC datetimes (sunrise, sunset). `date` may be a `date` or
    `datetime`; only the calendar day is used. Returns (None, None) for polar
    night / midnight sun (the sun never crosses the horizon that day).

    Implementation follows NOAA's simplified solar position algorithm. Accuracy
    is within ~1 minute outside polar regions, which is plenty for "switch the
    clock theme around dusk".
    """
    n = date.timetuple().tm_yday
    # Fractional year (radians)
    gamma = 2 * math.pi / 365 * (n - 1)
    # Equation of time (minutes)
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    # Solar declination (radians)
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    lat_rad = math.radians(latitude)
    # 90.833° accounts for atmospheric refraction + the sun's apparent radius.
    cos_h = math.cos(math.radians(90.833)) / (math.cos(lat_rad) * math.cos(decl)) - math.tan(
        lat_rad
    ) * math.tan(decl)
    if cos_h > 1 or cos_h < -1:
        return None, None
    h_deg = math.degrees(math.acos(cos_h))

    # Times come out in minutes-from-UTC-midnight.
    sunrise_min = 720 - 4 * (longitude + h_deg) - eqtime
    sunset_min = 720 - 4 * (longitude - h_deg) - eqtime

    base = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    return (
        base + timedelta(minutes=sunrise_min),
        base + timedelta(minutes=sunset_min),
    )
