# 02 — Problem Statement, Target User & CAE-to-Agri Skill Map

## The problem (sharp, local, fundable)

In Kerala's rain-shadow belt — **Eruthempathy, Kozhinjampara, Vadakarapathy,
Perumatty (Chittur, Palakkad)** — farmers receive only ~1,000-1,250 mm rainfall
vs the state average of ~3,000 mm. The new Moolathara Right Bank Canal extension
now delivers drip/lift irrigation to ~3,575 ha, but:

1. **Water is now available but not optimally scheduled.** Farmers irrigate by
   habit/calendar, not by crop-and-soil need. Over-irrigation wastes the scarce
   water the canal just secured; under-irrigation causes stress and yield loss.
2. **No decision tool exists at the plot level.** Krishi Bhavan advice is
   generic; there is no per-zone, day-by-day "how much water/nutrient, where,
   today" answer that accounts for this specific microclimate.
3. **FPOs cannot plan at cluster scale.** 1,500+ vegetable farmers across 650 ha
   have no shared planning layer for water budgeting, staggered harvest, or
   procurement against the Nallepilly market.

### Quantified pain (for the pitch)

- Flood/over-irrigation typically wastes **30-50% of applied water** vs precise
  scheduling (drip + need-based control reported at 40-70% savings locally).
- Mistimed irrigation/nutrient stress costs **10-25% of potential yield** in
  vegetables and mango in marginal-water zones.
- Labour for manual irrigation is **~30% reducible** with scheduled precision.

## Target user (segmented)

| Tier | Who | First wedge |
| --- | --- | --- |
| Primary pilot | The founder's 15-acre farm + 8-12 neighbouring vegetable/mango farmers in Eruthempathy | Free pilot, generate data & demo |
| Beachhead buyer | **FPOs / FPCs** in Chittur taluk (cluster planning, water budgeting) | Paid per-farmer SaaS via FPO; AgriNext deployment |
| Scale buyer | Krishi Bhavans / Dept. of Agriculture, other rain-shadow districts | Govt procurement under KERA |
| Phase 2 | Lenders, insurers, input suppliers buying the data/risk layer | See doc 09 |

Beachhead choice: **FPOs in the Chittur rain-shadow cluster**, because (a) KERA/
AgriNext explicitly routes funding and adoption through FPOs, (b) one sale
reaches hundreds of farmers, and (c) the founder's farm is inside the cluster.

## The product, concretely (MVP scope)

A web app where a farm is represented as a **mesh of zones**. For each zone and
each day the engine answers: *irrigate or not, how many litres, and why* — plus
scenario comparison (flood vs uniform drip vs twin-optimized) showing water
saved, stress days avoided, and projected yield. The working MVP in
[`../mvp/index.html`](../mvp/index.html) implements exactly this.

## CAE-to-agri skill map (the credibility core of the pitch)

| Your CAE / simulation skill | Direct agri application in FarmTwin |
| --- | --- |
| **Meshing algorithms** (discretizing a domain into cells) | Discretize the farm into irrigation/soil zones; adaptive mesh by soil type, slope, crop, emitter layout |
| **FE/CFD-style field solvers** | Water-balance + lateral moisture transport solver across the mesh; nutrient diffusion/leaching |
| **Virtual assembly-line simulation** (time-stepped, resource-constrained flow) | Time-stepped crop-growth + irrigation scheduling under a constrained daily water budget; packhouse/cold-chain throughput sim for FPOs |
| **Scenario / DOE & optimization** | What-if scenarios + optimization of irrigation/fertigation schedules to minimize water/cost subject to yield constraints |
| **Model validation against test data** | Calibrate the twin against soil-moisture sensors + observed yield; quantify error, the same rigor as validating a crash/durability model |
| **Building robust engineering software for 20 years** | Production-grade solver, reproducibility, performance — the moat vs dashboard-only competitors |

## Why now

- Canal water just arrived (2025) -> scheduling optimization is suddenly the
  binding constraint, not water availability.
- World Bank KERA / AgriNext (2026) is actively funding and distributing exactly
  this category to FPOs.
- Cheap soil/weather sensing + free ET/weather data make a software-led,
  hardware-light product viable.

## Success criteria (so execution can be verified)

1. Twin calibrated on the 15-acre farm to within a defined soil-moisture error
   band over one crop cycle.
2. Demonstrated >=30% simulated water saving vs flood baseline at equal yield.
3. >=1 signed FPO pilot MoU in the Chittur cluster.
4. KSUM Idea Grant shortlist/pitch cleared.
