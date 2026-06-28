# 15 — IIT Palakkad & KAU Collaboration Brief

A concrete map of nearby research capability to KrishiFlow modules, plus an engagement
plan. The goal: validation, credibility (papers/IP), HPC access for the offline CFD, and
agronomy ground-truth — all within ~50 km of the Eruthempathy pilot.

## 1. Faculty / institution -> module mapping

| Who | Their work | Fits our module |
| --- | --- | --- |
| **Dr. B. Sridharan** (IIT PKD, Civil) | Computational & experimental hydraulics; teaches "Design of Water Supply Pipe Networks" and "Computational Hydraulics"; built IROMS (local-inertial 2-D FV flood model) and IROMS-C2D (river-ocean FV) | Validation of the GGA/MOC solvers ([12-...](12-solver-mathematics.md) §A1-A2), the zero-inertia surface track (§A3); access to the Water Resources lab flume/pipe rigs + HPC for OpenFOAM (§A6) |
| **Dr. Subhasis Mitra** (IIT PKD) | Irrigation Engineering; FAO ET methods, ET "paradox", GEFS precipitation/ET forecast post-processing | FAO-56/ASCE module + forecast-driven scheduling ([12-...](12-solver-mathematics.md) §A5, [17-...](17-weather-data-integration.md)) |
| **Dr. Athira P. / Dr. Sarmistha Singh** (IIT PKD) | Watershed / hydrologic modeling, agricultural water security | Catchment water balance, FPO-cluster scale-up |
| **TECHIN** (IIT PKD TBI) | Startup-India-recognized Technology Business Incubator | Incubation + grants in parallel with KSUM/AgriNext ([docs/07-funding-roadmap.md](../../docs/07-funding-roadmap.md)) |
| **Kerala Agricultural University (KAU)** — RARS Pattambi / Chittur belt | Crop agronomy, Package of Practices, fertigation, varietal trials | Source + validate the agronomy layer ([21-...](21-agronomy-layer.md)): Kc, nutrient recipes, yield calibration for local crops |

## 2. Key papers and what they give us

- **IROMS-C2D river-ocean FV** (Sridharan, Cea, Kuiry), zenodo.8128928 — finite-volume
  shallow-water solver pedigree; partner credibility for our FV/surface work.
- **Nithila Devi et al. (2020)** retention-storage urban flooding, *Water* 12(10), 2875 —
  applied hydraulic modeling in the group.
- **Varghese & Mitra (2024)** ETo variability & evapotranspiration paradox, *Water
  Resour. Manage.*, doi:10.1007/s11269-024-03931 — directly informs our ET module's
  local behavior.
- **Saminathan, Medina, Mitra, Tian (2021)** GEFS precipitation forecast over India,
  *J. Hydrology* 598:126431 — the basis for forecast-driven scheduling
  ([17-...](17-weather-data-integration.md)).
- **Saminathan & Mitra** NWP-based ETo forecasts — bias-correction recipe for our
  forecast feed.
- **KAU Package of Practices** — crop calendars, Kc, fertigation schedules seeding
  [21-agronomy-layer.md](21-agronomy-layer.md).

## 3. Resources to request

- **Water Resources Engineering Lab** — flume + pipe-network rigs to validate the GGA
  (pressures/flows) and emitter/uniformity claims.
- **HPC cluster** — run the offline OpenFOAM emitter-curve / K-value library
  ([12-...](12-solver-mathematics.md) §A6).
- **KAU trial plots / RARS** — agronomy ground truth (yield, nutrient response) for the
  recording loop ([21-...](21-agronomy-layer.md) §F4).

## 4. Engagement plan (steps)

1. Share the MVP + a one-page validation note; propose a joint **solver-vs-EPANET +
   flume** validation with Sridharan's group.
2. Scope an **M.Tech project** to build the OpenFOAM emitter-curve library on IIT HPC.
3. Co-develop the **FAO-56 forecast module** with Mitra's group (GEFS post-processing).
4. Engage **KAU RARS** for crop parameter calibration and a co-located trial.
5. Apply to **TECHIN** for incubation + grant runway alongside KSUM/AgriNext.
6. Co-author a **validation paper** for IP and credibility.

## 5. Outreach artifacts to prepare

- 1-page tech brief (this stack, the two products).
- Validation plan (cases, metrics, datasets).
- MoU draft (scope, IP, data sharing) — see
  [docs/08-fpo-pilot-mou-template.md](../../docs/08-fpo-pilot-mou-template.md) for a
  starting template style.
