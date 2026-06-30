# FarmTwin — Changelog

All notable changes to the FarmTwin project are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).  
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).  
Date format: YYYY-MM-DD.

---

## [Unreleased]

Changes merged to `master` but not yet assigned a release tag.

### To be released in v0.4.0 (this session — 2026-06-29)

#### Added — CI / Code Review / TDD / Schema

- `.github/workflows/ci.yml` — 7-job GitHub Actions CI pipeline:
  - Job 1 `lint-python`: Ruff check + format on every push and PR
  - Job 2 `ai-code-review`: AI bot (Claude Sonnet 4.6) auto-fixes safe Ruff issues via `--fix`, then calls Anthropic API for remaining issues, posts inline PR review comments with explanation + fix or `DEVELOPER ACTION REQUIRED` label
  - Job 3 `test-tdd`: runs `@pytest.mark.tdd` tests; TDD mode branch-aware (FAIL = correct in `tdd/**` branches; PASS required on `master`)
  - Job 4 `test-unit`: runs `@pytest.mark.unit` tests with ≥ 80% coverage gate (branch + statement)
  - Job 5 `test-regression`: runs `@pytest.mark.regression` tests against stored baselines
  - Job 6 `validate-schema`: validates all example FTS JSON docs against `fts_survey_schema.json`
  - Job 7 `summary`: prints consolidated status table
- `scripts/ai_code_review.py` — standalone AI code-review bot script: parses Ruff output per changed file, calls Anthropic API with FarmTwin coding-standards context, posts inline GitHub PR review comments, posts summary comment; exits 0 (non-blocking) so CI result is controlled by Ruff check job
- `engine/tests/conftest.py` — pytest configuration:
  - `FARMTWIN_TDD_MODE` environment-variable switch (on = TDD red phase, off = full pass required)
  - `pytest_runtest_makereport` hook: tdd-marked failing tests → `xfail` in TDD mode (correct); passing → `xpass` (signal to move test to `@pytest.mark.unit`)
  - `Tolerances` class: named numeric tolerance constants for each solver (GGA, FAO-56, Richards, MOC), each justified by its white-paper precision statement
  - Fixtures: `two_reservoir_network` (analytic H_J=90 m), `single_lateral_network`, `fao56_palakkad_inputs`, `van_genuchten_palakkad_laterite`, `default_params`, seeded `rng`
- `engine/tests/test_solver.py` — GGA solver test suite:
  - Unit: Hazen-Williams zero flow, known value (63mm PVC HDPE), direction symmetry, length scaling, C-factor parametrize sweep; invalid input raises; Darcy-Weisbach turbulent known value, laminar regime
  - Unit: GGA two-reservoir analytic validation (H_J=90 m), mass conservation, convergence count
  - TDD: PRV downstream head setpoint, EPANET .inp import, extended-period tank EPS, Elhay-Simpson zero-flow regularization
  - Regression: Eruthempathy pilot 2-zone coconut drip network (system flow, EU, pump duty vs stored baseline)
- `engine/tests/test_fao56.py` — FAO-56 test suite:
  - Unit: ET₀ Palakkad June range validation, FAO-56 Example 2.3 cross-check (Etzion, Israel; ±5%), wind/humidity monotonicity, finite+positive guard, T_max < T_min raises
  - Unit: dual crop coefficient Ke=0 case, Ke bounded by (Kcmax−Kcb)·few, ETc always positive
  - Unit: Ks=1 below RAW, Ks=0 at wilting point, monotonic decrease, never > 1
  - Unit: water balance no-change, irrigation reduces Dr, deep percolation when over field capacity, Dr clamped to [0, TAW]
  - TDD: GDD-based crop stage advancement, salinity stress (Maas-Hoffman), AquaCrop WP* biomass, irrigation trigger at RAW, multi-zone ETc aggregation
  - Regression: 30-day June cumulative ET₀ Palakkad (±5% vs NASA POWER baseline), water balance 30-day closure (< 0.1 mm residual)
- `engine/tests/test_schema.py` — FTS survey schema test suite:
  - Unit: valid example passes all V01–V18, schema version V01, UUID V02, missing fields reported multiple, farm area V03, known/unknown soil types, phone E.164 V18
  - Unit: elevation V04, no water source V05, dangling link V06, disconnected node V07, pipe diameter bounds V08 parametrize (5mm–500mm valid; outside → fail)
  - Unit: known/unknown crop types V16, emitter flow V10, no zones V12
  - Unit: round-trip load → node/link IDs preserved, pipe lengths exact
  - TDD: EPANET .inp import round-trip, KoboToolbox webhook ingest, QR DevEUI scan → sensor registration, BoM generator covers all pipe materials
