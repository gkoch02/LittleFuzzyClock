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

---

## Clean & everyday

Neutral, readable workhorses — for when you want the time to feel ordinary.

<table>
<tr>
<td align="center">
<img src="preview-dejavu.png" alt="dejavu"><br><br>
<strong><code>dejavu</code></strong> <em>(default)</em><br>
<sup>apt: fonts-dejavu-core</sup><br>
Clean humanist sans — high x-height, broad Unicode coverage.
</td>
<td align="center">
<img src="preview-cantarell.png" alt="cantarell"><br><br>
<strong><code>cantarell</code></strong><br>
<sup>apt: fonts-cantarell</sup><br>
GNOME's humanist sans — tall x-height, friendly curves.
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
<img src="preview-literata.png" alt="literata"><br><br>
<strong><code>literata</code></strong><br>
<sup>OFL · variable</sup><br>
Optically sized book serif — refined and even-toned.
</td>
<td align="center">
<img src="preview-libertinus.png" alt="libertinus"><br><br>
<strong><code>libertinus</code></strong><br>
<sup>OFL · static OTF</sup><br>
Open successor to Linux Libertine — classical book serif.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-charis-sil.png" alt="charis-sil"><br><br>
<strong><code>charis-sil</code></strong><br>
<sup>SIL OFL · static · apt: fonts-sil-charis</sup><br>
Warm humanist serif — generous x-height, broad glyph coverage.
</td>
<td align="center">
<img src="preview-bitter.png" alt="bitter"><br><br>
<strong><code>bitter</code></strong><br>
<sup>OFL · variable</sup><br>
High-contrast slab serif — confident vertical stress on e-ink.
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
| `bookerly` | `Bookerly-Bold.ttf` | Amazon (Kindle) | Warm humanist serif designed for long reading sessions; optimised for screen rendering. |
| `minion` | `MinionPro-Bold.otf` | Adobe | Classic old-style serif inspired by Renaissance-era type; timeless and space-efficient. |
| `livory` | `Livory-Bold.otf` | iA (Information Architects) | Transitional serif with calligraphic warmth; designed for iA Writer. |
| `chaparral` | `ChaparralPro-Bold.otf` | Adobe | Humanist slab serif blending serif warmth with slab structure; very even on e-ink. |
| `arno` | `ArnoPro-Bold.otf` | Adobe | Old-style text serif in the tradition of the early Venetian printers; compact and elegant. |
| `malabar` | `Malabar-Bold.otf` | Linotype | Sturdy hybrid serif with slab tendencies; originally designed for newspaper body text. |

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
<img src="preview-zilla-slab.png" alt="zilla-slab"><br><br>
<strong><code>zilla-slab</code></strong><br>
<sup>OFL · static</sup><br>
Mozilla humanist slab — warm and screen-optimised.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-rokkitt.png" alt="rokkitt"><br><br>
<strong><code>rokkitt</code></strong><br>
<sup>OFL · variable</sup><br>
Chunky literary slab — confident and even-toned on e-ink.
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
<td></td>
</tr>
</table>

---

## Soft & rounded

Friendly geometric curves — informal warmth, approachable at any size.

<table>
<tr>
<td align="center">
<img src="preview-fredoka.png" alt="fredoka"><br><br>
<strong><code>fredoka</code></strong><br>
<sup>OFL · variable · apt: fonts-fredoka</sup><br>
Rounded display — soft, friendly geometric shapes.
</td>
<td align="center">
<img src="preview-comfortaa.png" alt="comfortaa"><br><br>
<strong><code>comfortaa</code></strong><br>
<sup>OFL · variable · apt: fonts-comfortaa</sup><br>
Rounded geometric sans — warm and friendly.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-nunito.png" alt="nunito"><br><br>
<strong><code>nunito</code></strong><br>
<sup>OFL · variable</sup><br>
Rounded sans — generous x-height, approachable at any size.
</td>
<td align="center">
<img src="preview-jost.png" alt="jost"><br><br>
<strong><code>jost</code></strong><br>
<sup>OFL · variable</sup><br>
Geometric sans inspired by Futura — clean and modern.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-lilita-one.png" alt="lilita-one"><br><br>
<strong><code>lilita-one</code></strong><br>
<sup>OFL · static</sup><br>
Chunky Latin display — bold and cartoonish in the best way.
</td>
<td></td>
</tr>
</table>

