## What & why

<!-- One or two sentences: what changes, and what problem it solves. Link the
issue if there is one (e.g. "Closes #50"). -->

## How it was verified

<!-- Delete the lines that don't apply. -->

- `ruff check .` and `ruff format --check .` pass
- `python3 -m unittest discover` passes
- Rendering change: checked `python3 fuzzyclock_preview.py --dry-run --output /tmp/out.png`
- Hardware path (EPD, GPIO, systemd, `deploy.sh`): tested on the Pi — <!-- say how -->
- Hardware path touched but **not** tested on hardware — <!-- say why, and what could break -->

<!-- CI has no panel, no GPIO, and no button, so anything below the SPI
boundary is only ever verified by hand. Say which it was. -->

## Checklist

- [ ] `README.md` updated if user-facing behaviour changed
- [ ] `CLAUDE.md` touched only to add or fix a one-line rule for a non-obvious
      invariant or footgun. The explanation lives in the code, once — not in
      CLAUDE.md, the test docstring, and the code comment all at the same time
- [ ] Removed what this change made obsolete: dead code, stale comments, tests
      that no longer test anything
- [ ] New font variant? All four touches done: `FONT_VARIANTS`,
      `FONT_FRAME_CATEGORY`, the comment block in `fuzzyclock_config.yaml`, and
      a `docs/fonts.md` row (+ `docs/previews/<name>.png` if the font is vendored)
- [ ] New behaviour has a test that fails without the change
- [ ] No changes to CI job *names* — `lint`, `test (3.11)`, and `test (3.12)` are
      required contexts in `.github/rulesets/main.json` and renaming one blocks
      every merge

## Notes for the reviewer

<!-- Anything worth flagging: a tradeoff you weren't sure about, a follow-up you
deliberately left out, a risky spot in the diff. Delete if there's nothing. -->
