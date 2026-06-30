# FarmTwin — Design-Optimization Specification

**Status:** Draft v0.1 · **Date:** 2026-06-30
**Scope:** the FarmTwin **Studio** path from a field survey (GPS node locations +
pump specifications + crops/constraints) to the **best configuration of pipes,
valves and fittings** (the "top 2–3 designs" with a priced Bill of Materials).
**Related:** [`requirements.md`](requirements.md) §4.11, §5; [`docs/requirements.md`](docs/requirements.md);
[`docs/survey-schema.md`](docs/survey-schema.md); [`engine/docs/20-design-optimization.md`](engine/docs/20-design-optimization.md).

This document records **what is already implemented**, **what is missing**, the
**specification for the missing pieces**, and a **prioritized implementation
list**. It is the single reference for closing the survey → optimized-design loop.

---

## 0. The end-to-end pipeline

```
GPS node locations + pump nameplate/curve + crops + constraints   (the survey)
        │  (FTS .fts.json — docs/survey-schema.md)
        ▼
[A] Survey ingest & validation ............... load_fts_json / validate_fts_json   ✅ Done
        ▼
[B] Geometry from GPS ........................ pipe lengths, node static head      ❌ Missing
        ▼
[C] Pump spec → PumpCurve .................... 3-point curve from FTS attributes    ⚠ Partial
        ▼
[D] FTS → solvable Network ................... pumps/valves/emitters/zones/laterals ❌ Missing (bridge)
        ▼
[E] Demand model ............................. FAO-56 design flow per zone/emitter  ⚠ Partial
        ▼
[F] Candidate evaluation (inner loop) ........ solve → EU/DU, velocity, duty, cost  ⚠ Partial
        ▼
[G] Catalogs + cost model .................... pipe sizes, prices, energy ₹         ❌ Missing
        ▼
[H] Decision space + optimizer (NSGA-II) ..... search diameters/valves/fittings     ❌ Missing
        ▼
[I] Rank & select top 2–3 .................... least-cost / most-uniform / balanced ❌ Missing
        ▼
[J] Priced BoM + layout/EPANET export ........ generate_bom (aggregation only)      ⚠ Partial
        ▼
[K] Orchestration ............................ design_from_fts(fts) → RankedDesigns ❌ Missing
```

Legend: ✅ Done · ⚠ Partial (primitives exist, not wired/complete) · ❌ Missing.

---

## 1. Stage status matrix

| Stage | Inputs → Outputs | Lives in (today / planned) | Status |
| --- | --- | --- | --- |
| **A. Survey ingest** | `.fts.json` → validated doc + generic `{nodes,links}` | `preprocess.load_fts_json`, `validate_fts_json` (V01–V18), `convert_kobo_to_fts`, `load_epanet_inp` | ✅ Done |
| **B. GPS → geometry** | node `lat/lon/elevation` → pipe `length_m`, node static head | *none* → `geo.py` | ❌ Missing |
| **C. Pump spec → curve** | FTS pump `attributes` (shutoff/design/runout) → `PumpCurve` | `components.PumpCurve.from_design_point` (single point only) | ⚠ Partial |
| **D. FTS → Network** | FTS doc → solver `Network` with pumps+valves+emitters+fittings | `preprocess.network_from_dict` (internal schema only); `load_fts_json` returns a dict and **drops** pumps/valves/emitters | ❌ Missing |
| **E. Demand model** | zone crop+area+emitter layout → peak design flow, per-emitter `k` | `fao56.emitter_design_flow`, `crop_water_balance_step`, `gross_irrigation_depth` (primitives) | ⚠ Partial |
| **F. Candidate evaluation** | `Network` → EU/DU, velocity, pump duty/HP, feasibility, objective vector | `solver.solve`, `postprocess.uniformity`/`pump_report`/`pipe_velocity` (metrics only — no constraint/objective layer) | ⚠ Partial |
| **G. Catalog + cost** | design → ₹ capital + ₹ energy | *none* (`components.K_LIBRARY`, `MOTOR_CATALOG_HP` exist; **no diameters, no prices**) → `catalog.py` | ❌ Missing |
| **H. Optimizer** | decision space → Pareto front | *none* (`pymoo` is in `[pro]` extras, unused) → `optimize.py` | ❌ Missing |
| **I. Ranking** | Pareto front → top 2–3 labelled designs | *none* → `optimize.py` | ❌ Missing |
| **J. Priced BoM / export** | chosen design → quote + layout + `.inp` | `postprocess.generate_bom` (aggregates length/counts, **no prices**); EPANET **export** not implemented | ⚠ Partial |
| **K. Orchestration** | `fts` → ranked designs + BoMs | *none* → `studio_design.py` | ❌ Missing |

