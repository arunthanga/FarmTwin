# FarmTwin — Requirements (Single Source of Truth)

> **Status of this document.** This is the **single source of truth (SSOT)** for *what*
> FarmTwin must do, *which technology* each solver/component should be built with, and
> *which white papers* (original + latest improvements) ground each choice. Where this
> document and any other doc disagree, **this document wins** — update it first, then the
> design docs. Deep derivations live in [`engine/docs/`](engine/docs/) (referenced inline);
> this file is the authoritative index, decisions, and acceptance criteria.

- Scope: the FarmTwin Engine (`engine/FarmTwin`), its two products
  (**Studio** = design, **Runtime** = operations), and the user experience for both.
- Audience: engineers, the design/agronomy team, and reviewers (KSUM/AgriNext, IIT-PKD/KAU).
- Conventions: requirements are tagged `R-<area>-<n>` and are **MUST** unless marked
  *(SHOULD)* / *(MAY)*. Status is one of **Done**, **Partial**, **Planned**.

## How to read this file

1. [Personas](#1-personas) — who we build for (farmer + installation technician first).
2. [Product context](#2-product-context) — the two-product split on one shared core.
3. [Technology stack — decision summary](#3-technology-stack--decision-summary).
4. [Solver & component requirements](#4-solver--component-requirements) — one block per
   solver/component with **chosen technology + rationale + original paper + latest improvements**.
5. [Pre-processing UX](#5-pre-processing-ux-requirements) and
   [Post-processing UX](#6-post-processing-ux-requirements).
6. [Cross-cutting / non-functional requirements](#7-cross-cutting--non-functional-requirements).
7. [Implementation status matrix](#8-implementation-status-matrix).
8. [Consolidated references](#9-consolidated-references-original--latest).

---

## 1. Personas

The two **primary** personas drive every UX decision. The Studio also serves a
secondary professional persona; the Runtime serves an FPO operator.

| Persona | Who | Context & constraints | What they need from FarmTwin |
| --- | --- | --- | --- |
| **Farmer** (primary) | Smallholder / FPO member, Palakkad belt | Low/medium digital literacy; **Malayalam/Tamil** first; budget Android phone; patchy 4G; cares about water bill, power hours, and yield — not hydraulics | One-glance status (irrigate now / wait / why), simple alerts, visible **water + money saved**, one-tap actions, voice/SMS fallback |
| **Installation technician** (primary) | Dealer / installer who surveys, quotes, installs, commissions | On-site, tablet/laptop, often offline; moderate technical skill; time-pressured per job | Guided survey intake, auto pipe/pump/emitter sizing, **Bill of Materials + layout drawing**, device pairing/addressing, a commissioning checklist that proves the install meets the design |
| Designer / agronomist (secondary) | In-house or partner engineer | Desktop, FreeCAD, full technical depth | CAD layout, multi-objective optimization, validation against EPANET/WinSRFR, exportable design package |
| FPO operator (secondary) | Operates Runtime for many plots | Shared dashboard, some training | Multi-zone scheduling, exceptions, season reports, regional benchmarks |

**Persona requirements**

- `R-PERSONA-1` Every farmer-facing screen MUST be usable by a low-literacy user:
  icon-first, color-coded (green/amber/red), large touch targets, **Malayalam default**
  with English toggle. *(See [§6](#6-post-processing-ux-requirements).)*
- `R-PERSONA-2` Every installer flow MUST work **fully offline** and sync later; nothing
  in the field path may hard-require connectivity.
- `R-PERSONA-3` The system MUST never ask a farmer to enter a hydraulic quantity (pressure,
  head loss, K-value); those are derived by the engine or set by the installer/designer.
- `R-PERSONA-4` Outputs MUST be expressed in the persona's units: farmer in litres / hours /
  ₹ / kg; installer in m³/h, m head, mm, HP, ₹; designer in SI.

---

## 2. Product context

Two products on **one shared, live-parametrized core** ([engine/docs/19](engine/docs/19-two-product-architecture.md)):

| | **Studio** (Product 1) | **Runtime** (Product 2) |
| --- | --- | --- |
| When | Once, pre-install | Continuous, post-install |
| Primary user | Installation technician (+ designer) | Farmer (+ FPO operator) |
| Job | Survey → simulate → optimize → recommend top 2–3 designs → BoM | Sense → decide → actuate irrigation + fertigation; learn |
| Shared core | `solver.py`, `headloss.py`, `components.py`, `emitters.py`, `fao56.py`, planned `params.py`, `agronomy/`, `quality/qc.py` | same library, pinned by semantic version |

- `R-PROD-1` The physics/agronomy core MUST be a single versioned library consumed by both
  products (no forked copies). *(Done for the implemented modules.)*
- `R-PROD-2` Every physical coefficient MUST be an externally supplied, versioned
  **parameter** (the live-parametrization principle, [engine/docs/12 §A0](engine/docs/12-solver-mathematics.md)),
  never a hard-coded constant — so the Runtime twin can re-estimate it and feed Studio. *(Done: `params.py` `ParameterSet` is wired into the solver/head-loss.)*
- `R-PROD-3` A Studio design MUST serialize (network JSON via `preprocess.py`) into a Runtime
  baseline config including device positions/addresses, crop assignment, and setpoints.

---

## 3. Technology stack — decision summary

Backend solvers may be in **any** language; the rule is **"prototype in Python, port hot
loops to C++"**. Python is the reference + glue language (it also runs FreeCAD's API,
PyFoam, and the edge SBC); C++ is for the time-/iteration-critical kernels; C/C++ firmware
runs on the field MCUs.

| Layer / component | Recommended technology | Why |
| --- | --- | --- |
| Steady network solver (GGA) | **Python + NumPy** reference (done) → **C++ (Eigen + SuiteSparse/CHOLMOD)** via `pybind11` for production scale | Sparse SPD Cholesky; deterministic; C++ removes Python per-iteration overhead on large networks |
| Head loss / components / emitters | Python (done); fold into the C++ kernel with the solver | Tiny closures called inside the Newton loop |
| Transient / water hammer (MOC) | **C++** (explicit time-stepping), optional **CUDA/GPU** for large nets | Many nodes × thousands of timesteps; tight loop |
| Surface irrigation (zero-inertia) | **C++** (implicit Preissmann + nonlinear solve/timestep) | Robust nonlinear solve each step; reuse with Python bindings |
| Soil water (Richards) | **Python prototype** (SciPy ODE / method-of-lines) → **C++** per-zone kernel | Validate fast in Python; C++ when many zones run live |
| FAO-56 ET / crop water | **Python** (done) | Lightweight; runs on edge SBC; no need for C++ |
| Component CFD (offline) | **OpenFOAM (C++)** on HPC, scripted via **PyFoam**; **preCICE** for FSI | Only place 3-D CFD earns its cost; outputs cached as curves |
| Design optimizer | **Python** (`pymoo` NSGA-II/III) orchestrating the C++ solver; surrogate models (Kriging/RBF/ANN) | Mature MO library; inner eval is the fast solver; surrogates cut cost |
| Digital twin / assimilation | **Python (NumPy/SciPy)** EKF/EnKF → C++ if real-time at scale | Matrix-heavy but per-cycle, not per-iteration |
| Data QC | **Python**, reuse **`ioos_qc`** (QARTOD) | Don't reinvent a validated QC framework |
| Edge decision runtime | **Python on a Raspberry-Pi-class SBC** reusing `fao56.py` + `solver.py` | Same code as design; offline-first |
| Field node firmware | **C / C++ (ESP-IDF / STM32 HAL)** on ESP32/STM32 | Real-time, low-power, deterministic |
| Wireless / messaging | **LoRaWAN IN865** field; **MQTT v5 / Sparkplug B** gateway↔cloud; **CBOR/Protobuf** payloads | License-free km range, low power, compact |
| Pre/post desktop (designer) | **FreeCAD workbench (Python)** | Free, scriptable in the engine's language, CAD I/O |
| Pre/post field + farmer UX | **PWA** (React or Svelte) + **i18n (Malayalam/Tamil)**, offline-first | Installable, offline, one codebase for phone/tablet |
| Cloud services | Python (FastAPI) + time-series store; MQTT broker | Shares the engine language; standard IoT backplane |
| Interchange formats | **EPANET `.inp`** import/export; **JSON** native; PDF reports | Interoperability with industry + EPANET validation |

- `R-TECH-1` The reference implementation MUST stay runnable in **pure NumPy** (SciPy and
  any C++ kernel optional) so the engine builds and validates anywhere. *(Done.)*
- `R-TECH-2` Any C++/GPU kernel MUST be validated to produce results **bit-comparable within
  tolerance** to the Python reference on the test suite before it can replace it.
- `R-TECH-3` All numeric work MUST use **SI internally**; unit conversion happens only at the
  UI/IO boundary (`R-PERSONA-4`).

---

## 4. Solver & component requirements

Each block: **what it must do** → **chosen technology + rationale** → **white paper(s)**
(original + the *latest improvements* to use). Module names map to `engine/FarmTwin/`.
Deep math is in [engine/docs/12](engine/docs/12-solver-mathematics.md);
papers are summarized in [engine/docs/22](engine/docs/22-implementation-whitepapers.md).

### 4.1 Steady network solver — GGA · `solver.py`, `headloss.py` · **Done**

- `R-NET-1` Solve a pressurized pipe network (mass + energy) for nodal heads and link flows
  using the **Global Gradient Algorithm** (Todini–Pilati), the EPANET core method.
- `R-NET-2` Treat every link (pipe, pump, valve, venturi, virtual emitter link) uniformly via
  an evaluator returning `(headloss, dheadloss/dQ)`; the system matrix is sparse SPD.
- `R-NET-3` Handle the Hazen–Williams **zero-flow singularity** so the gradient stays
  invertible in drip laterals (many near-zero flows). *(Partial — regularization to confirm.)*
- `R-NET-4` *(SHOULD)* Adopt a **high-order / robustly-damped** Newton step for hard
  pressure-driven cases to cut iterations.

**Technology:** Python + NumPy now (`numpy.linalg.solve`); production path = C++ with
**Eigen + SuiteSparse (CHOLMOD)** sparse Cholesky, bound via `pybind11`; `scipy.sparse`
as the intermediate step. Rationale: the matrix `A21 G⁻¹ A12` is SPD → Cholesky is the
right factorization; C++/CHOLMOD removes interpreter overhead for 10³–10⁵-edge networks.

**White papers**
- *Original:* Todini & Pilati (1988) GGA; Todini & Rossman (2013) / EPANET 2.2 manual (validation target).
- *Latest improvements:* Elhay & Simpson (2011) zero-flow regularization; Elhay, Piller, Deuerlein & Simpson (2015) **robust, Goldstein-damped** PDM solver; **high-order (3rd-order) GGA** for pressure-driven modeling, *J. Water Resour. Plan. Manage.* 148(3) 2022; pressure-flow-based PDA algorithms (2022); Giustolisi & Todini (2010) extended-period (tanks).

### 4.2 Head loss & component library — `components.py`, `headloss.py` · **Done**

- `R-COMP-1` Provide **Hazen–Williams** and **Darcy–Weisbach** (Swamee–Jain `f`) head loss.
- `R-COMP-2` Provide pumps/motors with curve fit and **1–50 HP motor sizing**; ball/gate/check
  valves, filters, tees, elbows via a **minor-loss K-library**; a **venturi** fertigation injector.
- `R-COMP-3` Each component is a closure `h(Q), dh/dQ` (or a node term) — no bespoke solver.

**Technology:** Python (done); compiles into the C++ Newton kernel alongside `solver.py`.
K-values and emitter curves are **data** (catalog or CFD-derived, §4.10), not code.

**White papers:** Rossman EPANET 2 manual (HW/DW, Swamee–Jain, minor losses, pumps/valves);
Swamee & Jain (1976) explicit friction factor. *Latest:* component K/emitter curves from CFD (§4.10).

### 4.3 Emitters — `emitters.py` · **Done**

- `R-EMIT-1` Non-PC power-law emitters `q = k·Pˣ` solved exactly via virtual links.
- `R-EMIT-2` Pressure-compensating emitters as clamped demand over `[p_min, p_max]`, with a
  band-violation warning.
- `R-EMIT-3` Report **EU / DU(low-quarter) / CV** uniformity from solved emitter flows.

**Technology:** Python (done). Emitter `k, x` and PC band are live parameters and may be
**CFD-derived** (§4.10) or catalog.

**White papers:** Keller & Karmeli (1974) trickle emitter design / uniformity.
*Latest:* see emitter-CFD papers in §4.10 for deriving `q = k Hˣ`.

### 4.4 Control valves (PRV/PSV/FCV) — `solver.py` extension · **Planned**

- `R-CV-1` Model PRV (downstream-pressure), PSV (upstream-pressure), FCV (flow cap), TCV
  (fixed K) by **status switching** (ACTIVE/OPEN/CLOSED) re-checked between GGA iterations,
  as EPANET does. *(MVP has TCV + open/closed; PRV/PSV/FCV flagged in code.)*

**Technology:** same C++/Python GGA core; adds per-iteration status logic.
**White papers:** Rossman EPANET 2 manual (valve status logic); Todini & Rossman (2013).

### 4.5 Transient / water hammer — MOC · `transient.py` · **Planned**

- `R-TRANS-1` Solve the 1-D water-hammer PDEs by the **Method of Characteristics** on the
  network topology to size air/relief valves and pump-trip protection and justify
  pump↔valve sequencing interlocks.
- `R-TRANS-2` Enforce the **Courant** condition `Cr = a·dt/dx ≤ 1`; model boundary devices
  (valve-closure law, pump trip with inertia, surge tank).
- `R-TRANS-3` Include an **unsteady-friction** correction for realistic pressure-wave damping.

**Technology:** **C++** (explicit MOC time-stepping is loop-heavy and a poor fit for pure
Python); optional **CUDA/GPU** for large networks; Python bindings + plots. Consider a
**second-order Godunov FVM** (or MOC) where shock capturing matters.

**White papers**
- *Original:* Wylie & Streeter (1993) *Fluid Transients in Systems* (MOC); Chaudhry *Applied Hydraulic Transients* (boundary devices).
- *Latest improvements:* "Numerical Approaches to Water Hammer Modelling", *Water* 13(11) 1597 (2021, MOC vs FDM vs FVM); MUSCL-type **second-order FVM** with Brunone unsteady friction, *Water* 17(16) 2480 (2025); **fifth-order WENO + GPU** transient solver, *Appl. Sci.* 12(14) 7350 (2022); **TVB unsteady-friction** FVM with experimental validation, *Water* 15(15) 2742 (2023); Urbanowicz et al. convolution-based unsteady friction, *Water* 14(19) 3151 (2022).

### 4.6 Surface irrigation (WinSRFR-class) — zero-inertia Saint-Venant · `surface.py` · **Planned**

- `R-SURF-1` Solve 1-D open-channel continuity+momentum with an infiltration sink using the
  **zero-inertia** simplification, discretized by the **Preissmann four-point implicit** scheme,
  coupled to **Kostiakov–Lewis** infiltration; model advance/storage/depletion/recession.
- `R-SURF-2` Validate against **WinSRFR/SRFR** for furrow/border/basin (paddy + open field).

**Technology:** **C++** (robust nonlinear implicit solve per timestep; mirror SRFR's
incident handling); Python bindings. *(SHOULD)* support Green-Ampt and 1-D-Richards
infiltration options as WinSRFR 5.1 added.

**White papers**
- *Original:* Strelkoff & Katopodes (1977) zero-inertia border irrigation; Bautista, Clemmens, Strelkoff & Schlegel (2009) **WinSRFR**, *Agric. Water Manage.* 96(7).
- *Latest improvements:* **WinSRFR 5.1 / SRFR 5** (USDA-ARS, 2019/2023 — reprogrammed engine + API, Green-Ampt & 1-D-Richards infiltration, advective-dispersive fertigation); GLUE **uncertainty assessment** of WinSRFR furrow simulation, *Water* 15(6) 1250 (2023); Lyn & Goodwin (1987) Preissmann stability.

### 4.7 Soil water (root-zone twin) — Richards equation · `richards.py` · **Planned**

- `R-SOIL-1` Solve **mixed-form** Richards with **van Genuchten–Mualem** retention/conductivity,
  using a **mass-conservative** scheme (the head-based form loses mass and is forbidden).
- `R-SOIL-2` 1-D vertical per zone with a root-uptake sink; FAO-56 supplies the top flux;
  the soil-moisture state is what the twin assimilates sensor data into. Validate vs **HYDRUS**.

**Technology:** **Python prototype** with SciPy (method-of-lines + adaptive ODE solver — the
openRE approach is concise and mass-conservative) → **C++** per-zone kernel when many zones
run live. Rationale: prototype/validate quickly, then optimize.

**White papers**
- *Original:* Celia, Bouloutas & Zarba (1990) mass-conservative **Modified Picard**, *WRR* 26(7); van Genuchten (1980) retention/conductivity, *SSSAJ*.
- *Latest improvements:* **openRE v1.0** — method-of-lines + off-the-shelf ODE solver + Solver-Flux-Output-Method, *Geosci. Model Dev.* 16:659 (2023); **adaptive L-scheme/Newton switching**, *Comput. Math. Appl.* (2023, doi:10.1016/j.camwa.2023.10.020); **semi-implicit 2nd-order** schemes for coupled water+solute, *Adv. Water Resour.* (2024); Šimůnek et al. HYDRUS (validation).

### 4.8 Reference ET & crop water — FAO-56 / ASCE · `fao56.py` · **Done**

- `R-ET-1` Compute **FAO Penman–Monteith ET0**, the **dual crop coefficient** `(Kcb+Ke)`,
  the soil-evaporation balance for `Ke`, the stress coefficient `Ks`, and the root-zone
  water balance (TAW/RAW/MAD).
- `R-ET-2` Support the **ASCE-EWRI standardized** form (fixed `Cn/Cd` for grass/alfalfa).
- `R-ET-3` Crop coefficients/root depth/MAD come from the agronomy layer and advance by
  growth stage in real time.

**Technology:** **Python** (done) — lightweight enough for the edge SBC; cross-check vs **pyfao56**.

**White papers**
- *Original:* Allen, Pereira, Raes & Smith (1998) **FAO-56**; ASCE-EWRI (2005) Standardized Reference ET.
- *Latest improvements:* Pereira, Paredes et al. (2021) **updated standard single & basal Kc/Kcb** for field crops and for vegetable crops, *Agric. Water Manage.* 243; **FAO-56 Revised Edition (2025)** (remote sensing + IoT, updated coefficients); Thorp (2022) **pyfao56**, *SoftwareX* (open cross-check).

### 4.9 Agronomy & yield — `agronomy/` · **Planned**

- `R-AGRO-1` Per-crop parameter sets (phenology/GDD, Kcb/Zr/p, Ym/Ky, salinity threshold-slope,
  N-P-K uptake, calendar) seeded from FAO tables + **KAU Package of Practices**, live-calibrated.
- `R-AGRO-2` **GDD-driven** stage advance from AWS temperature; real-time **FAO-33** yield
  estimate `(1−Ya/Ym)=Ky(1−ETa/ETc)`, extended with Maas–Hoffman salinity + nutrient stress.
- `R-AGRO-3` A **yield-recording loop** captures actual outcomes per zone/season and calibrates
  Ky/Kc/nutrient response (governed write-back) — the venture's most valuable feedback.

**Technology:** Python (`agronomy/cropdb`, `phenology`, `yield`, `records`). Heavy models
(AquaCrop / DSSAT / APSIM) run **offline** to calibrate the lightweight real-time model.

**White papers**
- *Original:* Doorenbos & Kassam (1979) **FAO-33** (Ky); Maas & Hoffman (1977) salt tolerance.
- *Latest improvements:* Steduto, Hsiao, Fereres & Raes (2012) **FAO-66 / AquaCrop**; Jones et al. (2003) DSSAT-CSM; Holzworth et al. (2014) APSIM; Pereira et al. (2021) updated Kc (§4.8).

### 4.10 Component CFD (offline) — OpenFOAM · feeds `components.py`/`emitters.py` · **Planned**

- `R-CFD-1` Use 3-D CFD **only offline** to derive `q = k Hˣ` emitter curves, anti-clog
  wall-shear, venturi loss/suction, and tee/manifold K-values; cache as the K-library /
  emitter curves the 1-D solver reads — **never per design**.
- `R-CFD-2` Pressure-compensating diaphragms need **FSI** (fluid-structure interaction).

**Technology:** **OpenFOAM (C++)** on a workstation / **IIT-PKD HPC**, scripted via
**PyFoam**; **preCICE** coupling OpenFOAM + CalculiX/deal.II for FSI.

**White papers**
- *Original:* Li et al. (2008) emitter labyrinth CFD + particle tracking, *Irrig. Sci.* 26(5).
- *Latest improvements:* Lequette et al. (2024) SKE/RSM/LES labyrinth comparison; "Performance of Emitters … CFD", *Water* 17(5) 689 (2025); PC-emitter diaphragm **FSI**, *Irrig. & Drain.* (doi:10.1002/ird.2601); preCICE coupling library.

### 4.11 Design optimizer — `optimize.py` · **Planned**

- `R-OPT-1` Search the design space (discrete pipe diameters, pump 1–50 HP, zones/schedule,
  emitter type, valve/sensor placement) and return a **Pareto front**, then present the **top
  2–3** (least-cost / most-uniform / best-balanced) with BoM, pump duty/HP, expected EU/DU and
  yield/profit.
- `R-OPT-2` Score each candidate by running the §4.1 solver + §4.8 FAO-56 + §4.9 agronomy
  under the critical operating case(s); respect catalog discreteness and constraints
  (Pmin≤P≤Pmax, V≤Vmax, pump envelope, budget).
- `R-OPT-3` Fold **sensor/flow-meter observability** into the search so the chosen design is
  twin-ready.

**Technology:** **Python (`pymoo`)** for NSGA-II/III orchestration; the inner evaluation
calls the fast (C++) solver; **surrogate models** (Kriging / RBF / ANN) approximate the
expensive yield/hydraulic objectives to cut runtime.

**White papers**
- *Original:* Deb, Pratap, Agarwal & Meyarivan (2002) **NSGA-II**; Savic & Walters (1997) GANET least-cost design.
- *Latest improvements:* Deb & Jain (2014) **NSGA-III** (many-objective); **surrogate-assisted** MO frameworks for precision-ag irrigation/fertigation, *Sci. Rep.* 13 (2023, doi:10.1038/s41598-023-27990-w); **Kriging-assisted NSGA-III** for expensive many-objective problems (2023); **NSGA-III + ANN** irrigation-limit optimization, *Water* 15(4) 783 (2023); Reca & Martínez (2006) GESTAR.

### 4.12 Digital twin / data assimilation — `assimilation.py` · **Partial**

- `R-TWIN-1` Formulate a state-space model from the hydraulic+soil+agronomy equations;
  treat parameters (roughness, clog, demand, θ, Kc, van Genuchten, Ky) as **augmented states**;
  use **pressure-dependent demand**.
- `R-TWIN-2` Use **EKF** as the lean default; **EnKF** when nonlinearity/dimension grows.
  Add **innovation (χ²) gating** + **Huber robust update** + covariance inflation so no
  single bad reading corrupts state or write-back.
- `R-TWIN-3` Promote confident parameter estimates to the shared core as new **priors** under
  governance (enough samples, σ̂≪prior σ, QC-clean, bounded step), versioned and reviewable.

**Technology:** **Python (NumPy/SciPy)** EKF/EnKF (per-cycle, parallelizable ensemble);
move to C++ only if multi-site real-time demands it.

**White papers**
- *Original:* Evensen (2003) **Ensemble Kalman Filter**, *Ocean Dynamics* 53; Bar-Shalom et al. (2001) EKF + innovation gating.
- *Latest improvements:* **3-EnKF-WDN** multi-step assimilation with PDD + parameter estimation, *Water Resour. Manage.* (2024, doi:10.1007/s11269-024-03809-9); end-to-end **digital twin with wireless pressure sensing** (Unalakleet), *ACS ES&T Water* (2025); Corr-EKF process-noise covariance (NSF PAR 10653477).

### 4.13 Sensors, placement & data quality — `sensors/`, `quality/qc.py` · **Planned**

- `R-QC-1` Every measurement MUST pass a **QARTOD-style** gate (gross-range, spike/rate,
  flatline, climatology) with pass/suspect/fail flags **before** it can drive control or
  estimation; on missing/failed critical inputs the engine **fails safe**.
- `R-QC-2` Use a **robust (Hampel: median ± k·MAD)** outlier test; site sensors for
  observability (benchmark vs BWSN).

**Technology:** **Python**, reusing the open **`ioos_qc`** package (don't reinvent QC).

**White papers:** IOOS **QARTOD** manuals; Hampel (1974) robust identifier; Ostfeld et al.
(2008) Battle of the Water Sensor Networks (placement benchmark). *Latest:* information-theory
placement, *Sensors* 22(2) 443 (2022); Branisavljević et al. (2011) sensor data validation.

### 4.14 Weather data — `weather/` · **Planned**

- `R-WX-1` Default to free feeds with a documented **source precedence**: on-farm AWS →
  **NASA POWER** (radiation gap-fill / history) / **Open-Meteo** (forecast) → IMD → GEFS/ERA5;
  feed FAO-56 ET0 and look-ahead scheduling.

**Technology:** **Python** provider adapters; self-hostable Open-Meteo for offline.
**White papers:** NASA POWER docs + "ETo from POWER", *Agronomy* 11(10) 2077 (2021);
Open-Meteo (CC BY 4.0). *Latest:* Saminathan et al. (2021) GEFS precipitation forecast.

### 4.15 Edge / IoT / control — `edge/`, `control/`, `cloud/` · **Planned**

- `R-IOT-1` **Edge-first:** the decision engine (FAO-56 + GGA + fertigation) runs locally and
  keeps irrigating through connectivity gaps; cloud is store/forecast/dashboard, not in the
  real-time loop.
- `R-IOT-2` Field radio = **LoRa/LoRaWAN IN865** (license-free, km range, solar-friendly),
  ACKed commands, **fail-safe** valve defaults on link loss.
- `R-IOT-3` **Plug-and-play onboarding:** LoRaWAN OTAA join + a self-description capability
  descriptor auto-creates a device twin (patterned on Sparkplug B / W3C WoT); payloads in
  **CBOR/Protobuf** over **MQTT v5**.
- `R-IOT-4` Pump/valve/fertigation safety interlocks: dry-run protection, pump↔valve
  sequencing (open zone before pump start; stop pump before closing last valve), EC/pH cutoffs,
  end-of-cycle flush, no-flow injection lockout.
- `R-IOT-5` Distributed sensor/valve/fertigation nodes are **solar + LiFePO4** with DC
  latching solenoids (zero idle power); low-battery surfaces as a QC health signal.

**Technology:** edge runtime in **Python** on an SBC; node firmware in **C/C++ (ESP-IDF /
STM32)**; **MQTT v5** + **Eclipse Sparkplug B** + **W3C WoT** TD; pump VFD via **Modbus-RTU**.

**White papers / specs:** LoRaWAN 1.0.4 Regional Parameters **IN865**; OASIS **MQTT v5** /
MQTT-SN; **Eclipse Sparkplug B**; **W3C Web of Things** Thing Description; **CoAP** (RFC 7252).
*Latest:* solar-powered LoRa WSN field studies for agriculture (MDPI *Sensors*/*Agronomy*).

---

## 5. Pre-processing UX requirements

Pre-processing turns a real farm into a solvable model and a buildable design. The
**installation technician** is the primary field user; the **designer** uses the full
desktop depth. UX here is a first-class requirement, not an afterthought.

- `R-PRE-1` **Guided survey intake** (installer): a step wizard for field boundary +
  topography (GPS/DGPS, DEM, or manual spot levels), water source flow/pressure, crop + area
  + rows, soil type, water quality (EC/hardness/sediment), and budget. Each field shows *why
  it matters* in plain language. *(SHOULD)* prefill from GPS/map and offline basemaps.
- `R-PRE-2` **Auto network generation:** from the survey, generate candidate drip-lateral /
  sector layouts (`preprocess.py` lateral generator) without the installer drawing pipes by hand.
- `R-PRE-3` **Catalog-driven component placement:** drop pumps/valves/filters/venturis/emitters
  from a catalog; each carries its hydraulic parameters (no manual K-values). Designer does this
  in the **FreeCAD workbench**; installer does it via a simplified picker.
- `R-PRE-4` **One-tap "optimize":** run the optimizer (§4.11) and present the **top 2–3 designs**
  side-by-side (cost / uniformity / balanced) with trade-offs in farmer-legible terms
  (₹ upfront, ₹/season power, expected yield).
- `R-PRE-5` **Bill of Materials + layout drawing** export (PDF) the installer can quote and
  procure from; itemized with quantities and sizes.
- `R-PRE-6` **Device & address plan:** the chosen design lists every sensor/valve/flow-meter
  with its location and address so commissioning can **auto-map** devices (QR/OTAA pairing).
- `R-PRE-7` **Offline-first:** the entire survey→design→BoM flow MUST complete with no network;
  sync to cloud later (`R-PERSONA-2`).
- `R-PRE-8` **EPANET `.inp` import/export** *(SHOULD)* so existing designs interoperate and
  validate.
- `R-PRE-9` **Round-trip integrity:** a design serialized to JSON and reloaded MUST reproduce the
  same solver result (regression-tested).

**Technology:** FreeCAD workbench (Python) for the designer; the installer wizard is part of
the **PWA** (offline, tablet-first, large controls, Malayalam/English).

## 6. Post-processing UX requirements

Post-processing communicates results. The **farmer** is the primary consumer of the
Runtime view; the **installer** consumes the commissioning/validation view.

**Farmer (Runtime dashboard)**
- `R-POST-1` A single home screen answers three questions at a glance, icon + color first:
  **Should I irrigate now?** (green/amber/red), **What's my soil moisture / which zones?**,
  **How much water + money have I saved?** — no hydraulic jargon (`R-PERSONA-3`).
- `R-POST-2` **One-tap actions** (irrigate now / skip / acknowledge alert) and plain-language
  alerts ("Zone 3 valve not responding", "Skip today — rain expected").
- `R-POST-3` **Malayalam default**, English toggle; **voice / SMS / IVR fallback** for
  low-connectivity or low-literacy users.
- `R-POST-4` Show the headline KPI the venture sells: **water saved % and yield at equal-or-better**
  vs the farmer's old schedule.

**Installer (commissioning / validation view)** and **Designer (analysis view)**
- `R-POST-5` Network result report: nodal **pressures**, link **flows + velocities**, emitter
  discharges, **EU / DU(low-quarter) / CV**, pump duty point + **motor HP**, and PC-band warnings
  (`postprocess.py`). *(Done for the report; plots optional via matplotlib.)*
- `R-POST-6` **Visual overlay:** color pipes by velocity, nodes by pressure, emitters by
  uniformity — FreeCAD overlay (designer) and a web map (installer/farmer-lite).
- `R-POST-7` **Commissioning check:** measured vs designed pressures/flows at head + zone valves,
  pass/fail against the design's tolerance band, producing a sign-off the install meets the design.
- `R-POST-8` Exportable **PDF report** (design + as-built) for the KSUM/AgriNext pitch and FPO records.

**Technology:** PWA (React/Svelte) + charting; FreeCAD overlay for the desktop; PDF export.
Accessibility: large fonts, high-contrast color (and color-blind-safe palettes), offline cache.

---

## 7. Cross-cutting / non-functional requirements

- `R-NFR-1 Live-parametrization:` no frozen physical constants; every coefficient is a
  versioned parameter with `{value, prior, uncertainty, source, updated_at, version}`
  (`params.py`, planned). Twin write-back is governed (`R-TWIN-3`).
- `R-NFR-2 Offline-first:` field paths (install survey, edge control, farmer dashboard) MUST
  function without connectivity and reconcile on reconnect.
- `R-NFR-3 Performance targets:` steady network solve for a typical farm (≤ a few thousand
  links) **< 1 s**; optimizer Pareto front in **minutes** (surrogate-assisted); edge decision
  cycle well within its scheduling window. C++/GPU kernels exist to hold these at scale.
- `R-NFR-4 Determinism & reproducibility:` same inputs + same parameter version → same result;
  parameter versions are recorded with every run.
- `R-NFR-5 Validation targets:` GGA vs **EPANET** on shared `.inp`; surface vs **WinSRFR**;
  soil vs **HYDRUS**; FAO-56 vs **pyfao56**; plus the in-repo analytic tests
  (`tests/test_solver.py`, `tests/test_fao56.py`, **passing**).
- `R-NFR-6 Units & i18n:` SI internally; persona units + Malayalam/Tamil at the boundary.
- `R-NFR-7 Security:` per-device keys + message auth on the IoT bus; secrets never in the repo;
  governed, reviewable parameter write-back.
- `R-NFR-8 Licensing/openness:` engine stays an open, India-built alternative to
  IRRICAD/IrriPro/WCADI/HydroCalc; built on FreeCAD + OpenFOAM to avoid per-seat license cost.
- `R-NFR-9 Packaging:` reference engine installs with `pip install -r engine/requirements.txt`
  (NumPy required; SciPy/matplotlib optional); the C++ kernels ship as optional accelerators.

---

## 8. Implementation status matrix

Single source of truth for *what exists vs what's planned* (verified by running the tests
and the demo).

| Area | Module | Status | Notes |
| --- | --- | --- | --- |
| GGA steady solver | `solver.py` | **Done** | All analytic tests pass |
| Head loss (HW + DW) | `headloss.py` | **Done** | Swamee–Jain `f` |
| Components (pumps/valves/fittings/venturi, 1–50 HP) | `components.py` | **Done** | K-library + motor sizing |
| Emitters (PC + non-PC) | `emitters.py` | **Done** | EU/DU/CV |
| Pre-processor (JSON + lateral generator) | `preprocess.py` | **Done** | JSON round-trip |
| Post-processor (report + uniformity + duty/HP) | `postprocess.py` | **Done** | Plots optional |
| FAO-56 ET / dual-Kc / balance | `fao56.py` | **Done** | ASCE form |
| Zero-flow regularization | `headloss.py` / `components.py` | **Done** | Elhay–Simpson |Q| floor at `zero_flow_eps_m3s` in the pipe gradient |
| Control valves PRV/PSV/FCV | `solver.py` | **Planned** | TCV + open/closed done |
| Live parameters | `params.py` | **Done** | `ParameterSet` wired into solver/head-loss (A0); `LiveParameter` carries write-back provenance |
| Transient / water hammer | `transient.py` | **Partial** | Python MOC ref (vs Joukowsky); optional TSNet; C deferred |
| Surface irrigation | `surface.py` | **Partial** | Python ref: Kostiakov-Lewis + volume-balance; C/Preissmann deferred |
| Soil water (Richards) | `richards.py` | **Partial** | Python ref: van Genuchten + method-of-lines (SciPy) |
| Agronomy + yield | `agronomy.py` | **Partial** | GDD + FAO-33 + Maas-Hoffman |
| Component CFD (offline) | OpenFOAM | **Planned** | Feeds K/emitter library |
| Optimizer | `optimize.py` | **Planned** | pymoo NSGA-II/III |
| Digital twin / assimilation | `assimilation.py` | **Partial** | Iterated-EKF parameter calibration from sensor pressures/flows, QC fail-safe + innovation gating + governed write-back; EnKF deferred |
| QC | `quality.py` | **Done** | B1-B6 + Hampel; `ioos_qc` optional backend |
| Weather providers | `weather/` | **Planned** | POWER/Open-Meteo/IMD |
| Edge / IoT / control | `edge/`, `control/`, `cloud/` | **Planned** | LoRa, MQTT, solar |
| EPANET `.inp` I/O | `preprocess.py` | **Partial** | WNTR-backed when installed; minimal built-in parser fallback |
| FreeCAD workbench | — | **Planned** | JSON round-trip → viewer → workbench |
| Pre/post PWA + i18n | — | **Planned** | Farmer + installer UX |

---

## 9. Consolidated references (original + latest)

Grouped by solver/component. **Original** = read before coding; **Latest** = the modern
improvement to incorporate. Full summaries: [engine/docs/22](engine/docs/22-implementation-whitepapers.md)
and [engine/docs/16](engine/docs/16-annotated-bibliography.md).

**Network solver (§4.1–4.4)**
- Todini & Pilati (1988) GGA; Todini & Rossman (2013) *J. Hydraul. Eng.*; Rossman EPANET 2 manual (2000).
- Swamee & Jain (1976) explicit friction factor.
- Elhay & Simpson (2011) zero-flow regularization, doi:10.1061/(ASCE)HY.1943-7900.0000411.
- Elhay, Piller, Deuerlein & Simpson (2015) robust Goldstein-damped PDM, doi:10.1061/(ASCE)WR.1943-5452.0000578.
- High-order GGA for pressure-driven WDN modeling (2022), doi:10.1061/(ASCE)WR.1943-5452.0001524.
- Giustolisi & Todini (2010) extended-period GGA, doi:10.2166/hydro.2010.164.
- Keller & Karmeli (1974) trickle emitter design.

**Transients (§4.5)**
- Wylie & Streeter (1993) *Fluid Transients in Systems*; Chaudhry *Applied Hydraulic Transients*.
- "Numerical Approaches to Water Hammer Modelling", *Water* 13(11) 1597 (2021).
- MUSCL-type 2nd-order FVM + Brunone friction, *Water* 17(16) 2480 (2025).
- WENO5 + GPU transient solver, *Appl. Sci.* 12(14) 7350 (2022).
- TVB unsteady-friction FVM (experimental), *Water* 15(15) 2742 (2023); Urbanowicz et al., *Water* 14(19) 3151 (2022).

**Surface irrigation (§4.6)**
- Strelkoff & Katopodes (1977); Bautista, Clemmens, Strelkoff & Schlegel (2009) WinSRFR, doi:10.1016/j.agwat.2009.03.007.
- WinSRFR 5.1 / SRFR 5 (USDA-ARS, 2019/2023) — engine + API, Green-Ampt & 1-D-Richards infiltration.
- GLUE uncertainty assessment of WinSRFR furrow, *Water* 15(6) 1250 (2023); Lyn & Goodwin (1987).

**Soil water (§4.7)**
- Celia, Bouloutas & Zarba (1990) *WRR* 26(7), doi:10.1029/WR026i007p01483; van Genuchten (1980) *SSSAJ*.
- openRE v1.0 (method-of-lines + SFOM), *Geosci. Model Dev.* 16:659 (2023).
- Adaptive L-scheme/Newton switching, doi:10.1016/j.camwa.2023.10.020 (2023).
- Semi-implicit 2nd-order water+solute schemes, *Adv. Water Resour.* (2024); Šimůnek et al. HYDRUS.

**ET & agronomy (§4.8–4.9)**
- Allen, Pereira, Raes & Smith (1998) FAO-56; ASCE-EWRI (2005), doi:10.1061/9780784408056.
- Pereira, Paredes et al. (2021) updated Kc/Kcb — field crops & vegetable crops, *Agric. Water Manage.* 243.
- FAO-56 Revised Edition (2025, FAO); Thorp (2022) pyfao56, *SoftwareX*.
- Doorenbos & Kassam (1979) FAO-33; Steduto et al. (2012) FAO-66/AquaCrop; Maas & Hoffman (1977); DSSAT/APSIM; KAU Package of Practices.

**Component CFD (§4.10)**
- Li et al. (2008) labyrinth CFD, doi:10.1007/s00271-008-0108-1; Lequette et al. (2024).
- Emitter CFD, *Water* 17(5) 689 (2025); PC-emitter FSI, doi:10.1002/ird.2601; preCICE.

**Optimization (§4.11)**
- Deb et al. (2002) NSGA-II, doi:10.1109/4235.996017; Savic & Walters (1997) GANET.
- Deb & Jain (2014) NSGA-III; surrogate-assisted MO precision-ag, doi:10.1038/s41598-023-27990-w (2023).
- Kriging-assisted NSGA-III (2023); NSGA-III + ANN irrigation limit, *Water* 15(4) 783 (2023); Reca & Martínez (2006).

**Twin / assimilation / QC (§4.12–4.13)**
- Evensen (2003) EnKF, doi:10.1007/s10236-003-0036-9; Bar-Shalom et al. (2001).
- 3-EnKF-WDN with PDD, doi:10.1007/s11269-024-03809-9 (2024); DT wireless pressure sensing, *ACS ES&T Water* (2025).
- IOOS QARTOD; Hampel (1974), doi:10.1080/01621459.1974.10482962; Ostfeld et al. (2008) BWSN.

**Weather / IoT (§4.14–4.15)**
- NASA POWER + ETo from POWER, *Agronomy* 11(10) 2077 (2021); Open-Meteo (CC BY 4.0).
- LoRaWAN IN865; OASIS MQTT v5; Eclipse Sparkplug B; W3C Web of Things; CoAP (RFC 7252).
