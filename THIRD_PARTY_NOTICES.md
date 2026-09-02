# Third-party notices

The MIT license in [`LICENSE`](LICENSE) covers everything in this repository
except the third-party material vendored alongside it. Those components keep
their own licenses, listed below.

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

Those labels are taken from each vendored file's own name table where it records
one, since that copy is what this repository redistributes. Some files — mostly
variable-font builds — carry no license string, and are labelled from the
upstream project instead.

Two files are worth calling out because they do **not** follow that pattern:

| File | License |
|------|---------|
| `fonts/DejaVuSans-Bold.ttf`, `fonts/DejaVuSerif-Bold.ttf` | Bitstream Vera Fonts License (© 2003 Bitstream, Inc.; DejaVu changes are public domain) — not OFL. |
| `fonts/Ubuntu-Bold.ttf` | Ubuntu Font Licence 1.0 (© Canonical Ltd.) — not OFL. |

A third file, `fonts/TFoust.ttf`, was removed along with its `tfoust` variant:
its metadata read "© 2025 myfont — All rights reserved" (source: `myfont.bid`)
and carried no grant permitting redistribution. Don't reintroduce it.

### Known gap

Several of these licenses require their text to travel with the binaries they
cover — OFL 1.1 says so directly, and Apache 2.0 §4(a) requires every recipient
of a redistributed work to get a copy of the license. This repository ships none
of them next to `fonts/`. Recording the license per variant in `docs/fonts.md`
documents the intent but does not satisfy those conditions.

Bundling the four texts the vendored set actually needs — OFL 1.1, Apache
License 2.0, the Bitstream Vera Fonts License, and Ubuntu Font Licence 1.0 — is
outstanding work.