---

## 2. Gap analysis (what is missing, stage by stage)

### B. Geometry from GPS — **Missing**
The FTS carries `node.location.{lat,lon,elevation_m}` and `link.length_m` with a
`length_source` (`gps_straight`/`gps_track`/`manual`), but the **engine has no
function to derive or check geometry from coordinates**:
- No geodesic (haversine) segment length, no 3-D length including elevation drop.
- No DEM/SRTM elevation lookup (the survey app is assumed to fill `elevation_m`).
- No conversion of `water_source` (`sump_elevation_m`, static/dynamic water level)
  into a **reservoir total head** for the solver.
Consequence: a survey whose `length_m` is absent/unverified cannot be turned into
a correctly-scaled network, and source head is not derived from GPS elevation.

### C. Pump spec → curve — **Partial**
`PumpCurve.from_design_point` builds a curve from one duty point with an assumed
shutoff factor. The FTS pump node provides **three** points
(`curve_shutoff_m`, `curve_design_q_m3s`/`curve_design_h_m`, `curve_maxflow_m3s`)
plus efficiencies and HP. Missing: a constructor that fits `h0 − r_p·Q^c` to the
real shutoff/design/runout points and carries the nameplate efficiencies.

### D. FTS → solvable Network — **Missing (the critical bridge)**
`load_fts_json` returns a generic `{"nodes":[…],"links":[…]}` dict and **does not
build a solver `Network`**: it ignores the pump curve, valve K/sizing, fittings
(`link.minor_losses`), and the per-zone `emitter_layout`. `network_from_dict`
*can* build a full `Network` but only from the **internal** schema, not FTS.
There is **no `fts_to_network()`** that:
- instantiates `Reservoir` (head from source elevation + water level), `Pump`
  (with the fitted `PumpCurve`), `Valve`, `Pipe` (with `minor_loss`/`fittings`
  from `link.minor_losses`),
- expands each zone's `emitter_layout` (lateral length/spacing, emitters/plant)
  into emitter nodes with the right `k`,`x`,
- sets nodal demands from the demand model (E).
Without this, stages F–K have nothing to score.

### E. Demand model — **Partial**
`fao56.emitter_design_flow(...)` and `crop_water_balance_step(...)` exist, but
nothing maps a **zone** (crop, area, `emitters_per_plant`, `plant_count`,
irrigation window) to a **system design flow** and per-emitter discharge that the
network must deliver in the critical operating case. No simultaneous-zone logic
(`design_constraints.max_simultaneous_zones`, irrigation window).

### F. Candidate evaluation — **Partial**
`solve` + `postprocess` already yield pressures, flows, velocities, EU/DU/CV,
pump duty + motor HP. **Missing** is the scoring layer:
- a **constraint checker** (`Pmin ≤ emitter P ≤ Pmax`, `velocity ≤ Vmax`, pump
  within envelope, EU ≥ `min_eu_pct`, demand met in window, cost ≤ budget),
- an **objective vector** (capital cost, season pumping energy, 1−EU, −yield),
- season **pumping energy** = `ρ g Q H / η` integrated over FAO-56 duty.

### G. Catalogs + cost model — **Missing entirely**
No commercial **pipe-diameter catalog** (per material: DN, internal diameter,
PN class, Hazen-Williams C, ₹/m), no fitting/valve/pump/emitter **prices**, no
energy tariff plumbing (the FTS has `electricity_tariff_inr_kwh`). `K_LIBRARY`
(fitting K-values) and `MOTOR_CATALOG_HP` (sizes) exist but carry no diameters or
costs. Without a cost model there is no "least-cost / best-balanced" axis.