- `engine/tests/test_quality.py` — B6 QC gate test suite:
  - Unit: QCFlag values match QARTOD (PASS=1, SUSPECT=3, FAIL=4), ordering
  - Unit: B1 gross range — 6-case parametrize, soil moisture bounds, pressure transducer bounds
  - Unit: B3 spike — no spike pass, large spike fail, moderate spike at least suspect
  - Unit: B4 rate-of-change — slow change pass, instantaneous jump fail
  - Unit: B5 flatline — varying pass, stuck fail, short window pass
  - Unit: B6 Hampel — clean series all pass, single outlier flagged at correct index, length preserved
  - Unit: full B6 gate — all checks pass for clean reading, gross-range failure propagates to overall, FAIL sets usable=False
  - TDD: B2 climatological range via date-specific percentile table, battery voltage alert, adaptive spike threshold auto-calibrated from history
- `docs/coding-standards.md` — FarmTwin coding standards document (v1.0.0):
  - Ruff rule set with fixable vs manual split
  - C standards: C11, clang-tidy, clang-format, naming, error codes, no-global-state, mandatory CFLAGS
  - C++17 edge engine standards: `[[nodiscard]]`, RAII, `std::optional`, Result type
  - JavaScript/TypeScript/React Native: ESLint airbnb + typescript-eslint, i18n mandate, accessibility requirements
  - TDD switch rules, test naming conventions, numeric/scientific standards N1–N6, security standards S1–S4
  - Complete tool config blocks: `pyproject.toml` (Ruff + pytest), `.clang-format`, `.clang-tidy`, `.eslintrc.js`
- `docs/survey-schema.md` — FTS survey schema specification (v1.0.0):
  - §1: Mobile phone as primary survey instrument — capability matrix (GPS, photo, QR, audio, GPS-track, offline)
  - §2: Four entry modes (native app, KoboToolbox/ODK, CSV bulk, direct JSON API)
  - §3: Master FTS JSON schema with all top-level fields
  - §4: Nine sub-schemas (farm, water_source, nodes, links, zones, sensors, weather, design_constraints, attachments) with all allowed-value enumerations
  - §5: 8-screen mobile survey UX wizard flow; GPS auto-fill rules for elevation and pipe length
  - §6: Import/export rules — Studio→Runtime as-built JSON hand-off, EPANET .inp import/export
  - §7: Offline-first sync protocol (SQLite, conflict resolution, background attachment upload)
  - §8: KoboToolbox/ODK integration (XLSForm template, webhook endpoint, limitations)
  - §9: 18 validation rules V01–V18 with error messages
  - §10: Complete worked example — Eruthempathy 15-acre pilot farm, 2-zone coconut, 5HP pump
- `pyproject.toml` — consolidated project configuration:
  - Ruff: full rule set (E,W,F,I,N,UP,B,C4,C90,PL,PT,SIM,D,ANN,S,BLE,RUF); per-file overrides for tests and scripts
  - pytest: markers, strict mode, filterwarnings as errors
  - coverage: branch coverage, 80% gate, exclude abstract stubs

### To be released in v0.3.0

#### Added (planned — requirements.md v1.0.0 scope)

- `requirements.md` — single source of truth requirements document covering all solvers, components, UX personas, and technology choices (this session)
- `changelog.md` — this file; established Keep-a-Changelog format
- Specification for C-language GGA solver core (`libkrishiflow.so`) as a CPython extension for edge and high-performance Studio use
- Specification for C-language MOC transient solver (`transient.py` backend)
- Specification for C-language zero-inertia Saint-Venant surface irrigation solver (`surface.py` backend)
- Specification for C-language Richards equation soil-water solver (`richards.py` backend) with Modified Picard (Celia 1990) and van Genuchten (1980) retention/conductivity
- Specification for C++ 17 edge decision engine (`edge/` runtime) linking C solver core
- Specification for C firmware fertigation PID controller on STM32/ESP32 nodes
- Specification for React Native farm survey tablet app (GPS node placement, offline Mapbox tiles)
- Specification for NSGA-II design optimizer via pymoo with parallel candidate evaluation
- Specification for EKF hydraulic twin and EnKF soil twin (Evensen 2003) on cloud
- Specification for B6 QC gate (IOOS QARTOD + Hampel filter)
- Specification for LoRaWAN IN865 IoT stack (ChirpStack + Mosquitto + Sparkplug B onboarding)
- Specification for farmer PWA with Malayalam/English toggle and WhatsApp Business API alerts
- Specification for installation person commissioning app (QR-scan DevEUI, pre-flight pressure map)
- Specification for TimescaleDB time-series storage and FastAPI cloud backend
- Full white-paper reference index covering all solver and module choices (17 sections)

