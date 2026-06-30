# Changelog

All notable changes to **FarmTwin** are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the project aims to follow
[Semantic Versioning](https://semver.org/) once the engine reaches `1.0.0`.

The authoritative spec for scope, technology choices, and references is
[`requirements.md`](requirements.md) (the single source of truth). Engine version is tracked
in `engine/krishiflow/__init__.py` (`__version__`).

## [Unreleased]

### Added
- **`requirements.md`** — single source of truth: personas (farmer + installation
  technician first), the two-product context, a per-solver/component **technology decision**
  (Python reference + C/C++ hot loops, OpenFOAM for offline CFD, PWA + FreeCAD for UX),
  white-paper references for **every** solver plus the **latest improvements** around each
  original paper, pre/post-processing UX requirements, non-functional requirements, and an
  implementation status matrix.
- **`changelog.md`** — this file.

### Notes
- Verified on Python 3.12: `engine/tests/test_solver.py` and `engine/tests/test_fao56.py`
  pass, and `engine/examples/demo_drip_system.py` runs end-to-end (matplotlib optional).

## [0.1.0] — 2026-06-28

First tagged engine MVP and the KSUM/AgriNext execution package.

### Added — Engine (`engine/krishiflow`)
- **Steady network solver** via the Global Gradient Algorithm (Todini–Pilati), the EPANET
  core method — `solver.py`.
- **Head loss**: Hazen–Williams and Darcy–Weisbach (Swamee–Jain `f`) — `headloss.py`.
- **Component library** — `components.py`: pump/motor curve fit with **1–50 HP motor sizing**;
  ball/gate/check valves, filters, tees, elbows via a minor-loss **K-library**; **venturi**
  fertigation injector.
- **Emitters** — `emitters.py`: non-PC power-law (virtual links) and pressure-compensating,
  with EU / DU(low-quarter) / CV uniformity.
- **Pre-processor** — `preprocess.py`: JSON network I/O + drip-lateral generator.
- **Post-processor** — `postprocess.py`: pressures, flows, velocities, emitter discharges,
  uniformity, pump duty + HP, optional plots.
- **FAO-56 agronomy** — `fao56.py`: Penman–Monteith ET0, dual crop coefficient, root-zone
  water balance, net/gross irrigation requirement, emitter design flow.
- **Validation tests** — `tests/test_solver.py`, `tests/test_fao56.py` (analytic checks);
  worked example — `examples/demo_drip_system.py`.

### Added — Design & strategy documentation
- Engine design docs 10–22 (`engine/docs/`): numerical methods & architecture, solver
  mathematics (GGA/MOC/zero-inertia/Richards/FAO-56/CFD), sensors & QA-QC, digital twin &
  data assimilation, IIT-PKD/KAU brief, annotated bibliography, weather integration, IoT
  control, two-product architecture, design optimization, agronomy layer, and the
  implementation white-paper index.
- Venture/application docs 01–10 (`docs/`): venture decision, problem statement,
  DPIIT/KSUM registration, Idea Grant draft, AgriNext submission, incorporation, funding
  roadmap, FPO pilot MoU, agri-fintech phase-2, branding & trademark.
- **MVP** browser digital-twin irrigation simulator (`mvp/index.html`) and on-farm pilot
  protocol (`mvp/PILOT.md`).

### Changed
- Rebranded the venture and engine to **FarmTwin** and documented trademark due diligence.

[Unreleased]: https://github.com/arunthanga/FarmTwin/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/arunthanga/FarmTwin/releases/tag/v0.1.0
