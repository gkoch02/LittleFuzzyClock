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

---

## Apt-installed

`deploy.sh` installs these automatically. No extra steps needed on the Pi.

| Variant | Preview | Package | Character |
|---------|---------|---------|-----------|
| `dejavu` *(default)* | ![dejavu](preview-dejavu.png) | `fonts-dejavu-core` | Clean humanist sans — high x-height, broad Unicode coverage. |
| `dejavu-serif` | ![dejavu-serif](preview-dejavu-serif.png) | `fonts-dejavu` | Elegant transitional serif companion to DejaVu Sans. |
| `liberation-serif` | ![liberation-serif](preview-liberation-serif.png) | `fonts-liberation2` | Times-metric serif — newspaper feel, very readable at small sizes. |
| `roboto-slab` | ![roboto-slab](preview-roboto-slab.png) | `fonts-roboto-slab` | Chunky slab serif; renders especially crisply on e-ink. |
| `cantarell` | ![cantarell](preview-cantarell.png) | `fonts-cantarell` | GNOME's humanist sans; tall x-height, friendly curves. |
| `ubuntu` | ![ubuntu](preview-ubuntu.png) | `fonts-ubuntu` | Distinctive warm sans with subtle calligraphic terminals. |
| `jetbrains-mono` | ![jetbrains-mono](preview-jetbrains-mono.png) | `fonts-jetbrains-mono` | Modern monospaced; typewriter personality on e-ink. |

---

## Open-source, vendored

These ship in the `fonts/` directory and work on any machine without an apt install. License noted beside each.

| Variant | Preview | License | Source |
|---------|---------|---------|--------|
| `fredoka` | ![fredoka](preview-fredoka.png) | OFL | Variable font; `fonts/Fredoka.ttf` (falls back to `fonts-fredoka` apt package). Rounded display — soft, friendly geometric shapes. |
| `bitter` | ![bitter](preview-bitter.png) | OFL | Variable font; `fonts/Bitter-Bold.ttf` (Google Fonts). High-contrast slab serif with strong vertical stress — confident on e-ink. |
| `literata` | ![literata](preview-literata.png) | OFL | Variable font; `fonts/Literata-Bold.ttf` (Google Fonts / Google Books). Optically sized book serif; refined and even-toned. |
| `libertinus` | ![libertinus](preview-libertinus.png) | OFL | Static OTF; `fonts/LibertinusSerif-Bold.otf` (v7.051). Open successor to Linux Libertine — classical book serif with broad glyph coverage. |
| `charis-sil` | ![charis-sil](preview-charis-sil.png) | SIL OFL | Static TTF; `fonts/CharisSIL-Bold.ttf` (SIL International). Warm humanist serif with generous x-height; also installable via `fonts-sil-charis`. |
| `playfair` | ![playfair](preview-playfair.png) | OFL | Variable font; `fonts/PlayfairDisplay-Bold.ttf` (Google Fonts). High-contrast display serif — dramatic stroke variation, elegant and legible at large sizes. |
| `pacifico` | ![pacifico](preview-pacifico.png) | OFL | Static TTF; `fonts/Pacifico-Regular.ttf` (Google Fonts). Casual brush-script — maximally playful, reads beautifully when the display shows just a handful of words. |
| `lilita-one` | ![lilita-one](preview-lilita-one.png) | OFL | Static TTF; `fonts/LilitaOne-Regular.ttf` (Google Fonts). Chunky Latin display face — very bold, almost cartoonish in the best way. |
| `righteous` | ![righteous](preview-righteous.png) | OFL | Static TTF; `fonts/Righteous-Regular.ttf` (Google Fonts). Art Deco geometric sans — retro-modern personality with even strokes. |
| `comfortaa` | ![comfortaa](preview-comfortaa.png) | OFL | Variable font; `fonts/Comfortaa-Bold.ttf` (Google Fonts). Rounded geometric sans — warm and friendly; also installable as `fonts-comfortaa` (static Bold used as system fallback). |
| `nunito` | ![nunito](preview-nunito.png) | OFL | Variable font; `fonts/Nunito-Bold.ttf` (Google Fonts). Rounded sans with a generous x-height — approachable and legible at any display size. |
| `jost` | ![jost](preview-jost.png) | OFL | Variable font; `fonts/Jost-Bold.ttf` (Google Fonts). Geometric sans inspired by Futura — clean and modern with subtle character in the `a` and `t`. |
| `bangers` | ![bangers](preview-bangers.png) | OFL | Static TTF; `fonts/Bangers-Regular.ttf` (Google Fonts). Comic-book display font — bold, condensed, pop-art energy. The narrow width fits longer phrases like "twenty-five past" comfortably. |

---

## Commercial — bring your own file

These variants are registered but need a licensed copy of the font dropped into the `fonts/` directory. The daemon will use the macOS system fallback (Georgia Bold or Times New Roman Bold) for off-Pi dev renders when no file is present.

| Variant | File to drop in `fonts/` | Publisher | Character |
|---------|--------------------------|-----------|-----------|
| `bookerly` | `Bookerly-Bold.ttf` | Amazon (Kindle) | Warm humanist serif designed for long reading sessions; optimised for screen rendering. |
| `minion` | `MinionPro-Bold.otf` | Adobe | Classic old-style serif inspired by Renaissance-era type; timeless and space-efficient. |
| `livory` | `Livory-Bold.otf` | iA (Information Architects) | Transitional serif with calligraphic warmth; designed for iA Writer. |
| `chaparral` | `ChaparralPro-Bold.otf` | Adobe | Humanist slab serif blending serif warmth with slab structure; very even on e-ink. |
| `arno` | `ArnoPro-Bold.otf` | Adobe | Old-style text serif in the tradition of the early Venetian printers; compact and elegant. |
| `malabar` | `Malabar-Bold.otf` | Linotype | Sturdy hybrid serif with slab tendencies; originally designed for newspaper body text. |
| `pigeonette` | `Pigeonette-Bold.otf`, `Pigeonette-Regular.otf`, or `Pigeonette.otf` | Tortilla Studio ([Future Fonts](https://www.futurefonts.xyz/tortillastudio/pigeonette)) | Idiosyncratic display serif with expressive stroke contrast. |
