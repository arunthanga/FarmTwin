# 19 — Two-Product Architecture (Design Studio + Runtime) on One Shared Engine

Goal: define how the venture ships as **two distinct products** built on **one shared
physics/agronomy core** (`engine/krishiflow`), why the engine is kept shared rather
than split, and the data that flows between the products.

> **Headline.** Product 1 (**KrishiFlow Design Studio**) is used once, *before*
> installation, to survey a farm, simulate many setups, optimize, and recommend the
> best 2-3 designs. Product 2 (**KrishiTwin Runtime**) runs forever *after*, an IoT
> system that senses + decides + actuates irrigation and fertigation. The shared core
> is kept common *on purpose*: Product 2's digital twin re-estimates the physical
> parameters from real-world data and writes them back, so Product 1's designs keep
> getting better. That feedback loop is the venture's main moat.

## 1. The two products

| | Product 1 — Design Studio | Product 2 — Runtime |
| --- | --- | --- |
| When | Pre-installation (one-off per farm) | Post-installation (continuous) |
| Job | Survey -> simulate -> optimize -> recommend top 2-3 | Sense -> decide -> actuate (irrigation + fertigation) |
| Users | Designer / agronomist / dealer | Farmer / FPO operator (mostly autonomous) |
| Core feature | Multi-objective design optimizer (`optimize.py`) | Edge decision engine + IoT control (`edge/`, `control/`) |
| Output | As-built design (JSON), BoM, sensor/valve plan, expected yield | Live control, twin state, alerts, recorded yield |
| Docs | [20-design-optimization.md](20-design-optimization.md) | [14-...](14-digital-twin-data-assimilation.md), [18-...](18-iot-control-architecture.md) |

Both depend on the shared core for the same physics so a design and its running system
speak the same language.

## 2. Shared core vs split product layers

```
                    Shared core (engine/krishiflow)  <----------------------------+
   GGA solver | components/emitters | FAO-56 | head loss | params | qc | agronomy  |
            |                                                   |                  |  calibrated params
            v                                                   v                  |  (emitter curves,
  PRODUCT 1  KrishiFlow Design Studio              PRODUCT 2  KrishiTwin Runtime   |  roughness/clog, Kc,
  (designstudio/: optimize.py, CAD, BoM)           (runtime/: edge, control, twin) |  soil params, Ky, yield)
            |                                                   |                  |
   as-built design JSON + BoM + sensor/valve  ----------->  runtime + digital-twin |
   locations + setpoints       (downstream handoff)         assimilation ----------+
                                                            (upstream feedback)
```

**Kept shared (one versioned library):** the physics and agronomy core —
[`solver.py`](../krishiflow/solver.py), [`components.py`](../krishiflow/components.py),
[`emitters.py`](../krishiflow/emitters.py), [`headloss.py`](../krishiflow/headloss.py),
[`fao56.py`](../krishiflow/fao56.py), plus the planned `params.py`, `quality/qc.py` and
`agronomy/`. Published with **semantic versioning**; both products pin a version.

**Split (product-specific layers):**

- `designstudio/` — Product 1: optimizer orchestration, survey intake, CAD/FreeCAD bridge, BoM, reports.
- `runtime/` — Product 2: `edge/` (decision runtime), `control/` (LoRa + pump/valve/fertigation firmware), `cloud/` (services), `twin/` (assimilation).

## 3. Why not split the engine too?

Splitting the physics core would (a) duplicate the math, (b) let the two copies drift
apart, and (c) sever the calibration feedback loop. We therefore split only the
product layers and keep the core common. A core improvement (e.g., a better emitter
model from CFD, see [12-solver-mathematics.md](12-solver-mathematics.md) §A6) then
upgrades **both** products at once.

This rests on the **live-parametrization principle** ([12-solver-mathematics.md](12-solver-mathematics.md)
§A0): no frozen constants — every coefficient is an externally supplied, versioned
parameter. The twin re-estimates them; promotion to the shared core is governed and
reviewable, not a silent mutation.

## 4. Data handoff between products

### 4a. Downstream: Design Studio -> Runtime (at install)
The chosen design is serialized (network JSON via
[`preprocess.py`](../krishiflow/preprocess.py)) and becomes the Runtime's **baseline
model and configuration**:

- Network topology, pipe sizes, pump curve, valve/zone layout.
- Emitter type and design flow per zone.
- Sensor / flow-meter / valve **positions and addresses** (so devices auto-map).
- Crop assignment per zone + initial agronomy parameters ([21-agronomy-layer.md](21-agronomy-layer.md)).
- Initial setpoints (target soil moisture, EC/pH, schedules).

### 4b. Upstream: Runtime -> shared core (continuous)
The twin estimates real parameters and, after governance checks, promotes them to the
shared core as new **priors**:

| Estimated in Runtime | Becomes a better prior for |
| --- | --- |
| Emitter q-P curve, clog rate | Component library, optimizer ([20](20-design-optimization.md)) |
| Pipe roughness aging (H-W C) | Network design assumptions |
| Pump performance / efficiency drift | Pump selection |
| Local Kc, van Genuchten soil params, MAD | FAO-56 design + scheduling |
| As-built vs predicted uniformity (EU/DU) | Optimizer uniformity model |
| Recorded yield -> Ky, nutrient response | Optimizer yield/profit objective |

Aggregated across farms, these become **regional design priors** (e.g., the Palakkad
rain-shadow belt) — an agronomic + hydraulic data moat.

## 5. Product independence

The shared core is shared **as a versioned dependency, not a running process**. The two
products deploy separately and can be **sold separately**: the Design Studio is useful
standalone (a design/quote tool for dealers and FPOs), and the Runtime can adopt an
existing field by importing or reverse-modeling its layout. The compounding advantage
comes from customers who run both.

## 6. Module ownership map

| Module / area | Shared core | Product 1 | Product 2 |
| --- | --- | --- | --- |
| `solver.py`, `headloss.py`, `components.py`, `emitters.py` | x | uses | uses |
| `fao56.py`, `agronomy/` | x | uses (design ET, yield) | uses (real-time) |
| `params.py` (live parameters) | x | reads | reads + writes (via twin) |
| `quality/qc.py` | x |  | uses (ingest guard) |
| `optimize.py`, CAD/BoM | | x | |
| `weather/` providers | x | uses (design climate) | uses (real-time + forecast) |
| `edge/`, `control/`, `cloud/`, `twin/` | | | x |

## 7. References to sibling docs

- Solver math + live parametrization: [12-solver-mathematics.md](12-solver-mathematics.md)
- Design optimizer: [20-design-optimization.md](20-design-optimization.md)
- Agronomy + yield: [21-agronomy-layer.md](21-agronomy-layer.md)
- Sensors + QA/QC: [13-sensors-and-instrumentation.md](13-sensors-and-instrumentation.md)
- Weather data: [17-weather-data-integration.md](17-weather-data-integration.md)
- Digital twin: [14-digital-twin-data-assimilation.md](14-digital-twin-data-assimilation.md)
- IoT control: [18-iot-control-architecture.md](18-iot-control-architecture.md)
- IIT Palakkad / KAU: [15-iitpkd-collaboration-brief.md](15-iitpkd-collaboration-brief.md)
- Bibliography: [16-annotated-bibliography.md](16-annotated-bibliography.md)
