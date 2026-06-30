# FarmTwin — Agri Digital Twin for Precision Irrigation

[![CI](https://github.com/arunthanga/FarmTwin/actions/workflows/ci.yml/badge.svg)](https://github.com/arunthanga/FarmTwin/actions/workflows/ci.yml)

**Pilot site:** 15-acre rain-shadow farm, Eruthempathy, Chittur, Palakkad, Kerala  
**Status:** MVP complete · Engine v0.2 · CI/TDD infra v0.4

FarmTwin applies hydraulic simulation, agronomy science, and a digital-twin calibration loop to farm irrigation — shipped as two products on one shared physics engine.

| Product | Who uses it | When |
|---------|-------------|------|
| **FarmTwin Studio** | Installation person / agronomist | Once, at farm setup |
| **FarmTwin Runtime** | Farmer / FPO operator | Always-on, daily operations |

---

## Repository Structure

```
FarmTwin/
│
├── engine/                        # Shared physics core (FarmTwin)
│   ├── FarmTwin/                # Python package — all solvers
│   │   ├── __init__.py
│   │   ├── params.py              # Live ParameterSet (A0 principle)
│   │   ├── solver.py              # GGA hydraulic solver (Todini & Pilati 1988)
│   │   ├── headloss.py            # Hazen-Williams + Darcy-Weisbach
│   │   ├── components.py          # Pumps, valves, filters, venturi
│   │   ├── emitters.py            # Drip & PC emitter models
│   │   ├── preprocess.py          # FTS JSON → solver network
│   │   ├── postprocess.py         # Results → EU/DU and optional plots
│   │   ├── fao56.py               # FAO-56 Penman-Monteith ET₀ + dual Kc
│   │   ├── quality.py             # B6 QC gate (QARTOD + Hampel) [planned]
│   │   ├── agronomy.py            # Crop catalogue, FAO-33 yield model [planned]
│   │   ├── transient.py           # MOC water-hammer solver [planned]
│   │   ├── surface.py             # Zero-inertia Saint-Venant [planned]
│   │   ├── richards.py            # Richards unsaturated flow [planned]
│   │   ├── commissioning.py       # QR-scan DevEUI → FTS registration [planned]
│   │   └── schemas/
│   │       └── fts_survey_schema.json   # JSON Schema for FTS v1.0
│   │
│   ├── tests/                     # pytest test suite
│   │   ├── conftest.py            # TDD switch, fixtures, tolerances
│   │   ├── test_solver.py         # GGA unit + regression
│   │   ├── test_fao56.py          # FAO-56 unit + regression
│   │   ├── test_schema.py         # FTS schema unit + TDD
│   │   ├── test_quality.py        # B6 QC gate unit + TDD
│   │   └── baselines/             # Golden outputs for future baseline tests
│   │
│   ├── docs/                      # Engine-specific deep-dive docs (docs 10–22)
│   ├── examples/                  # Runnable demo scripts
│   ├── requirements.txt           # Legacy mirror of pyproject dependencies
│   └── requirements-dev.txt       # Legacy mirror of pyproject dev extras
│
├── apps/                          # User-facing application layer
│   ├── studio/                    # FarmTwin Studio (React Native tablet app)
│   ├── runtime/                   # FarmTwin Runtime (farmer PWA — React)
│   ├── dashboard/                 # Cloud dashboard (React + Tailwind)
│   └── commissioning/             # Installer commissioning app (React Native)
│
├── infra/                         # Infrastructure
│   ├── edge/                      # C++17 edge decision engine (RPi4)
│   ├── cloud/                     # FastAPI backend + TimescaleDB migrations
│   └── iot/                       # ChirpStack config, MQTT, Sparkplug B
│
├── scripts/                       # Dev utilities
│   ├── ai_code_review.py          # AI code-review bot (called by CI)
│   ├── generate_baselines.py      # Regenerate regression baselines
│   └── validate_schema.py         # Validate FTS JSON docs against schema
│
├── docs/                          # Project-level documentation
│   ├── requirements.md            # ★ Single source of truth (all solvers, UX, tech)
│   ├── coding-standards.md        # Ruff / clang-tidy / ESLint standards
│   ├── survey-schema.md           # FTS input format + mobile survey UX
│   ├── adr/                       # Architecture Decision Records
│   │   ├── 0001-two-product-one-engine.md
│   │   ├── 0002-c-solver-cores.md
│   │   └── 0003-lorawan-in865.md
│   ├── examples/
│   │   └── eruthempathy_pilot.fts.json   # Pilot farm survey (valid FTS v1.0)
│   ├── business/                  # Business docs (grants, MoUs, funding)
│   └── whitepapers/               # Cached PDFs of reference white papers
│
├── mvp/                           # Browser-based MVP demo (no build step)
│   └── index.html
│
├── .github/
│   ├── workflows/ci.yml           # 7-job CI pipeline
│   ├── CODEOWNERS                 # Auto-review assignments
│   ├── ISSUE_TEMPLATE/
│   └── pull_request_template.md
│
├── CHANGELOG.md                   # Keep-a-Changelog format
├── pyproject.toml                 # Packaging, dependencies, Ruff, pytest
├── .gitignore
├── .editorconfig
└── .env.example
```

---

## Quick Start

```bash
# Clone
git clone https://github.com/arunthanga/FarmTwin.git
cd FarmTwin

# Install engine (Python 3.11+)
make install

# Run checks
make lint
make test-unit

# Run the MVP demo (open in browser)
open mvp/index.html
```

---

## TDD Mode

```bash
# Red phase — write tests first, expect failures
FARMTWIN_TDD_MODE=on  pytest tests/ -m tdd -v

# Green phase — add product code, all tests must pass
FARMTWIN_TDD_MODE=off pytest tests/ -m tdd -v

# Full test run (skip TDD stubs)
FARMTWIN_TDD_MODE=off pytest tests/ -m "unit and not tdd" --cov=FarmTwin
```

CI automatically sets `FARMTWIN_TDD_MODE=on` on `tdd/**` branches and `off` on `master`.

---

## Key Documents

| Document | Purpose |
|----------|---------|
| [`docs/requirements.md`](docs/requirements.md) | Single source of truth — all solver specs, tech choices, white-paper refs |
| [`docs/coding-standards.md`](docs/coding-standards.md) | Ruff, clang-tidy, ESLint rules; TDD workflow |
| [`docs/survey-schema.md`](docs/survey-schema.md) | FTS JSON schema; mobile survey UX design |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history and roadmap |
| [`engine/docs/`](engine/docs/) | Deep-dive solver mathematics (docs 10–22) |

---

## White-Paper References (key)

| Module | Reference |
|--------|-----------|
| GGA solver | Todini & Pilati (1988); Todini & Rossman (2013) / EPANET 2 |
| Transient (MOC) | Wylie & Streeter (1993); Urbanowicz et al. (2021) *Water* |
| Surface irrigation | Strelkoff & Katopodes (1977); Bautista et al. (2009) WinSRFR |
| Soil water (Richards) | Celia et al. (1990) *WRR*; van Genuchten (1980) *SSSAJ* |
| ET₀ / Crop water | Allen et al. (1998) FAO-56; ASCE-EWRI (2005) |
| Yield model | Doorenbos & Kassam (1979) FAO-33; Steduto et al. (2009) AquaCrop |
| Optimiser | Deb et al. (2002) NSGA-II *IEEE TEC* |
| Digital twin | Evensen (2003) EnKF *Ocean Dynamics* |
| Data quality | IOOS QARTOD; Hampel (1974) *JASA* |

Full annotated bibliography: [`engine/docs/16-annotated-bibliography.md`](engine/docs/16-annotated-bibliography.md)

---

*FarmTwin — Eruthempathy, Palakkad, Kerala*