---

## [0.2.0] — 2026-06-29

Initial engine design documents and MVP committed to `master`.

### Added

- `engine/README.md` — engine overview: GGA solver, FAO-56 agronomy, design-doc index (docs 10–22), install/run instructions
- `engine/krishiflow/solver.py` — steady-state GGA (Todini & Pilati 1988 / EPANET 2 method); Newton-Raphson with sparse SPD solve; validation target: two-reservoir analytic case H_J = 90 m
- `engine/krishiflow/headloss.py` — Hazen-Williams (n=1.852) and Darcy-Weisbach (Swamee-Jain friction factor) head-loss laws
- `engine/krishiflow/components.py` — pumps/motors (curve fitting, 1–50 HP sizing); ball/gate/check valves; filters; tees/elbows via minor-loss K library; venturi fertigation injector
- `engine/krishiflow/emitters.py` — non-PC power-law emitters (virtual-link method) and pressure-compensating emitters
- `engine/krishiflow/preprocess.py` — JSON network I/O; drip-lateral auto-generator
- `engine/krishiflow/postprocess.py` — pressures, flows, velocities, emitter discharges, EU/DU(lq)/CV uniformity, pump duty + HP; optional Matplotlib plots
- `engine/krishiflow/fao56.py` — FAO Penman-Monteith ET₀; dual crop coefficient (Kcb + Ke); root-zone water balance; net/gross irrigation requirement; emitter design flow
- `engine/examples/demo_drip_system.py` — full demo: pump + filter + valve + venturi + lateral; generates `lateral_profile.png`
- `engine/tests/test_solver.py` — GGA validation against hand calculations (two-reservoir analytic check)
- `engine/tests/test_fao56.py` — FAO-56 validation
- `engine/docs/10-numerical-methods-and-architecture.md` — method choices and architecture rationale
- `engine/docs/11-freecad-openfoam-twin-iitpkd-roadmap.md` — FreeCAD/OpenFOAM integration and IIT Palakkad collaboration roadmap
- `engine/docs/12-solver-mathematics.md` — deep-dive governing equations and numerical schemes per solver (GGA, MOC, surface, Richards, FAO-56, OpenFOAM, NSGA-II)
- `engine/docs/13-sensors-and-instrumentation.md` — sensor types, AWS, placement, B6 data-quality guards
- `engine/docs/14-digital-twin-data-assimilation.md` — EKF/EnKF theory, parameter estimation, governed write-back
- `engine/docs/15-iitpkd-collaboration-brief.md` — IIT Palakkad and KAU expertise and engagement plan
- `engine/docs/16-annotated-bibliography.md` — ~60 annotated references grouped by topic
- `engine/docs/17-weather-data-integration.md` — public weather feeds, source precedence, fallback cascade
- `engine/docs/18-iot-control-architecture.md` — edge-first IoT: 3-tier architecture, LoRa/LoRaWAN IN865, fertigation PID, solar autonomy, Sparkplug B onboarding
- `engine/docs/19-two-product-architecture.md` — two-product split (Studio + Runtime) on shared engine; downstream/upstream data flow; module ownership map
- `engine/docs/20-design-optimization.md` — NSGA-II multi-objective optimizer specification; Pareto front; top-3 output
- `engine/docs/21-agronomy-layer.md` — crop catalogue, dual Kc, FAO-33 yield model, fertigation nutrient plan
- `engine/docs/22-implementation-whitepapers.md` — key white papers per module with summaries, what to implement, and links; reading-order guide
- `mvp/index.html` — working farm digital-twin precision-irrigation simulator (browser, no build step)

### Added (business/application docs)

