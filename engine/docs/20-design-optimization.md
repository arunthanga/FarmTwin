# 20 — Design Optimization (Product 1 core)

The headline capability of the **Design Studio** ([19-...](19-two-product-architecture.md)):
instead of producing a single point design, it searches the design space and returns
the **best 2-3 setups** with their trade-offs, so the user picks with eyes open.

> **One line.** Survey the farm -> generate many candidate layouts -> score each by
> running the hydraulic solver + FAO-56 + agronomy -> return a Pareto front -> present
> the top 2-3 (least-cost / most-uniform / best-balanced) with BoM, pump duty and
> expected yield.

## 1. Survey inputs (what the user provides)

| Input | Why it matters | Drives |
| --- | --- | --- |
| Field boundary + topography / altitude | Elevation sets static head | pump duty, pressure zones |
| Water source: flow rate + available pressure | Supply constraint | pump sizing, simultaneous zones |
| Crop / plant + growth stage, area, rows | Water + nutrient demand | FAO-56 design flow, agronomy |
| Soil type | Infiltration, TAW, MAD | scheduling, zone sizing |
| Water quality (EC, hardness, sediment) | Clogging, filtration | filter + emitter choice |
| Budget | Cost ceiling | constraint |

Topography can come from a survey (GPS/DGPS), a DEM, or manual spot levels.

## 2. Decision variables

- Pipe diameters per segment — **discrete** from a commercial catalog.
- Pump model (1-50 HP) from a pump catalog ([`components.py`](../FarmTwin/components.py)).
- Zone count and layout (which laterals on which valve), watering schedule blocks.
- Emitter type and spacing (PC vs non-PC; q-P curve).
- Valve sizing and placement.
- Sensor / flow-meter count and location (observability — see
  [13-...](13-sensors-and-instrumentation.md) §B3).

## 3. Objectives and constraints

```
minimize  capital cost + present-value pumping energy (duty over the season)
maximize  distribution uniformity EU / DU (emitter-flow evenness)
maximize  expected yield / profit and water productivity (kg per m3)
subject to  Pmin <= emitter pressure <= Pmax            (emitter operating range)
            velocity <= Vmax                            (scour / water-hammer, ~1.5-2.5 m/s)
            pump operating point within its envelope
            crop peak water demand met within the irrigation window
            total cost <= budget
```

- **Cost** = pipes + fittings + pump + valves + emitters + sensors + controllers + (PV/battery for solar nodes).
- **Energy** = `rho g Q H / eta` integrated over the season's duty (from FAO-56 demand).
- **Uniformity** = emission uniformity `EU` / distribution uniformity `DU` from the
  solved emitter flows ([`emitters.py`](../FarmTwin/emitters.py)).
- **Yield / profit** = expected yield from the agronomy layer
  ([21-...](21-agronomy-layer.md)) given the design's achievable uniformity and water
  delivery, times price, minus operating cost.

## 4. Candidate scoring (the inner loop)

Each candidate design is evaluated by:

1. Build the network ([`network.py`](../FarmTwin/network.py),
   [`preprocess.py`](../FarmTwin/preprocess.py)).
2. Solve hydraulics with the GGA ([`solver.py`](../FarmTwin/solver.py)) for the
   critical operating case(s) -> nodal pressures, link flows, emitter discharges.
3. Compute uniformity (EU/DU), pump duty point and motor HP
   ([`postprocess.py`](../FarmTwin/postprocess.py)).
4. Compute crop water demand + expected yield (FAO-56 + agronomy).
5. Check constraints; compute the objective vector.

Infeasible candidates are penalized or repaired.

## 5. Optimization method

**Primary: NSGA-II** (Deb et al. 2002) — an elitist multi-objective genetic algorithm
that returns a **Pareto front** (non-dominated set) over the competing objectives.

```
init population of designs (encode the decision variables as a genome)
repeat for G generations:
    evaluate objectives (Section 4) for each design
    non-dominated sort + crowding-distance
    tournament select -> crossover -> mutation (respect catalog discreteness)
    elitist merge parents+children -> next population
return Pareto front
```

**Why NSGA-II:** handles discrete catalogs, multiple conflicting objectives, and gives a
*set* of trade-off designs (exactly what "top 2-3" needs) without collapsing to a single
weighted score.

**Lighter alternatives:**

- Simulated annealing / GA single-objective with a weighted cost function (Savic &
  Walters 1997, GANET) when only least-cost-meeting-constraints is wanted.
- LP / dynamic programming on pipe diameters for a fixed layout (fast, classic
  least-cost diameter selection).

## 6. Ranking and presenting the top 2-3

From the Pareto front, pick representative knee points and label them:

| Recommendation | Picked as |
| --- | --- |
| Lowest cost | min capital, constraints met |
| Highest uniformity | max EU/DU |
| Best balanced | knee of the Pareto front (best yield/profit per rupee) |

Each is delivered with: layout drawing (FreeCAD), **Bill of Materials**, pump duty +
motor HP, expected EU/DU, expected yield/profit and water productivity, and the
sensor/valve/flow-meter placement plan.

## 7. The Product 1 -> Product 2 bridge

Because sensor/flow-meter siting folds the **observability objective** (§B3) into the
search, the recommended design is **twin-ready**: its device positions and addresses
serialize straight into the Runtime's baseline config
([19-...](19-two-product-architecture.md) §4a). The chosen design's parameters start as
priors that the twin then refines ([14-...](14-digital-twin-data-assimilation.md)).

## 8. Module

A planned `optimize.py` orchestrating [`solver.py`](../FarmTwin/solver.py) +
[`fao56.py`](../FarmTwin/fao56.py) + [`emitters.py`](../FarmTwin/emitters.py) +
the agronomy layer; consumed by the Design Studio pre/post-processor.

## 9. References

- Savic & Walters (1997) GANET least-cost pipe-network design, *J. Water Resour. Plan. Manage.*
- Deb, Pratap, Agarwal, Meyarivan (2002) NSGA-II, *IEEE Trans. Evol. Comput.*, doi:10.1109/4235.996017
- Reca & Martinez (2006) GESTAR genetic optimization of irrigation networks, *Comput. Electron. Agric.*
- Keller & Karmeli (1974) trickle-irrigation emitter design.
- Lansey & Mays — optimal design of water distribution systems (classic least-cost).
