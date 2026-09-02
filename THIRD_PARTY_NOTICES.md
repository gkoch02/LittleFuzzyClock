# Third-party notices

The MIT license in [`LICENSE`](LICENSE) covers this project's own code —
`fuzzyclock/`, `fuzzyclock_core.py`, `fuzzyclock_daemon.py`,
`fuzzyclock_preview.py`, `tests/`, `deploy.sh`, `systemd/`, and `docs/`.

It does **not** cover the third-party material vendored alongside it. Those
components keep their own licenses, listed below.

## `waveshare_epd/`

A verbatim copy of the Waveshare e-Paper Python driver
(`epd2in13_V4.py`, `epdconfig.py`) from
<https://github.com/waveshare/e-Paper>. MIT licensed; the copyright and
permission notice is preserved in each file's header. Don't edit these files
locally — resync from upstream instead.

## `fonts/`

Every vendored typeface is redistributed under its own license, not under this
repository's MIT grant. [`docs/fonts.md`](docs/fonts.md) records the license
alongside each variant's preview; the great majority are SIL Open Font License
1.1, with a handful under Apache License 2.0.

Three files are worth calling out because they do **not** follow that pattern:

| File | License |
|------|---------|
| `fonts/DejaVuSans-Bold.ttf`, `fonts/DejaVuSerif-Bold.ttf` | Bitstream Vera Fonts License (© 2003 Bitstream, Inc.; DejaVu changes are public domain) — not OFL. |
| `fonts/Ubuntu-Bold.ttf` | Ubuntu Font Licence 1.0 (© Canonical Ltd.) — not OFL. |
| `fonts/TFoust.ttf` | **No open-source license.** The font's own metadata reads "© 2025 myfont — All rights reserved" (source: `myfont.bid`). There is no grant permitting redistribution, so this file should be removed from the repository and the `tfoust` variant retired or repointed at a licensed face. |

### Known gap

The OFL 1.1 requires its license text to travel with the font files it covers,
and this repository does not currently ship a copy of the OFL (or of the
Bitstream Vera / Ubuntu Font Licence texts) next to `fonts/`. Recording the
license per variant in `docs/fonts.md` documents the intent but does not
satisfy that condition. Bundling the license texts — and dropping
`fonts/TFoust.ttf` — is outstanding work.