- `docs/01-venture-decision.md` — lead-venture decision and rationale
- `docs/02-problem-statement.md` — problem, target user, CAE-to-agri skill transfer map
- `docs/03-dpiit-ksum-registration.md` — DPIIT and KSUM Unique ID registration guide
- `docs/04-ksum-idea-grant-application.md` — KSUM Idea Grant application draft
- `docs/05-agrinext-problem-statement.md` — AgriNext/KERA problem-statement submission
- `docs/06-incorporation-guide.md` — Pvt Ltd vs LLP decision and incorporation steps
- `docs/07-funding-roadmap.md` — Grant → Seed → Scale-up funding sequence
- `docs/08-fpo-pilot-mou-template.md` — FPO pilot MoU template
- `docs/09-agri-fintech-phase2.md` — Phase-2 agri-fintech layer specification
- `docs/10-branding-and-trademark.md` — FarmTwin brand decision and trademark due diligence

---

## [0.1.0] — 2026-06-28

Repository initialized.

### Added

- `README.md` — project overview: FarmTwin agri digital-twin platform; pilot site Eruthempathy, Palakkad; KSUM application context; repository structure table; status legend

---

## Roadmap (post-v0.3.0)

Items not yet in scope for v0.3.0 but formally planned in the design documents.

### v0.4.0 — Solver C Cores (planned)

- Implement and unit-test `libkrishiflow.so` C GGA solver; cross-validate against EPANET 2 on published `.inp` test networks
- Implement MOC transient C library; validate against Wylie & Streeter example problems and published surge-test data
- Python cffi bindings for both C libs; replace NumPy GGA in solver.py with C backend call
- Implement zero-flow Elhay-Simpson regularization in C core

### v0.5.0 — Surface and Soil Solvers (planned)

- Implement zero-inertia Saint-Venant surface irrigation C library; validate against WinSRFR published test cases (Bautista 2009 benchmark)
- Implement Richards C library with Celia (1990) Modified Picard; validate against HYDRUS-1D published test problems
- Integrate soil-moisture output into FAO-56 root-zone balance (replace bucket model with Richards profile in high-fidelity mode)

### v0.6.0 — NSGA-II Optimizer + BoM Export (planned)

- Implement NSGA-II via pymoo; connect to C GGA solver for candidate evaluation; parallel multiprocessing pool
- Implement BoM generation and PDF export (ReportLab)
- Implement top-3 Pareto design comparison report

### v0.7.0 — IoT Control Firmware (planned)

- C++ 17 edge decision engine (`edge/` runtime): FAO-56 + GGA decision loop; SQLite logging; offline-capable with cached weather
- C fertigation PID firmware for STM32 or ESP32 nodes
- ChirpStack LoRaWAN network server setup; MQTT broker (Mosquitto); Sparkplug B BIRTH/DEATH onboarding
- Valve RTU node firmware (LoRa + latching solenoid H-bridge)

### v0.8.0 — Digital Twin & Data Assimilation (planned)

- EKF hydraulic twin (cloud-side, Python + NumPy): augmented state [Q, H, emitter_k, pipe_C, pump_coeffs]
- EnKF soil twin (N=50 ensemble, van Genuchten parameter estimation)
- B6 QC gate (ioos_qc + Hampel filter); QARTOD-aligned flags
- Parameter promotion governance: confidence check + log entry before write-back to shared core
- TimescaleDB time-series storage; REST API for twin-state query

### v0.9.0 — Farmer PWA & Installer App (planned)

- React + Tailwind farmer PWA: Malayalam/English toggle; home-screen farm status; soil moisture bars; WhatsApp Business API alerts
- React Native installer/commissioning app: QR-scan DevEUI registration; pre-flight pressure map; BoM share via WhatsApp
- FastAPI cloud backend: JWT auth; role-based access (farmer/installer/agronomist/admin); WebSocket live telemetry

### v1.0.0 — Production Release (planned)

- Pilot deployment on 15-acre Eruthempathy farm (Palakkad)
- End-to-end validation: Studio design → installation → Runtime operation → twin calibration → yield recording
- EPANET `.inp` import/export for interoperability
- FreeCAD workbench integration for pipe-route CAD overlay
- IIT Palakkad collaboration: soil-parameter measurement and Richards model validation for Palakkad laterite soils

---

*End of CHANGELOG.md*