### H. Optimizer (`optimize.py`) — **Missing entirely**
The NSGA-II design search (decision vector → Pareto front) does not exist.
`pymoo` is declared only in the `[pro]` extra and is unused. No decision-variable
encoding, no genome↔network mapping, no repair of catalog-discrete choices.

### I. Ranking / top-2-3 — **Missing**
No selection of representative knee points (least-cost / most-uniform / balanced).

### J. Priced BoM / layout / EPANET export — **Partial**
`generate_bom` aggregates pipe length by `(material, nominal_diameter_mm)` and
counts components, but **adds no prices** and takes the *survey* FTS, not an
*optimized* design. EPANET `.inp` **export** (mentioned in survey-schema §6) is
not implemented (only import exists).

### K. Orchestration — **Missing**
No single entry point `design_from_fts(fts, catalog, costs) → [RankedDesign]`
tying B→J together; nothing exposes the Studio "one-tap optimize" capability.

---

## 3. Specification of the missing components

All SI internally (m, m³/s, m head); ₹ for cost; display conversions at the UI
boundary only. Each new module stays pure-NumPy in the core; `pymoo` is used only
when the `[pro]` extra is installed, with a deterministic fallback otherwise.

### 3.1 `engine/FarmTwin/geo.py` — geospatial geometry (Stage B)
```python
def haversine_m(lat1, lon1, lat2, lon2) -> float           # great-circle distance
def segment_length_m(a: dict, b: dict, *, use_elevation=True) -> float  # 3-D length
def polyline_length_m(points: list[dict]) -> float         # GPS-track length
def source_head_m(water_source: dict) -> float             # sump_elevation - dynamic_water_level (or static)
def fill_link_lengths(fts: dict, *, overwrite_missing_only=True) -> dict  # set length_m from node GPS when length_source is gps_*
def elevation_lookup(lat, lon) -> float | None             # optional DEM/SRTM hook (pluggable; None if offline)
```
Rules: respect `length_source` (don't overwrite `manual`/`gps_track` measured
lengths); when only endpoints exist use `gps_straight`. Geodesy via haversine
(WGS84 mean radius); 3-D length adds the elevation delta in quadrature.

### 3.2 `preprocess.fts_to_network()` — survey → solver Network (Stage D)
```python
def fts_to_network(fts: dict, *, scenario: ZoneScenario | None = None) -> Network
```
Builds a full `Network`:
- `reservoir`/source node → `Reservoir(head=geo.source_head_m(...))`;
- `pump` node → `Pump(curve=PumpCurve.from_fts(node["attributes"]))` (3.3);
- `zone_valve`/`prv`/`psv`/`fcv` → `Valve` (K and DN from `attributes`);
- `pipe`/`mainline`/`submain` link → `Pipe(length, diameter=internal_diameter_m,
  coeff=hazen_williams_c, minor_loss=Σ minor_losses.k, fittings=[…])`;
- each `zone.emitter_layout` → expand into emitter nodes/laterals with `k,x`
  derived from `flow_rate_lh` & `operating_pressure_kpa`, count from
  `plant_count × emitters_per_plant`;
- nodal demand from the demand model (3.4) for the active `scenario`.
Round-trips IDs so a design serializes back to FTS (R-PRE-9).

### 3.3 `components.PumpCurve.from_fts(attributes)` (Stage C)
Fit `h(Q)=h0 − r_p·Q^c` to (`0,shutoff`), (`design_q,design_h`),
(`maxflow,~0`); carry `pump_eff`/`motor_eff` from nameplate. Falls back to
`from_design_point` when only a single point is present.

### 3.4 Demand model `fao56.zone_design_flow(zone, et0_peak, eff)` (Stage E)
Map a zone to (a) total peak flow (m³/s) and (b) per-emitter discharge, using
`emitter_design_flow` and `gross_irrigation_depth`; produce `ZoneScenario`
objects honouring `max_simultaneous_zones` and the irrigation window so the
network is sized for the **critical** simultaneous-operation case.