---

## Geometric & condensed

Clean geometric proportions and condensed widths — from balanced all-round workhorse to Art Deco elegance to space-saving condensed type. Condensed faces like Oswald fit longer fuzzy-time phrases on one line at a larger point size.

<table>
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
<img src="preview-oswald.png" alt="oswald"><br><br>
<strong><code>oswald</code></strong><br>
<sup>OFL · variable</sup><br>
Condensed sans — fits long dialect phrases at a larger size.
</td>
<td align="center">
<img src="preview-work-sans.png" alt="work-sans"><br><br>
<strong><code>work-sans</code></strong><br>
<sup>OFL · variable</sup><br>
Utilitarian geometric sans — clean and legible at any size.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-cabin.png" alt="cabin"><br><br>
<strong><code>cabin</code></strong><br>
<sup>OFL · variable</sup><br>
Humanist geometric sans — slightly warmer than Poppins.
</td>
<td align="center">
<img src="preview-space-grotesk.png" alt="space-grotesk"><br><br>
<strong><code>space-grotesk</code></strong><br>
<sup>OFL · static</sup><br>
Quirky geometric sans — slightly irregular strokes give it personality.
</td>
</tr>
</table>

---

## Bold display & poster

Big shouty character — signage, comic, slab, condensed. The clock as a poster.

<table>
<tr>
<td align="center">
<img src="preview-bangers.png" alt="bangers"><br><br>
<strong><code>bangers</code></strong><br>
<sup>OFL · static</sup><br>
Comic-book display — bold, condensed, pop-art energy.
</td>
<td align="center">
<img src="preview-bungee.png" alt="bungee"><br><br>
<strong><code>bungee</code></strong><br>
<sup>OFL · static</sup><br>
David Jonathan Ross signage face — architectural and bold.
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
<img src="preview-staatliches.png" alt="staatliches"><br><br>
<strong><code>staatliches</code></strong><br>
<sup>OFL · static</sup><br>
Bauhaus all-caps — extreme width contrast.
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
<img src="preview-abril-fatface.png" alt="abril-fatface"><br><br>
<strong><code>abril-fatface</code></strong><br>
<sup>OFL · static</sup><br>
Fashion-magazine ultra-bold display serif — high contrast.
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
<img src="preview-creepster.png" alt="creepster"><br><br>
<strong><code>creepster</code></strong><br>
<sup>OFL · static</sup><br>
Halloween / horror display — seasonal novelty.
</td>
<td align="center">
<img src="preview-luckiest-guy.png" alt="luckiest-guy"><br><br>
<strong><code>luckiest-guy</code></strong><br>
<sup>OFL · static</sup><br>
Cereal-box cartoon — irregular baseline, high-energy retro fun.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-titan-one.png" alt="titan-one"><br><br>
<strong><code>titan-one</code></strong><br>
<sup>OFL · static</sup><br>
Super-chunky rounded bold — compact punch, maximum presence.
</td>
<td align="center">
<img src="preview-boogaloo.png" alt="boogaloo"><br><br>
<strong><code>boogaloo</code></strong><br>
<sup>OFL · static</sup><br>
Retro casual comic/poster — lighter and breezier than Bangers.
</td>
</tr>
</table>

**Commercial drop-ins** — drop the listed file into `fonts/` to unlock:

