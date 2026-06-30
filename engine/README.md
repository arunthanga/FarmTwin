# FarmTwin Engine — open irrigation hydraulic + agronomy engine

An India-built, open alternative to IRRICAD / IrriPro / WCADI (Rivulis) /
HydroCalc 3.0 (Netafim) for pressurized irrigation network design, plus a track
toward WinSRFR-style surface irrigation. Built to sit on **FreeCAD**
(pre-processing/CAD) and **OpenFOAM** (component CFD), with our own hydraulic
solver at the core and a **FAO-56** agronomy layer for digital-twin operation.

See [`docs/10-numerical-methods-and-architecture.md`](docs/10-numerical-methods-and-architecture.md)
for the method choices and [`docs/11-freecad-openfoam-twin-iitpkd-roadmap.md`](docs/11-freecad-openfoam-twin-iitpkd-roadmap.md)
for the build/collaboration roadmap.

## Design documents (the full plan)

The venture is two products on one shared, self-calibrating engine — see
[`docs/19-two-product-architecture.md`](docs/19-two-product-architecture.md).

| Doc | Topic |
| --- | --- |
| [10-numerical-methods-and-architecture.md](docs/10-numerical-methods-and-architecture.md) | Method choices + architecture (entry point) |
| [11-freecad-openfoam-twin-iitpkd-roadmap.md](docs/11-freecad-openfoam-twin-iitpkd-roadmap.md) | FreeCAD/OpenFOAM/twin + IIT-PKD roadmap |
| [12-solver-mathematics.md](docs/12-solver-mathematics.md) | A0 live-parametrization + GGA/MOC/Saint-Venant/Richards/ET/CFD math |
| [13-sensors-and-instrumentation.md](docs/13-sensors-and-instrumentation.md) | Sensors, AWS, placement, **B6 data-quality guards** |
| [14-digital-twin-data-assimilation.md](docs/14-digital-twin-data-assimilation.md) | EKF/EnKF, parameter estimation, governed write-back |
| [15-iitpkd-collaboration-brief.md](docs/15-iitpkd-collaboration-brief.md) | IIT Palakkad / KAU expertise + engagement plan |
| [16-annotated-bibliography.md](docs/16-annotated-bibliography.md) | ~60 annotated references, grouped by topic |
| [17-weather-data-integration.md](docs/17-weather-data-integration.md) | Public weather feeds + source precedence |
| [18-iot-control-architecture.md](docs/18-iot-control-architecture.md) | Edge-first IoT, LoRa, fertigation, solar autonomy |
| [19-two-product-architecture.md](docs/19-two-product-architecture.md) | Design Studio + Runtime on a shared core |
| [20-design-optimization.md](docs/20-design-optimization.md) | Product 1: survey -> NSGA-II -> top setups |
| [21-agronomy-layer.md](docs/21-agronomy-layer.md) | Crops, water/fertigation, yield, yield recording |
| [22-implementation-whitepapers.md](docs/22-implementation-whitepapers.md) | Key papers per module: summaries + links |

## What works today (MVP)

- **Steady network solver** via the Global Gradient Algorithm (Todini-Pilati),
  the EPANET core method — `krishiflow/solver.py`.
- **Head loss**: Hazen-Williams and Darcy-Weisbach (Swamee-Jain `f`) —
  `headloss.py`.
- **Component library** — `components.py`:
  - Pumps/motors with curve fitting and **1-50 HP motor sizing**.
  - Ball/gate/check valves, filters, tees, elbows via a minor-loss **K library**.
  - **Venturi** fertigation injector (loss element + injection metadata).
- **Emitters** — `emitters.py`: non-PC power-law (solved exactly via virtual
  links) and pressure-compensating.
- **Pre-processor** — `preprocess.py`: JSON network I/O + drip-lateral generator.
- **Post-processor** — `postprocess.py`: pressures, flows, velocities, emitter
  discharges, **EU / DU(low-quarter) / CV**, pump duty + HP, optional plots.
- **FAO-56 agronomy** — `fao56.py`: Penman-Monteith ET0, dual crop coefficient,
  root-zone water balance, net/gross irrigation requirement, emitter design flow.

## Layout

```
engine/
  krishiflow/        core package (solver, components, emitters, fao56, pre/post)
  examples/          demo_drip_system.py  (pump+filter+valve+venturi+lateral)
  tests/             pytest suite for solver, FAO-56, FTS schema, and QC stubs
  docs/              design docs 10-22 (architecture, math, sensors, twin, IoT,
                     optimization, agronomy, whitepapers) — see table above
  requirements.txt   legacy mirror; pyproject.toml is the dependency source
```

## Install & run

```bash
cd <repo-root>
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

make test-unit
python engine/examples/demo_drip_system.py # full system report + lateral_profile.png
```

`test_two_reservoirs` checks the solver against the exact analytic answer
H_J = 90 m and is included in both unit and regression selections.

## Design principle

Every component is a **link** exposing `headloss(Q)` and `gradient(Q)` (or a
node term, for emitters). The single GGA core then handles pipes, pumps, valves,
venturis and emitters uniformly — so adding hardware means adding small closure
functions, not new solvers. 3-D CFD (OpenFOAM) is used only *offline* to generate
loss/emitter curves that feed this 1-D model.

## Roadmap (next)

MOC water-hammer transients, zero-inertia surface-irrigation solver (WinSRFR
equivalent), EPANET `.inp` import/export, PRV/PSV/FCV control valves, Richards
soil model, FreeCAD workbench, and live digital-twin assimilation. See docs 11,
12 and 19; the per-module papers to read first are in
[doc 22](docs/22-implementation-whitepapers.md).