### 3.5 `engine/FarmTwin/catalog.py` — catalogs + cost model (Stage G)
```python
@dataclass
class PipeSpec:   material: str; nominal_diameter_mm: float; internal_diameter_m: float
                  pressure_class: str; hw_c: float; inr_per_m: float
@dataclass
class CostModel:  pipe_inr_per_m: dict[(material,dn) -> float]
                  fitting_inr: dict[str -> float]; valve_inr: dict[dn -> float]
                  pump_inr_by_hp: dict[hp -> float]; emitter_inr_each: float
                  energy_inr_per_kwh: float
PIPE_CATALOG: list[PipeSpec]            # commercial sizes per material (PVC/HDPE/…)
def pipe_options(material) -> list[PipeSpec]
def capital_cost(design, costs) -> float
def season_energy_cost(duty_rows, hours, costs) -> float
```
Seed `PIPE_CATALOG` from IS 4985 (uPVC) / IS 4984 (HDPE) sizes; prices as
overridable defaults (FTS `electricity_tariff_inr_kwh` feeds energy).

### 3.6 Decision space (Stage H, data contract)
```python
@dataclass
class DecisionVariable:           # one tunable choice in the design
    kind: str                     # "pipe_diameter" | "valve_dn" | "pump_hp" | "fitting"
    target_id: str                # link/node id it applies to
    options: list                 # discrete catalog choices
@dataclass
class DesignCandidate:
    choices: dict[str, object]    # decision_var.name -> chosen option
    def apply(self, net) -> Network
```
Genome = index vector over each variable's `options` (catalog-discrete).

### 3.7 `engine/FarmTwin/evaluate.py` — scoring (Stage F)
```python
@dataclass
class DesignConstraints:  p_min_m; p_max_m; v_max_ms; min_eu_pct; budget_inr; pump_envelope
@dataclass
class DesignObjectives:   capital_inr; energy_inr; eu_pct; yield_rel
@dataclass
class DesignReport:       objectives; constraints_ok: bool; violations: list[str]; solve: SolveResult
def evaluate(net, scenarios, constraints, costs) -> DesignReport
```
`evaluate` = build/apply → `solve` per scenario → `uniformity`/`pipe_velocity`/
`pump_report` → constraint check → objective vector. Infeasible designs get a
penalty (objectives + large constraint-violation term) for the optimizer.

### 3.8 `engine/FarmTwin/optimize.py` — NSGA-II + fallback (Stages H–I)
```python
def optimize_design(fts, *, catalog=PIPE_CATALOG, costs=DEFAULT_COSTS,
                    objectives=("cost","energy","uniformity"),
                    pop=60, generations=40, seed=0) -> list[RankedDesign]
```
- **Primary:** `pymoo` NSGA-II over the genome (3.6), objectives from `evaluate`
  (3.7), discrete catalog repair, constraint handling; returns the Pareto front.
- **Fallback (no `pymoo`):** greedy/LP least-cost diameter selection per segment
  meeting `p_min`/`v_max` (Lansey–Mays style) so the core still produces a design.
- **Ranking:** label `lowest_cost`, `highest_uniformity`, `balanced` (knee) →
  `RankedDesign{label, candidate, report, bom}`.

### 3.9 Priced BoM + export (Stage J)
```python
def priced_bom(design_fts, costs) -> dict      # extend postprocess.generate_bom with ₹ lines + total
def export_epanet_inp(net, path) -> None        # write .inp for EPANET/IRRICAD verification
```

### 3.10 Orchestration `engine/FarmTwin/studio_design.py` (Stage K)
```python
def design_from_fts(fts, *, catalog=PIPE_CATALOG, costs=DEFAULT_COSTS) -> list[RankedDesign]:
    fts = geo.fill_link_lengths(fts)            # B
    validate_fts_json(fts)                       # A (raise on hard errors)
    scenarios = build_scenarios(fts)             # E
    return optimize_design(fts, catalog, costs)  # C,D,F,G,H,I,J
```
Single Studio entry point: survey in → top 2–3 priced, ranked designs out.

---

## 4. Implementation list (prioritized)

Phased so each step is independently testable and builds on existing code.
"Builds on" names functions that already exist.

**Phase 1 — make a survey solvable (unblocks everything)**
1. `geo.py`: `haversine_m`, `segment_length_m`, `polyline_length_m`,
   `source_head_m`, `fill_link_lengths`. *(Builds on: FTS node/link schema.)*
   *Done when:* lengths derived from the pilot FTS GPS match the document's
   `length_m` within tolerance; source head computed from sump/water levels.
