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

## Apt-installed

`deploy.sh` installs these automatically — no extra steps needed on the Pi.

<table>
<tr>
<td align="center">
<img src="preview-dejavu.png" alt="dejavu"><br><br>
<strong><code>dejavu</code></strong> <em>(default)</em><br>
<sup>fonts-dejavu-core</sup><br>
Clean humanist sans — high x-height, broad Unicode coverage.
</td>
<td align="center">
<img src="preview-dejavu-serif.png" alt="dejavu-serif"><br><br>
<strong><code>dejavu-serif</code></strong><br>
<sup>fonts-dejavu</sup><br>
Elegant transitional serif companion to DejaVu Sans.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-liberation-serif.png" alt="liberation-serif"><br><br>
<strong><code>liberation-serif</code></strong><br>
<sup>fonts-liberation2</sup><br>
Times-metric serif — newspaper feel, very readable at small sizes.
</td>
<td align="center">
<img src="preview-roboto-slab.png" alt="roboto-slab"><br><br>
<strong><code>roboto-slab</code></strong><br>
<sup>fonts-roboto-slab</sup><br>
Chunky slab serif — renders especially crisply on e-ink.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-cantarell.png" alt="cantarell"><br><br>
<strong><code>cantarell</code></strong><br>
<sup>fonts-cantarell</sup><br>
GNOME's humanist sans — tall x-height, friendly curves.
</td>
<td align="center">
<img src="preview-ubuntu.png" alt="ubuntu"><br><br>
<strong><code>ubuntu</code></strong><br>
<sup>fonts-ubuntu</sup><br>
Distinctive warm sans with subtle calligraphic terminals.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-jetbrains-mono.png" alt="jetbrains-mono"><br><br>
<strong><code>jetbrains-mono</code></strong><br>
<sup>fonts-jetbrains-mono</sup><br>
Modern monospaced — typewriter personality on e-ink.
</td>
<td></td>
</tr>
</table>

---

## Open-source, vendored

These ship in the `fonts/` directory and work on any machine without an apt install. All are [OFL](https://openfontlicense.org/) licensed unless noted.

<table>
<tr>
<td align="center">
<img src="preview-fredoka.png" alt="fredoka"><br><br>
<strong><code>fredoka</code></strong><br>
<sup>OFL · variable · apt: fonts-fredoka</sup><br>
Rounded display — soft, friendly geometric shapes.
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
<img src="preview-playfair.png" alt="playfair"><br><br>
<strong><code>playfair</code></strong><br>
<sup>OFL · variable</sup><br>
High-contrast display serif — dramatic stroke variation.
</td>
</tr>
<tr>
<td align="center">
<img src="preview-pacifico.png" alt="pacifico"><br><br>
<strong><code>pacifico</code></strong><br>
<sup>OFL · static</sup><br>
Casual brush-script — maximally playful.
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
<img src="preview-righteous.png" alt="righteous"><br><br>
<strong><code>righteous</code></strong><br>
<sup>OFL · static</sup><br>
Art Deco geometric sans — retro-modern personality.
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
<img src="preview-bangers.png" alt="bangers"><br><br>
<strong><code>bangers</code></strong><br>
<sup>OFL · static</sup><br>
Comic-book display — bold, condensed, pop-art energy.
</td>
<td></td>
</tr>
</table>

---

## Display / themed — vendored

Higher-character display faces for when you want the clock to *say something*. All ship in `fonts/` and work out of the box. Most are SIL OFL; the typewriter and marker faces are Apache 2.0 (Google Fonts). These are deliberately personality-forward — they read worse than DejaVu at small sizes, but each has a strong typographic flavour.

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
<img src="preview-monoton.png" alt="monoton"><br><br>
<strong><code>monoton</code></strong><br>
<sup>OFL · static</sup><br>
Multi-line striped art-deco caps — striking silhouette.
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
<img src="preview-abril-fatface.png" alt="abril-fatface"><br><br>
<strong><code>abril-fatface</code></strong><br>
<sup>OFL · static</sup><br>
Fashion-magazine ultra-bold display serif — high contrast.
</td>
</tr>
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
<img src="preview-special-elite.png" alt="special-elite"><br><br>
<strong><code>special-elite</code></strong><br>
<sup>Apache 2.0 · static</sup><br>
Distressed typewriter — uneven inking, ribbon strikes.
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
<img src="preview-creepster.png" alt="creepster"><br><br>
<strong><code>creepster</code></strong><br>
<sup>OFL · static</sup><br>
Halloween / horror display — seasonal novelty.
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
<img src="preview-lobster.png" alt="lobster"><br><br>
<strong><code>lobster</code></strong><br>
<sup>OFL · static</sup><br>
Bold script — heavier and more decorative than Pacifico.
</td>
<td></td>
</tr>
</table>

---

## Commercial — bring your own file

Drop a licensed copy of the font into `fonts/`. The daemon falls back to a macOS system font (Georgia Bold or Times New Roman Bold) for dev renders when no file is present.

| Variant | File to drop in `fonts/` | Publisher | Character |
|---------|--------------------------|-----------|-----------|
| `bookerly` | `Bookerly-Bold.ttf` | Amazon (Kindle) | Warm humanist serif designed for long reading sessions; optimised for screen rendering. |
| `minion` | `MinionPro-Bold.otf` | Adobe | Classic old-style serif inspired by Renaissance-era type; timeless and space-efficient. |
| `livory` | `Livory-Bold.otf` | iA (Information Architects) | Transitional serif with calligraphic warmth; designed for iA Writer. |
| `chaparral` | `ChaparralPro-Bold.otf` | Adobe | Humanist slab serif blending serif warmth with slab structure; very even on e-ink. |
| `arno` | `ArnoPro-Bold.otf` | Adobe | Old-style text serif in the tradition of the early Venetian printers; compact and elegant. |
| `malabar` | `Malabar-Bold.otf` | Linotype | Sturdy hybrid serif with slab tendencies; originally designed for newspaper body text. |
| `pigeonette` | `Pigeonette-Bold.otf`, `Pigeonette-Regular.otf`, or `Pigeonette.otf` | Tortilla Studio ([Future Fonts](https://www.futurefonts.xyz/tortillastudio/pigeonette)) | Idiosyncratic display serif with expressive stroke contrast. |
