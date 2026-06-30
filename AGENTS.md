# AGENTS.md

## Cursor Cloud specific instructions

### What this repo is
FarmTwin is primarily a **Python irrigation/agronomy engine** (`engine/FarmTwin`) plus a
**static browser MVP** (`mvp/index.html`). The `apps/*` and `infra/*` directories are
placeholder READMEs only — there is no backend server, database, frontend build, or IoT code
to run. There are **no long-running services and no listening ports**; "running the product"
means (a) exercising the Python engine and (b) opening the static MVP page in a browser.

### Python environment
- Dependencies are installed into a virtualenv at `/workspace/.venv` (the update script creates
  it and installs `engine/requirements-dev.txt`). Run tools via `.venv/bin/python`,
  `.venv/bin/pytest`, `.venv/bin/ruff`, etc. (or activate the venv).
- System Python is 3.12; the project targets `>=3.11` and pins `numpy<2.0` / `scipy<2.0`.
- Creating the venv requires the `python3.12-venv` system package (already installed in the
  VM image, not in the update script).

### Standard commands
Use the `Makefile` targets from the repo root. Key targets:
`make lint`, `make test-unit`, `make test-regression`, `make validate-schema`. CI is
`.github/workflows/ci.yml`.

### Non-obvious gotchas
- **TDD mode**: `FARMTWIN_TDD_MODE` (`on`/`off`) flips how `tdd`-marked tests are graded. On
  `master` it is `off` and CI runs `pytest -m "unit and not tdd"`. Tests marked `tdd` are
  expected-to-fail stubs (product code not written) — do not treat their failures as a broken
  environment.
- **Partial module coverage**: some modules are reference implementations or planned surfaces,
  so unit coverage is currently baselined below the long-term target. This is the repo's current
  partial state, not a setup failure.
- **Regression tests** (`-m regression`) currently select a small deterministic baseline set.

### Demoing the static MVP
`mvp/index.html` is fully client-side (no server). It auto-runs a season comparison on load and
has interactive controls (crop/climate/strategy selects, Play/Step/Reset, "Run full-season
comparison"). To capture screenshots/video headlessly, the system `google-chrome` works with
Playwright driven via `executable_path="/usr/bin/google-chrome"` (`playwright` + `playwright
install ffmpeg` are not project deps — install ad hoc only if you need to script the browser).

### Engine quick demo
`.venv/bin/python engine/examples/demo_drip_system.py` solves a drip network and writes
`engine/examples/lateral_profile.png` (generated artifact — don't commit it).