| Variant | File | Publisher | Character |
|---------|------|-----------|-----------|
| `pigeonette` | `Pigeonette-Bold.otf`, `Pigeonette-Regular.otf`, or `Pigeonette.otf` | Tortilla Studio ([Future Fonts](https://www.futurefonts.xyz/tortillastudio/pigeonette)) | Idiosyncratic display serif with expressive stroke contrast. |

---

## Retro & computing

Terminal, pixel, 8-bit nostalgia.

<table>
<tr>
<td align="center">
<img src="preview-vt323.png" alt="vt323"><br><br>
<strong><code>vt323</code></strong><br>
<sup>OFL · static</sup><br>
CRT terminal — chunky monospace, late-70s computing.
</td>
<td align="center">
<img src="preview-press-start-2p.png" alt="press-start-2p"><br><br>
<strong><code>press-start-2p</code></strong><br>
<sup>OFL · static</sup><br>
8-bit arcade pixel font — quarter-eating energy.
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
<img src="preview-jetbrains-mono.png" alt="jetbrains-mono"><br><br>
<strong><code>jetbrains-mono</code></strong><br>
<sup>apt: fonts-jetbrains-mono</sup><br>
Modern monospaced — typewriter personality on e-ink.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-fira-mono.png" alt="fira-mono"><br><br>
<strong><code>fira-mono</code></strong><br>
<sup>OFL · static</sup><br>
Clean coding mono — readable and refined at small sizes.
</td>
<td align="center">
<img src="preview-courier-prime.png" alt="courier-prime"><br><br>
<strong><code>courier-prime</code></strong><br>
<sup>OFL · static</sup><br>
Refined typewriter serif — more character than Courier New.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-share-tech-mono.png" alt="share-tech-mono"><br><br>
<strong><code>share-tech-mono</code></strong><br>
<sup>OFL · static</sup><br>
Techno grid mono — sci-fi terminal aesthetic.
</td>
<td></td>
</tr>
</table>

---

## Vintage, deco & futuristic

1920s marquee through retro-futuristic chrome.

<table>
<tr>
<td align="center">
<img src="preview-monoton.png" alt="monoton"><br><br>
<strong><code>monoton</code></strong><br>
<sup>OFL · static</sup><br>
Multi-line striped art-deco caps — striking silhouette.
</td>
<td align="center">
<img src="preview-limelight.png" alt="limelight"><br><br>
<strong><code>limelight</code></strong><br>
<sup>OFL · static</sup><br>
1920s theatre marquee — vintage display serif.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-audiowide.png" alt="audiowide"><br><br>
<strong><code>audiowide</code></strong><br>
<sup>OFL · static</sup><br>
Retro-futuristic chrome — hi-fi receiver vibe.
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
<img src="preview-syncopate.png" alt="syncopate"><br><br>
<strong><code>syncopate</code></strong><br>
<sup>Apache 2.0 · static</sup><br>
All-caps techno geometric — architectural, no lowercase glyphs.
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
<img src="preview-cinzel-decorative.png" alt="cinzel-decorative"><br><br>
<strong><code>cinzel-decorative</code></strong><br>
<sup>OFL · static</sup><br>
Ornate Roman capitals with Art Deco serifs — regal, all-caps only.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-fascinate.png" alt="fascinate"><br><br>
<strong><code>fascinate</code></strong><br>
<sup>OFL · static</sup><br>
Art Deco inline — white channel through each stroke, striking on e-ink.
</td>
<td align="center">
<img src="preview-forum.png" alt="forum"><br><br>
<strong><code>forum</code></strong><br>
<sup>OFL · static</sup><br>
Elegant Art Nouveau Roman — calligraphic influence, lighter than Cinzel.
</td>
</tr>
</table>

---

## Blackletter & fantasy

Medieval, gothic, storybook.

<table>
<tr>
<td align="center">
<img src="preview-unifraktur-maguntia.png" alt="unifraktur-maguntia"><br><br>
<strong><code>unifraktur-maguntia</code></strong><br>
<sup>OFL · static</sup><br>
Full gothic blackletter — medieval manuscript feel.
</td>
<td align="center">
<img src="preview-medieval-sharp.png" alt="medieval-sharp"><br><br>
<strong><code>medieval-sharp</code></strong><br>
<sup>OFL · static</sup><br>
Storybook fantasy — readable medieval display.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-pirata-one.png" alt="pirata-one"><br><br>
<strong><code>pirata-one</code></strong><br>
<sup>OFL · static</sup><br>
Decorative pirate / treasure-map blackletter.
</td>
<td></td>
</tr>
</table>

---

## Handwriting & script

Cursive, brush, typewriter, marker — informal, hand-made character.

<table>
<tr>
<td align="center">
<img src="preview-pacifico.png" alt="pacifico"><br><br>
<strong><code>pacifico</code></strong><br>
<sup>OFL · static</sup><br>
Casual brush-script — maximally playful.
</td>
<td align="center">
<img src="preview-lobster.png" alt="lobster"><br><br>
<strong><code>lobster</code></strong><br>
<sup>OFL · static</sup><br>
Bold script — heavier and more decorative than Pacifico.
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
</table>

---

## Flowing script & calligraphy

Flowing connected cursives and formal calligraphic scripts — elegant, personal, occasion-ready. Bold weights where available; thin-stroked faces like Tangerine and Parisienne may look delicate at small auto-sizes.

<table>
<tr>
<td align="center">
<img src="preview-dancing-script.png" alt="dancing-script"><br><br>
<strong><code>dancing-script</code></strong><br>
<sup>OFL · variable</sup><br>
Flowing connected cursive — the most popular script on Google Fonts.
</td>
<td align="center">
<img src="preview-tangerine.png" alt="tangerine"><br><br>
<strong><code>tangerine</code></strong><br>
<sup>OFL · static</sup><br>
Elegant copperplate calligraphy — refined and formal.
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
<img src="preview-clicker-script.png" alt="clicker-script"><br><br>
<strong><code>clicker-script</code></strong><br>
<sup>OFL · static</sup><br>
Thick connecting brush script — bold and legible on e-ink.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-yellowtail.png" alt="yellowtail"><br><br>
<strong><code>yellowtail</code></strong><br>
<sup>Apache 2.0 · static</sup><br>
Condensed calligraphic brush — stylish and compact.
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
<img src="preview-caveat.png" alt="caveat"><br><br>
<strong><code>caveat</code></strong><br>
<sup>OFL · variable</sup><br>
Connected ballpoint cursive — quick personal notes.
</td>
<td align="center">
<img src="preview-kalam.png" alt="kalam"><br><br>
<strong><code>kalam</code></strong><br>
<sup>OFL · static</sup><br>
Rounded everyday handwriting — Indian Type Foundry.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-architects-daughter.png" alt="architects-daughter"><br><br>
<strong><code>architects-daughter</code></strong><br>
<sup>OFL · static</sup><br>
Neat block-letter print — drafting-style hand.
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
<img src="preview-patrick-hand.png" alt="patrick-hand"><br><br>
<strong><code>patrick-hand</code></strong><br>
<sup>OFL · static</sup><br>
Open clean handwriting — very legible at small sizes.
</td>
<td align="center">
<img src="preview-shadows-into-light.png" alt="shadows-into-light"><br><br>
<strong><code>shadows-into-light</code></strong><br>
<sup>OFL · static</sup><br>
Light marker on paper — airy, softly slanted.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-gloria-hallelujah.png" alt="gloria-hallelujah"><br><br>
<strong><code>gloria-hallelujah</code></strong><br>
<sup>Apache 2.0 · static</sup><br>
Loose kid-like print — wobbly baseline, joyful.
</td>
<td align="center">
<img src="preview-amatic-sc.png" alt="amatic-sc"><br><br>
<strong><code>amatic-sc</code></strong><br>
<sup>OFL · static</sup><br>
Tall thin all-caps handwritten — fits long phrases.
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
<img src="preview-homemade-apple.png" alt="homemade-apple"><br><br>
<strong><code>homemade-apple</code></strong><br>
<sup>Apache 2.0 · static</sup><br>
Quick handwritten cursive — looped and personal.
</td>
</tr>
</table>