2. `PumpCurve.from_fts(attributes)` (+ `from_three_points`). *(Builds on:
   `PumpCurve.from_design_point`, `head_gain`, `motor_hp`.)*
   *Done when:* curve reproduces shutoff/design/runout points within tolerance.
3. `preprocess.fts_to_network(fts, scenario)` — full Network incl. pumps, valves,
   fittings, emitter-layout expansion. *(Builds on: `network_from_dict`,
   `emitters`, `geo`, `PumpCurve.from_fts`.)*
   *Done when:* `solve(fts_to_network(pilot))` converges and `report()` prints
   sensible pressures/EU for the pilot farm.

**Phase 2 — score a design**
4. Demand model `fao56.zone_design_flow` + `build_scenarios` (simultaneous-zone /
   window logic). *(Builds on: `emitter_design_flow`, `gross_irrigation_depth`,
   `crop_water_balance_step`.)*
5. `catalog.py`: `PipeSpec`, `PIPE_CATALOG` (uPVC/HDPE sizes), `CostModel`,
   `DEFAULT_COSTS`, `capital_cost`, `season_energy_cost`. *(Builds on:
   `K_LIBRARY`, `MOTOR_CATALOG_HP`, FTS `electricity_tariff_inr_kwh`.)*
6. `evaluate.py`: `DesignConstraints`/`DesignObjectives`/`DesignReport` +
   `evaluate(net, scenarios, constraints, costs)`. *(Builds on: `solve`,
   `uniformity`, `pipe_velocity`, `pump_report`, `select_motor_hp`.)*
   *Done when:* the pilot design returns an objective vector and a correct
   feasible/infeasible verdict against `design_constraints`.

**Phase 3 — optimize & deliver**
7. Decision space (`DecisionVariable`, `DesignCandidate.apply`) +
   greedy/LP **fallback** least-cost diameter selection. *(Builds on: `catalog`,
   `evaluate`.)* *Done when:* fallback returns a feasible least-cost design with
   no `pymoo` installed.
8. `optimize.py`: NSGA-II via `pymoo` (genome, objectives, discrete repair,
   constraints) → Pareto front. *(Builds on: `evaluate`, `[pro]` `pymoo`.)*
9. Ranking → `RankedDesign` (lowest-cost / highest-uniformity / balanced knee).
10. `priced_bom` + `export_epanet_inp`. *(Builds on: `generate_bom`.)*
11. `studio_design.design_from_fts(fts)` orchestration + public API exports.

**Phase 4 — polish / interoperability**
12. EPANET `.inp` export verification vs WNTR; round-trip test (FTS→`.inp`→FTS).
13. Observability objective hook (sensor/flow-meter placement) feeding the
    optimizer so the chosen design is twin-ready (links to `assimilation.py`).
14. Wire selected design's parameters as priors into the digital twin
    (`HydraulicTwin`) for the Studio→Runtime handoff.

### Test/validation plan (per phase)
- **P1:** unit tests for haversine/length/source-head vs hand calc; `from_fts`
  curve points; `fts_to_network(pilot)` solves and round-trips IDs.
- **P2:** demand flow vs FAO-56 worked example; cost model arithmetic; constraint
  checker flags an over-velocity / under-pressure design.
- **P3:** fallback returns a feasible design; NSGA-II Pareto front dominates the
  naive uniform-diameter design on cost at equal EU; ranking returns 3 labelled
  designs; priced BoM totals match catalog × quantities; `.inp` re-imports equal.
- **Regression:** a fixed seed + pilot FTS produces a stable top-3 (golden file).

---

## 5. Out of scope (here) / future
- FreeCAD layout drawing and the PWA "one-tap optimize" UI (front-end).
- Surrogate models (Kriging/RBF/ANN) to accelerate the inner loop (R-OPT-1).
- Fertigation/nutrient optimization and multi-season scheduling.
- Full agronomy **yield** objective beyond the FAO-33 relative-yield proxy
  already in `agronomy.py` (couple it as the `yield_rel` objective in `evaluate`).

---

*This spec is descriptive of the current repository state as of 2026-06-30 and
prescriptive for the missing modules; update it as each phase lands.*
