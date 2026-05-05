# Font variants

All previews show the same moment — `9:15 am` in the `classic` dialect — so the typefaces are directly comparable. The display is 250 × 122 px (Waveshare 2.13" e-ink, landscape).

Set the active font in `fuzzyclock_config.yaml`:

```yaml
font: libertinus
```

Or try one in a dry-run render:

```bash
python3 fuzzyClock2.py --dry-run --font libertinus --output preview.png
```

Unknown values fall back to `dejavu` with a warning in the daemon log.

## Random mode

```yaml
font: random
```

Picks a fresh vendored variant each time the time phrase rolls over to the next 5-minute bucket — every phrase change comes with a new typeface. Only fonts whose file is actually present in `fonts/` are eligible, so a clean Pi without any commercial faces dropped in still works (it just rolls from the OFL set). A short button-press refresh keeps the current font; the variant only changes when the phrase itself does.

---

## Sourcing

Each preview's `<sup>` line indicates how the font reaches the daemon:

- **`apt: ...`** — installed automatically by `deploy.sh` on the Pi; no extra steps.
- **`OFL · ...`** / **`Apache 2.0 · ...`** — vendored in this repo's `fonts/` directory; works on any machine.
- **`Commercial · drop ... into fonts/`** — no apt package and not redistributable here. Provide the file yourself; the daemon falls back to a macOS system font for dev renders when no file is present.

Variants are grouped by theme/vibe and sorted alphabetically within each group.

---

## Clean & everyday

Neutral, readable workhorses — for when you want the time to feel ordinary.

<table>
<tr>
<td align="center">
<img src="preview-cantarell.png" alt="cantarell"><br><br>
<strong><code>cantarell</code></strong><br>
<sup>apt: fonts-cantarell</sup><br>
GNOME's humanist sans — tall x-height, friendly curves.
</td>
<td align="center">
<img src="preview-dejavu.png" alt="dejavu"><br><br>
<strong><code>dejavu</code></strong> <em>(default)</em><br>
<sup>apt: fonts-dejavu-core</sup><br>
Clean humanist sans — high x-height, broad Unicode coverage.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-ubuntu.png" alt="ubuntu"><br><br>
<strong><code>ubuntu</code></strong><br>
<sup>apt: fonts-ubuntu</sup><br>
Distinctive warm sans with subtle calligraphic terminals.
</td>
<td></td>
</tr>
</table>

---

## Classic & literary serifs

Reading-focused serifs with traditional proportions — book pages and printed essays in miniature. The commercial drop-ins live here too: most were designed for long-form reading.

<table>
<tr>
<td align="center">
<img src="preview-bitter.png" alt="bitter"><br><br>
<strong><code>bitter</code></strong><br>
<sup>OFL · variable</sup><br>
High-contrast slab serif — confident vertical stress on e-ink.
</td>
<td align="center">
<img src="preview-charis-sil.png" alt="charis-sil"><br><br>
<strong><code>charis-sil</code></strong><br>
<sup>SIL OFL · static · apt: fonts-sil-charis</sup><br>
Warm humanist serif — generous x-height, broad glyph coverage.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-dejavu-serif.png" alt="dejavu-serif"><br><br>
<strong><code>dejavu-serif</code></strong><br>
<sup>apt: fonts-dejavu</sup><br>
Elegant transitional serif companion to DejaVu Sans.
</td>
<td align="center">
<img src="preview-liberation-serif.png" alt="liberation-serif"><br><br>
<strong><code>liberation-serif</code></strong><br>
<sup>apt: fonts-liberation2</sup><br>
Times-metric serif — newspaper feel, very readable at small sizes.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-libertinus.png" alt="libertinus"><br><br>
<strong><code>libertinus</code></strong><br>
<sup>OFL · static OTF</sup><br>
Open successor to Linux Libertine — classical book serif.
</td>
<td align="center">
<img src="preview-literata.png" alt="literata"><br><br>
<strong><code>literata</code></strong><br>
<sup>OFL · variable</sup><br>
Optically sized book serif — refined and even-toned.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-roboto-slab.png" alt="roboto-slab"><br><br>
<strong><code>roboto-slab</code></strong><br>
<sup>apt: fonts-roboto-slab</sup><br>
Chunky slab serif — renders especially crisply on e-ink.
</td>
<td></td>
</tr>
</table>

**Commercial drop-ins** — drop the listed file into `fonts/` to unlock:

| Variant | File | Publisher | Character |
|---------|------|-----------|-----------|
| `arno` | `ArnoPro-Bold.otf` | Adobe | Old-style text serif in the tradition of the early Venetian printers; compact and elegant. |
| `bookerly` | `Bookerly-Bold.ttf` | Amazon (Kindle) | Warm humanist serif designed for long reading sessions; optimised for screen rendering. |
| `chaparral` | `ChaparralPro-Bold.otf` | Adobe | Humanist slab serif blending serif warmth with slab structure; very even on e-ink. |
| `livory` | `Livory-Bold.otf` | iA (Information Architects) | Transitional serif with calligraphic warmth; designed for iA Writer. |
| `malabar` | `Malabar-Bold.otf` | Linotype | Sturdy hybrid serif with slab tendencies; originally designed for newspaper body text. |
| `minion` | `MinionPro-Bold.otf` | Adobe | Classic old-style serif inspired by Renaissance-era type; timeless and space-efficient. |

---

## Slab serif

Sturdy bracketed slabs — from crisp geometric (Arvo, Josefin Slab) to warm humanist (Zilla Slab) to chunky literary (Rokkitt) to softened slab terminals (Crete Round).

<table>
<tr>
<td align="center">
<img src="preview-arvo.png" alt="arvo"><br><br>
<strong><code>arvo</code></strong><br>
<sup>OFL · static</sup><br>
Clean geometric slab — high contrast, confident strokes.
</td>
<td align="center">
<img src="preview-crete-round.png" alt="crete-round"><br><br>
<strong><code>crete-round</code></strong><br>
<sup>OFL · static</sup><br>
Rounded slab terminals — soft-but-solid, distinctive feel.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-josefin-slab.png" alt="josefin-slab"><br><br>
<strong><code>josefin-slab</code></strong><br>
<sup>OFL · variable</sup><br>
Geometric slab — strong thin/thick contrast; elegant at display sizes.
</td>
<td align="center">
<img src="preview-rokkitt.png" alt="rokkitt"><br><br>
<strong><code>rokkitt</code></strong><br>
<sup>OFL · variable</sup><br>
Chunky literary slab — confident and even-toned on e-ink.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-zilla-slab.png" alt="zilla-slab"><br><br>
<strong><code>zilla-slab</code></strong><br>
<sup>OFL · static</sup><br>
Mozilla humanist slab — warm and screen-optimised.
</td>
<td></td>
</tr>
</table>

---

## Soft & rounded

Friendly geometric curves — informal warmth, approachable at any size.

<table>
<tr>
<td align="center">
<img src="preview-comfortaa.png" alt="comfortaa"><br><br>
<strong><code>comfortaa</code></strong><br>
<sup>OFL · variable · apt: fonts-comfortaa</sup><br>
Rounded geometric sans — warm and friendly.
</td>
<td align="center">
<img src="preview-fredoka.png" alt="fredoka"><br><br>
<strong><code>fredoka</code></strong><br>
<sup>OFL · variable · apt: fonts-fredoka</sup><br>
Rounded display — soft, friendly geometric shapes.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-jost.png" alt="jost"><br><br>
<strong><code>jost</code></strong><br>
<sup>OFL · variable</sup><br>
Geometric sans inspired by Futura — clean and modern.
</td>
<td align="center">
<img src="preview-lilita-one.png" alt="lilita-one"><br><br>
<strong><code>lilita-one</code></strong><br>
<sup>OFL · static</sup><br>
Chunky Latin display — bold and cartoonish in the best way.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-modak.png" alt="modak"><br><br>
<strong><code>modak</code></strong><br>
<sup>OFL · static</sup><br>
Extreme inflated bubble — letters look pressurized, Devanagari-inspired.
</td>
<td align="center">
<img src="preview-nunito.png" alt="nunito"><br><br>
<strong><code>nunito</code></strong><br>
<sup>OFL · variable</sup><br>
Rounded sans — generous x-height, approachable at any size.
</td>
</tr>
</table>

---

## Geometric & condensed

Clean geometric proportions and condensed widths — from balanced all-round workhorse to Art Deco elegance to space-saving condensed type. Condensed faces like Oswald fit longer fuzzy-time phrases on one line at a larger point size.

<table>
<tr>
<td align="center">
<img src="preview-cabin.png" alt="cabin"><br><br>
<strong><code>cabin</code></strong><br>
<sup>OFL · variable</sup><br>
Humanist geometric sans — slightly warmer than Poppins.
</td>
<td align="center">
<img src="preview-oswald.png" alt="oswald"><br><br>
<strong><code>oswald</code></strong><br>
<sup>OFL · variable</sup><br>
Condensed sans — fits long dialect phrases at a larger size.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-poppins.png" alt="poppins"><br><br>
<strong><code>poppins</code></strong><br>
<sup>OFL · static</sup><br>
Balanced geometric sans — uniform stroke, contemporary feel.
</td>
<td align="center">
<img src="preview-raleway.png" alt="raleway"><br><br>
<strong><code>raleway</code></strong><br>
<sup>OFL · variable</sup><br>
Art Deco geometric — distinctive double-storey 'W'.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-space-grotesk.png" alt="space-grotesk"><br><br>
<strong><code>space-grotesk</code></strong><br>
<sup>OFL · static</sup><br>
Quirky geometric sans — slightly irregular strokes give it personality.
</td>
<td align="center">
<img src="preview-work-sans.png" alt="work-sans"><br><br>
<strong><code>work-sans</code></strong><br>
<sup>OFL · variable</sup><br>
Utilitarian geometric sans — clean and legible at any size.
</td>
</tr>
</table>

---

## Bold display & poster

Big shouty character — signage, comic, slab, condensed. The clock as a poster.

<table>
<tr>
<td align="center">
<img src="preview-abril-fatface.png" alt="abril-fatface"><br><br>
<strong><code>abril-fatface</code></strong><br>
<sup>OFL · static</sup><br>
Fashion-magazine ultra-bold display serif — high contrast.
</td>
<td align="center">
<img src="preview-akronim.png" alt="akronim"><br><br>
<strong><code>akronim</code></strong><br>
<sup>OFL · static</sup><br>
Frantic outlined italic — loose hand-drawn caps, kinetic and untidy.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-alfa-slab-one.png" alt="alfa-slab-one"><br><br>
<strong><code>alfa-slab-one</code></strong><br>
<sup>OFL · static</sup><br>
Chunky bold slab — confident, immovable.
</td>
<td align="center">
<img src="preview-anton.png" alt="anton"><br><br>
<strong><code>anton</code></strong><br>
<sup>OFL · static</sup><br>
Tall condensed poster sans — fits long phrases easily.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-bangers.png" alt="bangers"><br><br>
<strong><code>bangers</code></strong><br>
<sup>OFL · static</sup><br>
Comic-book display — bold, condensed, pop-art energy.
</td>
<td align="center">
<img src="preview-boogaloo.png" alt="boogaloo"><br><br>
<strong><code>boogaloo</code></strong><br>
<sup>OFL · static</sup><br>
Retro casual comic/poster — lighter and breezier than Bangers.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-bungee.png" alt="bungee"><br><br>
<strong><code>bungee</code></strong><br>
<sup>OFL · static</sup><br>
David Jonathan Ross signage face — architectural and bold.
</td>
<td align="center">
<img src="preview-bungee-shade.png" alt="bungee-shade"><br><br>
<strong><code>bungee-shade</code></strong><br>
<sup>OFL · static</sup><br>
3D perspective shadow block below each letter — architectural and striking.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-faster-one.png" alt="faster-one"><br><br>
<strong><code>faster-one</code></strong><br>
<sup>OFL · static</sup><br>
Extreme italic condensed — maximum rightward lean, racing energy.
</td>
<td align="center">
<img src="preview-henny-penny.png" alt="henny-penny"><br><br>
<strong><code>henny-penny</code></strong><br>
<sup>OFL · static</sup><br>
Wobbly storybook display — organic stroke widths, pleasantly falling apart.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-luckiest-guy.png" alt="luckiest-guy"><br><br>
<strong><code>luckiest-guy</code></strong><br>
<sup>OFL · static</sup><br>
Cereal-box cartoon — irregular baseline, high-energy retro fun.
</td>
<td align="center">
<img src="preview-playfair.png" alt="playfair"><br><br>
<strong><code>playfair</code></strong><br>
<sup>OFL · variable</sup><br>
High-contrast display serif — dramatic stroke variation.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-ribeye-marrow.png" alt="ribeye-marrow"><br><br>
<strong><code>ribeye-marrow</code></strong><br>
<sup>OFL · static</sup><br>
Hollow inline display serif — only the outline remains, marrow scooped out.
</td>
<td align="center">
<img src="preview-righteous.png" alt="righteous"><br><br>
<strong><code>righteous</code></strong><br>
<sup>OFL · static</sup><br>
Art Deco geometric sans — retro-modern personality.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-shrikhand.png" alt="shrikhand"><br><br>
<strong><code>shrikhand</code></strong><br>
<sup>OFL · static</sup><br>
Gujarati calligraphy-inspired bold — ink traps and terminals unlike any Latin font.
</td>
<td align="center">
<img src="preview-staatliches.png" alt="staatliches"><br><br>
<strong><code>staatliches</code></strong><br>
<sup>OFL · static</sup><br>
Bauhaus all-caps — extreme width contrast.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-titan-one.png" alt="titan-one"><br><br>
<strong><code>titan-one</code></strong><br>
<sup>OFL · static</sup><br>
Super-chunky rounded bold — compact punch, maximum presence.
</td>
<td></td>
</tr>
</table>

**Commercial drop-ins** — drop the listed file into `fonts/` to unlock:

| Variant | File | Publisher | Character |
|---------|------|-----------|-----------|
| `pigeonette` | `Pigeonette-Bold.otf`, `Pigeonette-Regular.otf`, or `Pigeonette.otf` | Tortilla Studio ([Future Fonts](https://www.futurefonts.xyz/tortillastudio/pigeonette)) | Idiosyncratic display serif with expressive stroke contrast. |

### More bold display

<table>
<tr>
<td align="center">
<img src="preview-chango.png" alt="chango"><br><br>
<strong><code>chango</code></strong><br>
<sup>OFL · static</sup><br>
Single-weight ultra-heavy Latin display — fills every pixel with imposing mass.
</td>
<td align="center">
<img src="preview-gravitas-one.png" alt="gravitas-one"><br><br>
<strong><code>gravitas-one</code></strong><br>
<sup>OFL · static</sup><br>
Maximum-weight display serif — brutal ink coverage, deep ink traps.
</td>
</tr>
</table>

---

## Vintage, deco & futuristic

1920s marquee through retro-futuristic chrome — Wild West poster type, Art Deco, Art Nouveau, Space Age, sci-fi.

<table>
<tr>
<td align="center">
<img src="preview-atomic-age.png" alt="atomic-age"><br><br>
<strong><code>atomic-age</code></strong><br>
<sup>OFL · static</sup><br>
Outlined Space Age display — '50s science-fiction inline.
</td>
<td align="center">
<img src="preview-audiowide.png" alt="audiowide"><br><br>
<strong><code>audiowide</code></strong><br>
<sup>OFL · static</sup><br>
Retro-futuristic chrome — hi-fi receiver vibe.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-cinzel-decorative.png" alt="cinzel-decorative"><br><br>
<strong><code>cinzel-decorative</code></strong><br>
<sup>OFL · static</sup><br>
Ornate Roman capitals with Art Deco serifs — regal, all-caps only.
</td>
<td align="center">
<img src="preview-diplomata.png" alt="diplomata"><br><br>
<strong><code>diplomata</code></strong><br>
<sup>OFL · static</sup><br>
Heavily ornamented Art Deco caps — diploma-grade engraving.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-exo-2.png" alt="exo-2"><br><br>
<strong><code>exo-2</code></strong><br>
<sup>OFL · variable</sup><br>
Techno-geometric variable — bridges vintage and sci-fi.
</td>
<td align="center">
<img src="preview-fascinate.png" alt="fascinate"><br><br>
<strong><code>fascinate</code></strong><br>
<sup>OFL · static</sup><br>
Art Deco inline — white channel through each stroke, striking on e-ink.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-forum.png" alt="forum"><br><br>
<strong><code>forum</code></strong><br>
<sup>OFL · static</sup><br>
Elegant Art Nouveau Roman — calligraphic influence, lighter than Cinzel.
</td>
<td align="center">
<img src="preview-iceland.png" alt="iceland"><br><br>
<strong><code>iceland</code></strong><br>
<sup>OFL · static</sup><br>
Geometric blocky display — Nordic rune-like construction.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-limelight.png" alt="limelight"><br><br>
<strong><code>limelight</code></strong><br>
<sup>OFL · static</sup><br>
1920s theatre marquee — vintage display serif.
</td>
<td align="center">
<img src="preview-megrim.png" alt="megrim"><br><br>
<strong><code>megrim</code></strong><br>
<sup>OFL · static</sup><br>
Constructed thin-stroke Art Nouveau — built from straight lines and circles.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-monoton.png" alt="monoton"><br><br>
<strong><code>monoton</code></strong><br>
<sup>OFL · static</sup><br>
Multi-line striped art-deco caps — striking silhouette.
</td>
<td align="center">
<img src="preview-orbitron.png" alt="orbitron"><br><br>
<strong><code>orbitron</code></strong><br>
<sup>OFL · variable</sup><br>
Geometric sci-fi display — clean techno feel.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-poiret-one.png" alt="poiret-one"><br><br>
<strong><code>poiret-one</code></strong><br>
<sup>OFL · static</sup><br>
Art Deco hairline geometric — distinctive thin strokes.
</td>
<td align="center">
<img src="preview-rye.png" alt="rye"><br><br>
<strong><code>rye</code></strong><br>
<sup>OFL · static</sup><br>
Wild West poster — ornate inline decorations inside every bracketed serif.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-sancreek.png" alt="sancreek"><br><br>
<strong><code>sancreek</code></strong><br>
<sup>OFL · static</sup><br>
Wild West cracked engraved poster serif — wanted-poster energy.
</td>
<td align="center">
<img src="preview-smokum.png" alt="smokum"><br><br>
<strong><code>smokum</code></strong><br>
<sup>Apache 2.0 · static</sup><br>
Western circus marquee — outlined slab with curling smoke wisps.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-syncopate.png" alt="syncopate"><br><br>
<strong><code>syncopate</code></strong><br>
<sup>Apache 2.0 · static</sup><br>
All-caps techno geometric — architectural, no lowercase glyphs.
</td>
<td align="center">
<img src="preview-wallpoet.png" alt="wallpoet"><br><br>
<strong><code>wallpoet</code></strong><br>
<sup>OFL · static</sup><br>
Chiselled stone techno — block letters with horizontal grooves cut through every stroke.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-baumans.png" alt="baumans"><br><br>
<strong><code>baumans</code></strong><br>
<sup>OFL · static</sup><br>
Techno-mechanical constructed from circles and straight rules — hi-fi instrument dials.
</td>
<td align="center">
<img src="preview-mystery-quest.png" alt="mystery-quest"><br><br>
<strong><code>mystery-quest</code></strong><br>
<sup>OFL · static</sup><br>
Alien sci-fi display — letterforms with UFO-landing-zone cut-outs and strange angular gaps.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-oi.png" alt="oi"><br><br>
<strong><code>oi</code></strong><br>
<sup>OFL · static</sup><br>
Victorian ornamental display — elaborate swash caps with inline filigree decoration.
</td>
<td align="center">
<img src="preview-emblema-one.png" alt="emblema-one"><br><br>
<strong><code>emblema-one</code></strong><br>
<sup>OFL · static</sup><br>
Outlined decorative display — inline channels carved through bold exotic caps.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-flamenco.png" alt="flamenco"><br><br>
<strong><code>flamenco</code></strong><br>
<sup>OFL · static</sup><br>
Art Nouveau calligraphic display — organic curved spurs growing from every terminal.
</td>
<td align="center">
<img src="preview-tourney.png" alt="tourney"><br><br>
<strong><code>tourney</code></strong><br>
<sup>OFL · variable</sup><br>
Racing championship variable — extreme condensed wdth axis, chequered-flag energy.
</td>
</tr>
</table>

---

## Retro & computing

Terminal, pixel, 8-bit nostalgia — plus the variable oddities that warp through machined and folded territory.

<table>
<tr>
<td align="center">
<img src="preview-courier-prime.png" alt="courier-prime"><br><br>
<strong><code>courier-prime</code></strong><br>
<sup>OFL · static</sup><br>
Refined typewriter serif — more character than Courier New.
</td>
<td align="center">
<img src="preview-fira-mono.png" alt="fira-mono"><br><br>
<strong><code>fira-mono</code></strong><br>
<sup>OFL · static</sup><br>
Clean coding mono — readable and refined at small sizes.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-foldit.png" alt="foldit"><br><br>
<strong><code>foldit</code></strong><br>
<sup>OFL · variable</sup><br>
Origami creased letterforms — every stroke looks like folded paper.
</td>
<td align="center">
<img src="preview-jetbrains-mono.png" alt="jetbrains-mono"><br><br>
<strong><code>jetbrains-mono</code></strong><br>
<sup>apt: fonts-jetbrains-mono</sup><br>
Modern monospaced — typewriter personality on e-ink.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-press-start-2p.png" alt="press-start-2p"><br><br>
<strong><code>press-start-2p</code></strong><br>
<sup>OFL · static</sup><br>
8-bit arcade pixel font — quarter-eating energy.
</td>
<td align="center">
<img src="preview-share-tech-mono.png" alt="share-tech-mono"><br><br>
<strong><code>share-tech-mono</code></strong><br>
<sup>OFL · static</sup><br>
Techno grid mono — sci-fi terminal aesthetic.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-silkscreen.png" alt="silkscreen"><br><br>
<strong><code>silkscreen</code></strong><br>
<sup>OFL · static</sup><br>
Bitmap-style display — late-90s desktop UI nostalgia.
</td>
<td align="center">
<img src="preview-sixtyfour.png" alt="sixtyfour"><br><br>
<strong><code>sixtyfour</code></strong><br>
<sup>OFL · variable</sup><br>
C64 CRT scanlines — retro-computing pixel grid with deliberate bleed.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-vt323.png" alt="vt323"><br><br>
<strong><code>vt323</code></strong><br>
<sup>OFL · static</sup><br>
CRT terminal — chunky monospace, late-70s computing.
</td>
<td align="center">
<img src="preview-workbench.png" alt="workbench"><br><br>
<strong><code>workbench</code></strong><br>
<sup>OFL · variable</sup><br>
Machined dot-matrix industrial — bled and scanned axes give workshop-printer feel.
</td>
</tr>
</table>

---

## Blackletter & fantasy

Medieval, gothic, storybook — manuscripts, spellbooks, and angular runic geometry.

<table>
<tr>
<td align="center">
<img src="preview-almendra-display.png" alt="almendra-display"><br><br>
<strong><code>almendra-display</code></strong><br>
<sup>OFL · static</sup><br>
Pen-drawn Gothic calligraphic — elaborate ink swells, medieval fantasy.
</td>
<td align="center">
<img src="preview-astloch.png" alt="astloch"><br><br>
<strong><code>astloch</code></strong><br>
<sup>OFL · static</sup><br>
Bold runic medieval — angular geometric blackletter built from sharp wedges.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-medieval-sharp.png" alt="medieval-sharp"><br><br>
<strong><code>medieval-sharp</code></strong><br>
<sup>OFL · static</sup><br>
Storybook fantasy — readable medieval display.
</td>
<td align="center">
<img src="preview-nabla.png" alt="nabla"><br><br>
<strong><code>nabla</code></strong><br>
<sup>OFL · variable · COLR/CPAL</sup><br>
3D faceted extrusion designed as a colour font; renders on e-ink as nested outlined geometry — gothic, structural, unlike anything else here.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-pirata-one.png" alt="pirata-one"><br><br>
<strong><code>pirata-one</code></strong><br>
<sup>OFL · static</sup><br>
Decorative pirate / treasure-map blackletter.
</td>
<td align="center">
<img src="preview-unifraktur-maguntia.png" alt="unifraktur-maguntia"><br><br>
<strong><code>unifraktur-maguntia</code></strong><br>
<sup>OFL · static</sup><br>
Full gothic blackletter — medieval manuscript feel.
</td>
</tr>
</table>

---

## Flowing script & calligraphy

Flowing connected cursives and formal calligraphic scripts — elegant, personal, occasion-ready. Bold weights where available; thin-stroked faces like Tangerine and Parisienne may look delicate at small auto-sizes.

<table>
<tr>
<td align="center">
<img src="preview-clicker-script.png" alt="clicker-script"><br><br>
<strong><code>clicker-script</code></strong><br>
<sup>OFL · static</sup><br>
Thick connecting brush script — bold and legible on e-ink.
</td>
<td align="center">
<img src="preview-dancing-script.png" alt="dancing-script"><br><br>
<strong><code>dancing-script</code></strong><br>
<sup>OFL · variable</sup><br>
Flowing connected cursive — the most popular script on Google Fonts.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-parisienne.png" alt="parisienne"><br><br>
<strong><code>parisienne</code></strong><br>
<sup>OFL · static</sup><br>
French ornamental script — decorative loops and flourishes.
</td>
<td align="center">
<img src="preview-splash.png" alt="splash"><br><br>
<strong><code>splash</code></strong><br>
<sup>OFL · static</sup><br>
Liquid brush splash — connected calligraphic ink, very wet.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-tangerine.png" alt="tangerine"><br><br>
<strong><code>tangerine</code></strong><br>
<sup>OFL · static</sup><br>
Elegant copperplate calligraphy — refined and formal.
</td>
<td align="center">
<img src="preview-yellowtail.png" alt="yellowtail"><br><br>
<strong><code>yellowtail</code></strong><br>
<sup>Apache 2.0 · static</sup><br>
Condensed calligraphic brush — stylish and compact.
</td>
</tr>
</table>

---

## Handwriting & casual script

Cursive, brush, typewriter, marker — informal, hand-made character.

<table>
<tr>
<td align="center">
<img src="preview-lobster.png" alt="lobster"><br><br>
<strong><code>lobster</code></strong><br>
<sup>OFL · static</sup><br>
Bold script — heavier and more decorative than Pacifico.
</td>
<td align="center">
<img src="preview-pacifico.png" alt="pacifico"><br><br>
<strong><code>pacifico</code></strong><br>
<sup>OFL · static</sup><br>
Casual brush-script — maximally playful.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-permanent-marker.png" alt="permanent-marker"><br><br>
<strong><code>permanent-marker</code></strong><br>
<sup>Apache 2.0 · static</sup><br>
Felt-tip handwriting — looks like whiteboard scribble.
</td>
<td align="center">
<img src="preview-special-elite.png" alt="special-elite"><br><br>
<strong><code>special-elite</code></strong><br>
<sup>Apache 2.0 · static</sup><br>
Distressed typewriter — uneven inking, ribbon strikes.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-unkempt.png" alt="unkempt"><br><br>
<strong><code>unkempt</code></strong><br>
<sup>Apache 2.0 · static</sup><br>
Scrawly asymmetric handwriting — deliberately wild loops, uneven baseline, zero composure.
</td>
<td></td>
</tr>
</table>

---

## Notebook & hand-drawn

Ballpoint, marker, classroom print — neat hand-made character that still reads cleanly at clock size.

<table>
<tr>
<td align="center">
<img src="preview-amatic-sc.png" alt="amatic-sc"><br><br>
<strong><code>amatic-sc</code></strong><br>
<sup>OFL · static</sup><br>
Tall thin all-caps handwritten — fits long phrases.
</td>
<td align="center">
<img src="preview-architects-daughter.png" alt="architects-daughter"><br><br>
<strong><code>architects-daughter</code></strong><br>
<sup>OFL · static</sup><br>
Neat block-letter print — drafting-style hand.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-caveat.png" alt="caveat"><br><br>
<strong><code>caveat</code></strong><br>
<sup>OFL · variable</sup><br>
Connected ballpoint cursive — quick personal notes.
</td>
<td align="center">
<img src="preview-gloria-hallelujah.png" alt="gloria-hallelujah"><br><br>
<strong><code>gloria-hallelujah</code></strong><br>
<sup>Apache 2.0 · static</sup><br>
Loose kid-like print — wobbly baseline, joyful.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-homemade-apple.png" alt="homemade-apple"><br><br>
<strong><code>homemade-apple</code></strong><br>
<sup>Apache 2.0 · static</sup><br>
Quick handwritten cursive — looped and personal.
</td>
<td align="center">
<img src="preview-indie-flower.png" alt="indie-flower"><br><br>
<strong><code>indie-flower</code></strong><br>
<sup>Apache 2.0 · static</sup><br>
Bouncy uneven print — friendly and informal.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-kalam.png" alt="kalam"><br><br>
<strong><code>kalam</code></strong><br>
<sup>OFL · static</sup><br>
Rounded everyday handwriting — Indian Type Foundry.
</td>
<td align="center">
<img src="preview-patrick-hand.png" alt="patrick-hand"><br><br>
<strong><code>patrick-hand</code></strong><br>
<sup>OFL · static</sup><br>
Open clean handwriting — very legible at small sizes.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-reenie-beanie.png" alt="reenie-beanie"><br><br>
<strong><code>reenie-beanie</code></strong><br>
<sup>OFL · static</sup><br>
Slanted notebook scribble — back-of-the-book doodle.
</td>
<td align="center">
<img src="preview-shadows-into-light.png" alt="shadows-into-light"><br><br>
<strong><code>shadows-into-light</code></strong><br>
<sup>OFL · static</sup><br>
Light marker on paper — airy, softly slanted.
</td>
</tr>
</table>

---

## Textured & experimental

Letterforms filled with pattern, texture, distortion, or melted into puddles — appearance over legibility. The Rubik Filtered family ships a wide collection of weirdness modes from the same chassis; the rest are one-off oddities.

<table>
<tr>
<td align="center">
<img src="preview-codystar.png" alt="codystar"><br><br>
<strong><code>codystar</code></strong><br>
<sup>OFL · static</sup><br>
Star-pattern stencil — letterforms assembled from clusters of dots.
</td>
<td align="center">
<img src="preview-freckle-face.png" alt="freckle-face"><br><br>
<strong><code>freckle-face</code></strong><br>
<sup>OFL · static</sup><br>
Speckled / freckled letterforms — each character has a pressed-in texture.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-plaster.png" alt="plaster"><br><br>
<strong><code>plaster</code></strong><br>
<sup>OFL · static</sup><br>
Heavy stencil plaster — slab industrial relief, feels poured.
</td>
<td align="center">
<img src="preview-rampart-one.png" alt="rampart-one"><br><br>
<strong><code>rampart-one</code></strong><br>
<sup>OFL · static</sup><br>
Letters built from masonry — towers, ramparts, and brick walls.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-rubik-beastly.png" alt="rubik-beastly"><br><br>
<strong><code>rubik-beastly</code></strong><br>
<sup>OFL · static</sup><br>
Chunky furry-creature shapes — letters that look like tiny beasts.
</td>
<td align="center">
<img src="preview-rubik-dirt.png" alt="rubik-dirt"><br><br>
<strong><code>rubik-dirt</code></strong><br>
<sup>OFL · static</sup><br>
Dirt and debris embedded in the strokes — deliberately rough fill.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-rubik-distressed.png" alt="rubik-distressed"><br><br>
<strong><code>rubik-distressed</code></strong><br>
<sup>OFL · static</sup><br>
Heavily eroded grunge — letters that look worn down by sandpaper.
</td>
<td align="center">
<img src="preview-rubik-glitch.png" alt="rubik-glitch"><br><br>
<strong><code>rubik-glitch</code></strong><br>
<sup>OFL · static</sup><br>
Letters torn apart by digital glitch — slipped slices and corrupted shapes.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-rubik-iso.png" alt="rubik-iso"><br><br>
<strong><code>rubik-iso</code></strong><br>
<sup>OFL · static</sup><br>
Isometric 3D outlined — architectural perspective on every glyph.
</td>
<td align="center">
<img src="preview-rubik-maze.png" alt="rubik-maze"><br><br>
<strong><code>rubik-maze</code></strong><br>
<sup>OFL · static</sup><br>
Every stroke filled with a continuous maze pattern — genuinely strange.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-rubik-microbe.png" alt="rubik-microbe"><br><br>
<strong><code>rubik-microbe</code></strong><br>
<sup>OFL · static</sup><br>
Cellular microbe texture across every stroke — petri-dish typography.
</td>
<td align="center">
<img src="preview-rubik-puddles.png" alt="rubik-puddles"><br><br>
<strong><code>rubik-puddles</code></strong><br>
<sup>OFL · static</sup><br>
Letterforms melted into puddles — gravity won.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-rubik-spray-paint.png" alt="rubik-spray-paint"><br><br>
<strong><code>rubik-spray-paint</code></strong><br>
<sup>OFL · static</sup><br>
Spray-painted stencil with overspray dots — graffiti-tag energy.
</td>
<td align="center">
<img src="preview-rubik-wet-paint.png" alt="rubik-wet-paint"><br><br>
<strong><code>rubik-wet-paint</code></strong><br>
<sup>OFL · static</sup><br>
Paint dripping down each stroke — fresh-coat-of-paint vandalism.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-kablammo.png" alt="kablammo"><br><br>
<strong><code>kablammo</code></strong><br>
<sup>OFL · variable · MORF axis</sup><br>
Inflated balloon variable font — the MORF axis bloats letterforms into pressurised rubber bubbles.
</td>
<td></td>
</tr>
</table>

---

## Horror & macabre

Drippy, bitten, blood-spattered, skeletal letterforms — the Halloween / horror corner of the gallery.

<table>
<tr>
<td align="center">
<img src="preview-butcherman.png" alt="butcherman"><br><br>
<strong><code>butcherman</code></strong><br>
<sup>OFL · static</sup><br>
Splatter horror display — uneven, ragged, slightly threatening.
</td>
<td align="center">
<img src="preview-creepster.png" alt="creepster"><br><br>
<strong><code>creepster</code></strong><br>
<sup>OFL · static</sup><br>
Halloween / horror display — seasonal novelty.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-eater.png" alt="eater"><br><br>
<strong><code>eater</code></strong><br>
<sup>OFL · static</sup><br>
Bites taken out of the letterforms — gnawed-on type.
</td>
<td align="center">
<img src="preview-jolly-lodger.png" alt="jolly-lodger"><br><br>
<strong><code>jolly-lodger</code></strong><br>
<sup>OFL · static</sup><br>
Skeletal carnival display — hollow-bone strokes, slightly creepy fairground.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-lacquer.png" alt="lacquer"><br><br>
<strong><code>lacquer</code></strong><br>
<sup>OFL · static</sup><br>
Thick lacquered marker — wet-glossy painted strokes.
</td>
<td align="center">
<img src="preview-nosifer.png" alt="nosifer"><br><br>
<strong><code>nosifer</code></strong><br>
<sup>OFL · static</sup><br>
Blood dripping from every stroke — proper Halloween horror.
</td>
</tr>
</table>
