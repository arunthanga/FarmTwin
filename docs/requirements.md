# FarmTwin — Requirements Document (Single Source of Truth)

**Version:** 1.0.0  
**Date:** 2026-06-29  
**Repository:** https://github.com/arunthanga/FarmTwin  
**Pilot site:** 15-acre rain-shadow farm, Eruthempathy, Chittur, Palakkad District, Kerala  
**Status:** Living document — supersedes all prior scattered design notes

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [User Personas](#2-user-personas)
3. [System Architecture](#3-system-architecture)
4. [Pre-Processing — FarmTwin Studio](#4-pre-processing--farmtwin-studio)
5. [Solvers — Shared Physics Core (krishiflow)](#5-solvers--shared-physics-core-krishiflow)
6. [Post-Processing — FarmTwin Studio Output](#6-post-processing--farmtwin-studio-output)
7. [Runtime — FarmTwin Runtime](#7-runtime--farmtwin-runtime)
8. [IoT & Edge Control Layer](#8-iot--edge-control-layer)
9. [Data Assimilation & Digital Twin Layer](#9-data-assimilation--digital-twin-layer)
10. [Weather Data Integration](#10-weather-data-integration)
11. [Component CFD (Offline)](#11-component-cfd-offline)
12. [Design Optimization](#12-design-optimization)
13. [Agronomy Layer](#13-agronomy-layer)
14. [Cloud & Dashboard](#14-cloud--dashboard)
15. [Technology Stack Summary](#15-technology-stack-summary)
16. [Non-Functional Requirements](#16-non-functional-requirements)
17. [Reference White Papers](#17-reference-white-papers)

---

## 1. Product Overview

FarmTwin is a deeptech agri-digital-twin platform that applies hydraulic simulation and agronomy science to farm irrigation. It ships as **two products on one shared physics engine**:

| Product | When Used | Primary Users |
|---|---|---|
| **FarmTwin Studio** | Pre-installation (one-off per farm) | Installation person / agronomist / dealer |
| **FarmTwin Runtime** | Post-installation (continuous, always-on) | Farmer / FPO operator |

The shared engine (`engine/krishiflow`) is the single versioned library that both products pin. Every physical coefficient and modeling constant in the engine is a live, externally supplied parameter — never a hard-coded value. The Runtime continuously re-estimates these parameters from field data and feeds improved priors back to the shared core; this calibration feedback loop is the venture's primary technical moat.

**Competitive positioning:** Open alternative to IRRICAD, IrriPro, WCADI (Rivulis), and HydroCalc 3.0 (Netafim) for pressurized irrigation network design, plus a WinSRFR-class surface irrigation track.

---

## 2. User Personas

### 2.1 Farmer (Runtime Persona)

**Profile:** Small-to-medium landholding farmer in rain-shadow Kerala/Tamil Nadu belt. Likely semi-literate in English; comfortable with Malayalam or Tamil. Owns a smartphone. Has basic familiarity with pump/valve operations but no engineering background.

**Goals:**
- Know exactly when to irrigate and for how long, without guessing
- Receive actionable WhatsApp/SMS alerts rather than dashboards full of graphs
- Confident that the system is not wasting water or money on fertiliser
- Trust that the pump/valves will sequence correctly without manual intervention

**Pain points:**
- Irregular power supply; pump trips on dry-run
- Fertiliser overdosing or underdosing leads to yield loss
- Poor-quality groundwater with variable EC/pH

**UX requirements (Runtime):**
- Mobile-first progressive web app (PWA) in Malayalam/English toggle
- Home screen: one-line farm status ("Irrigating Zone 2 — 40 min remaining"), last alert, and soil moisture bars per zone — all visible without scrolling
- Alerts pushed via WhatsApp Business API (primary) and SMS (fallback); no app open required
- All critical decisions already made by the system; farmer approves or overrides with a single tap
- Voice-note alerts in Malayalam using text-to-speech for critical pump/valve faults
- Offline-capable: app shows last-known state when connectivity drops

### 2.2 Installation Person (Studio Persona)

**Profile:** Irrigation contractor or FPO field officer. Has basic CAD familiarity but not a civil engineer. Walks the field with a tablet or ruggedized phone. Places sensors, mounts valves, and commissions the edge controller. Follows a printed or on-screen checklist. May service multiple farms per week.

**Goals:**
- Survey a new farm and get a pipe-layout recommendation in a single site visit
- Receive a complete Bill of Materials (BoM) with part numbers, lengths, and counts
- Commission sensor and valve nodes without network engineering knowledge (plug-and-play)
- Hand off a running system to the farmer by end of day

**Pain points:**
- Manual survey → design cycle takes days with conventional tools
- BoM errors discovered only at the hardware store
- Sensor/valve commissioning requires vendor-specific tools and app logins

**UX requirements (Studio):**
- Field survey input via tablet map: tap to place nodes (pump, junction, valve, emitter zone, sensor) on a GPS base map; tap-and-drag pipe routes
- Immediate visual feedback: pressure-colour-coded network overlay updates on every node placement (GGA solve in < 2 s for farms up to 500 nodes)
- Wizard-style flow: Survey → Crop selection → Run optimizer → Review top 3 designs → Export BoM + as-built JSON
- BoM exported as PDF and shareable via WhatsApp; includes QR codes linking to vendor product pages
- Commissioning checklist app: scan LoRaWAN DevEUI from node sticker → auto-registers device → runs pre-flight pressure/flow check → marks item done
- No login required for Studio trial mode (first 2 designs free; subscription for unlimited)

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Shared Core (engine/krishiflow)              │
│  GGA Solver | Head-Loss | Components | Emitters | FAO-56 | Params   │
│  QC Guards  | Agronomy  | Surface    | Richards | Transient         │
└────────────────────────┬────────────────────────┬───────────────────┘
                         │                        │
           ┌─────────────▼──────────┐  ┌─────────▼──────────────────┐
           │   PRODUCT 1            │  │   PRODUCT 2                │
           │   FarmTwin Studio      │  │   FarmTwin Runtime         │
           │                        │  │                            │
           │  Pre-processing:        │  │  Edge decision engine      │
           │  • GPS survey input     │  │  • FAO-56 real-time        │
           │  • FreeCAD workbench    │  │  • GGA for zone sizing     │
           │  • Network topology     │  │  • Fertigation PID         │
           │  • Crop/soil wizard     │  │                            │
           │                        │  │  IoT control:              │
           │  Solver runs:           │  │  • LoRa field nodes        │
           │  • GGA (network)        │  │  • MQTT messaging          │
           │  • FAO-56 (ET/crop)     │  │  • Pump/valve interlocks   │
           │  • NSGA-II (optimizer)  │  │                            │
           │                        │  │  Digital twin:             │
           │  Post-processing:       │  │  • EKF/EnKF assimilation   │
           │  • Design reports       │  │  • Parameter estimation    │
           │  • BoM (PDF/WhatsApp)   │  │  • Upstream parameter      │
           │  • As-built JSON        │  │    write-back to core      │
           │  • Yield forecast       │  │                            │
           └────────────────────────┘  └────────────────────────────┘
                         │                        │
                         └──────────┬─────────────┘
                                    │
                          ┌─────────▼──────────┐
                          │   Cloud / Dashboard │
                          │   (Farmer PWA)      │
                          │   WhatsApp alerts   │
                          │   Weather APIs      │
                          └────────────────────┘
```

**Data flow between products:**  
- Studio → Runtime (at install): as-built design JSON, network topology, sensor/valve addresses, crop assignments, initial setpoints  
- Runtime → Core (continuous): calibrated emitter curves, pipe roughness, pump drift, local Kc, soil params, recorded yield

---

## 4. Pre-Processing — FarmTwin Studio

### 4.1 Farm Survey Module

**Purpose:** Capture the physical farm layout from a field visit and convert it into a network topology for the solver.

**Technology:** React Native (tablet + Android/iOS) with Mapbox GL JS offline maps and GPS. Field data stored in JSON (aligned with preprocess.py NetworkJSON schema). Sync to cloud on connectivity restore.

**Functional requirements:**

- Load offline satellite/topo basemap tiles for Palakkad region (cached on device)
- Place nodes by GPS tap: pump, reservoir, pressure-reducing valve (PRV), junction, valve zone, emitter zone, sensor location
- Drag-connect nodes to define pipe routes; assign pipe diameter and material (PVC / HDPE / GI) from a dropdown
- Elevation input: read from SRTM/Google Elevation API for each node; override manually for bunds
- Crop type selection per zone (from agronomy layer crop catalogue)
- Soil texture input per zone: dropdown (sandy / loam / clay-loam / red laterite) or lab report upload (CSV)
- Auto-generate drip lateral layout within an emitter zone given row spacing, emitter spacing, and lateral length
- Export topology as preprocess.py-compatible JSON; this JSON is the canonical hand-off artefact

### 4.2 Network Pre-Processor (preprocess.py)

**Technology:** Python 3.11+. Current implementation: JSON network I/O + drip-lateral generator.

**Functional requirements:**

- Parse NetworkJSON: nodes (id, type, elevation, demand), links (id, from_node, to_node, diameter, length, material, roughness), emitters, pumps, valves
- Auto-generate virtual emitter links (one per emitter) for GGA handling
- Validate topology: no disconnected subgraphs, at least one fixed-head node, all pipe diameters within catalogue range
- Produce solver-ready internal network representation (adjacency/incidence matrices A12, A21, A10)
- Write pre-flight report: node/link counts, total pipe length by diameter, emitter count per zone

### 4.3 Component Library (components.py)

**Technology:** Python 3.11+. Extend with a JSON catalogue for hardware lookup.

**Functional requirements:**

- Pumps/motors: curve-fit H-Q polynomial (a + bQ + cQ²); 1–50 HP motor sizing; efficiency curve
- Ball, gate, check valves: minor-loss K library indexed by nominal diameter
- PRV, PSV, FCV: status-based (active/open/closed) with setpoint head
- Filters: dP vs flow curve (for screen and disc filters); clog-factor as live parameter
- Tees, elbows, reducers: K values per fitting type and diameter ratio
- Venturi fertigation injector: loss element (dP vs Q) + injection flow vs differential pressure
- All K and curve coefficients are live parameters (A0 parametrization principle)
- Hardware lookup: each component instance maps to a catalogue SKU (for BoM generation)

---

## 5. Solvers — Shared Physics Core (krishiflow)

### 5.1 Network Hydraulic Solver — GGA (solver.py, headloss.py)

**Algorithm:** Global Gradient Algorithm (GGA), Newton-Raphson, sparse SPD Cholesky solve.

**Technology:** Python 3.11 with NumPy/SciPy (current MVP). For production performance (farms > 500 nodes, edge deployment), rewrite the solver core in **C** (as a CPython extension module via cffi or ctypes). The C core exposes `solve_network(network_json) → result_json` and is callable from Python and from the C++ edge runtime.

**Rationale for C:** The GGA inner loop is a sparse Cholesky solve repeated 5–20 Newton iterations. NumPy/SciPy is adequate for design-time Studio runs (< 2 s target for 500 nodes), but the edge controller is a Raspberry Pi-class SBC or ARM MCU where Python overhead is prohibitive for the real-time decision loop. A C core with SuiteSparse (CHOLMOD) solves 500-node networks in < 50 ms on RPi 4.

**Mathematical reference:**
- Todini & Pilati (1988): original GGA formulation — A12/A21/A10 matrix assembly, two-step Newton-Raphson decomposition, SPD structure
- Todini & Rossman (2013) / EPANET 2 manual: unified GGA with HW/DW head-loss, pumps, valves, convergence criteria; cross-validation target
- Elhay & Simpson (2011): zero-flow regularization for Hazen-Williams singular gradient (Q → 0)
- Giustolisi & Todini (2010): extended-period (tank) GGA

**Functional requirements:**

- Hazen-Williams head loss: `h_L = 10.67 L Q^1.852 / (C^1.852 D^4.87)`, n = 1.852
- Darcy-Weisbach head loss: `f` via Swamee-Jain explicit approximation; exact `df/dQ` gradient
- Elhay-Simpson regularization applied whenever |Q| < Q_min (threshold = 1e-6 m³/s)
- Pumps: treated as negative-head links with `H_pump(Q) = a + bQ + cQ²`; shut-off and runout bounds enforced
- Emitters: modeled as virtual links with `q = k H^x`; PC emitters use piecewise linear band
- PRV/PSV/FCV: status logic (active/open/closed) updated between Newton iterations
- Convergence: `||dQ||/||Q|| < 1e-4` (default); max 50 iterations; warn if not converged
- EPANET `.inp` import/export for validation and interoperability (roadmap)
- Output: nodal pressures (m head and kPa), link flows (L/h and m³/h), velocities (m/s), emitter discharges, EU/DU(lq)/CV uniformity, pump duty point and HP

**Live parameters (A0):** Hazen-Williams C per pipe, Darcy roughness ε per pipe, minor-loss K per fitting, pump curve coefficients, valve Cv, nodal demand, background leakage.

### 5.2 Transient Solver — MOC (transient.py, planned)

**Algorithm:** Method of Characteristics (MOC), fixed grid with Courant condition.

**Technology:** **C** (standalone library, linked into the Python engine via cffi). MOC is time-critical for surge sizing and must run faster than real-time. SuiteSparse not required here; MOC is an explicit march with only device-equation solves at boundaries.

**Mathematical reference:**
- Wylie & Streeter (1993) *Fluid Transients in Systems*: MOC derivation, C+/C- compatibility equations, Courant stability, boundary device equations (valve closure law, pump trip with inertia, surge tank, air/relief valve)
- Chaudhry *Applied Hydraulic Transients*: practical implementation guide
- "Numerical Approaches to Water Hammer Modelling" (*Water* 2021, 13(11), 1597): open-access review comparing MOC vs FDM vs FVM; unsteady-friction (Brunone) corrections; discretization guidance

**Functional requirements:**

- 1-D hyperbolic mass+momentum PDEs: `dH/dt + (a²/gA) dQ/dx = 0`; `dQ/dt + gA dH/dx + fQ|Q|/(2dA) = 0`
- MOC characteristic equations: C+ `H_P = C_P - B Q_P`; C- `H_P = C_M + B Q_P`
- Courant condition: `Cr = a·dt/dx ≤ 1` enforced; interpolation for non-integer Courant
- Boundary devices: valve closure (user-specified law), pump trip (with motor+impeller inertia WR²), air/relief valve, one-way surge tank, dead-end reflection
- Brunone unsteady-friction model for accurate pressure-wave damping
- Outputs: max/min surge pressures at all nodes, time-to-peak, recommended air-valve sizes, pump trip protection adequacy
- Use case: offline sizing of surge protection at design time (Studio); also informs pump↔valve sequencing interlocks in the edge controller (must open a zone valve before pump start; must stop pump before closing last valve)

**Live parameters (A0):** wave celerity `a` (pipe material and age), unsteady-friction coefficient.

### 5.3 Surface Irrigation Solver — Zero-Inertia Saint-Venant (surface.py, planned)

**Algorithm:** Zero-inertia simplification of 1-D Saint-Venant; Preissmann four-point implicit; Kostiakov-Lewis infiltration.

**Technology:** **C** (standalone library). The Preissmann scheme requires solving a tridiagonal system per time step — trivially fast in C, but the iterative advance/recession phase and volume-balance closure loop benefit from low-overhead tight loops.

**Mathematical reference:**
- Strelkoff & Katopodes (1977) *J. Irrig. Drain. Div.* ASCE 103(IR3):257-269: foundational paper deriving zero-inertia simplification for border irrigation; justifies dropping acceleration terms at low Froude number (all practical fields)
- Bautista, Clemmens, Strelkoff & Schlegel (2009) *Agric. Water Manage.* 96(7) doi:10.1016/j.agwat.2009.03.007: WinSRFR architecture, SRFR engine, Kostiakov-Lewis and Green-Ampt infiltration, volume-balance procedures — primary reference design and validation target
- Bautista et al. SRFR 5, doi:10.1061/(ASCE)IR.1943-4774.0000938: updated SRFR 5 engine with computational-incident handling
- Lyn & Goodwin (1987): Preissmann scheme stability analysis

**Functional requirements:**

- 1-D continuity + zero-inertia momentum with infiltration sink `z`: `dA/dt + dQ/dx + dz/dt = 0`; `gA(dh/dx − S₀ + Sf) = 0`
- Preissmann four-point implicit with weighting factor θ = 0.6 (default)
- Kostiakov-Lewis infiltration: `z = k·tᵃ + b·t`; Green-Ampt as alternative
- Phases: advance, storage (ponded), depletion, recession with phase-transition detection
- Volume-balance check at end of each phase; parameter estimation (inverse solution for k, a, b from advance data)
- Computational-incident handling: instability detection and adaptive time-step reduction
- Outputs: advance/recession curves, application efficiency, distribution uniformity, deep percolation and runoff fractions, required inflow rate and set-time
- Validation against WinSRFR on published test cases

**Live parameters (A0):** Kostiakov-Lewis k, a, b; Manning n; inflow rate Q₀.

### 5.4 Soil Water Solver — Richards Equation (richards.py, planned)

**Algorithm:** Mixed-form Richards, Modified Picard iteration, van Genuchten–Mualem retention/conductivity, 1-D vertical FV/FE per zone.

**Technology:** **C** (standalone library). Modified Picard with lumped time matrix requires a tridiagonal solve per iteration per zone. Performance is critical for the real-time twin assimilation loop (many zones, many daily steps).

**Mathematical reference:**
- Richards (1931) *Physics* 1(5):318-333: original unsaturated flow equation
- Celia, Bouloutas & Zarba (1990) *WRR* 26(7):1483-1496 doi:10.1029/WR026i007p01483: **the essential implementation reference** — proves head-based form loses mass; derives mixed-form with Modified Picard + lumped diagonal time matrix for exact mass conservation at no extra cost; clean pseudocode
- van Genuchten (1980) *SSSAJ* 44(5):892-898 doi:10.2136/sssaj1980.03615995004400050002x: closed-form retention `θ(ψ)` and Mualem-based unsaturated hydraulic conductivity `K(θ)` with parameters α, n, θr, θs, Ks
- Šimůnek et al. HYDRUS-1D: validation target

**Functional requirements:**

- Mixed-form Richards PDE: `dθ/dt − d/dz[K(ψ)(dψ/dz + 1)] + S(z,t) = 0`
- van Genuchten retention: `Se = [1 + |αψ|ⁿ]^(−m)`, m = 1 − 1/n; K(Se) via Mualem-van Genuchten
- Modified Picard iteration with convergence criterion `||Δψ||∞ < 1e-3 m`; lumped (diagonal) mass matrix
- 1-D vertical domain per zone, 10–50 layers; root-distribution sink `S(z,t)` from FAO-56 ETc_adj
- Upper boundary: net irrigation or rain flux from FAO-56; lower boundary: free drainage or fixed head
- Outputs: soil moisture profile `θ(z,t)`, root-zone depletion Dr, bottom-flux (deep percolation), wetting front depth
- Validation against HYDRUS-1D on published test problems

**Live parameters (A0):** α, n, θr, θs, Ks (van Genuchten) per zone; root distribution function coefficients.

### 5.5 Reference ET & Crop Water — FAO-56 (fao56.py)

**Algorithm:** FAO Penman-Monteith ET₀; dual crop coefficient (Kcb + Ke); root-zone water balance.

**Technology:** Python 3.11 with NumPy. This is a daily-balance calculation — Python performance is adequate. For the edge controller, the FAO-56 core is re-implemented as a **C function** called from the edge decision runtime (≈ 200 lines of arithmetic, no matrix ops).

**Mathematical reference:**
- Allen, Pereira, Raes & Smith (1998) FAO Irrigation & Drainage Paper 56 https://www.fao.org/4/x0490e/x0490e00.htm: **the global standard** — Penman-Monteith ET₀ equation, dual crop coefficient (Kcb + Ke), soil-evaporation balance (Kr, few, Kcmax), water-stress coefficient Ks, root-zone water balance (TAW, RAW, MAD). Read chapters 2–4 and 6–8.
- ASCE-EWRI (2005) doi:10.1061/9780784408056: standardized form with fixed Cn/Cd constants for grass (ETos) and alfalfa (ETrs); removes inter-regional ambiguity; our canonical ET₀ mode
- Thorp (2022) pyfao56 *SoftwareX*: independent Python implementation for cross-check
- NASA POWER ETo validation (*Agronomy* 2021, 11(10), 2077): validates POWER-derived ET₀ against station data — our default radiation gap-fill

**Functional requirements (existing + extensions):**

- Penman-Monteith ET₀: ASCE-EWRI standardized form (grass reference, Cn=900, Cd=0.34) and alfalfa reference (Cn=1600, Cd=0.38)
- Dual crop coefficient: Kcb from crop-stage lookup; Ke from daily soil-evaporation balance
- ETc = (Kcb + Ke)·ET₀; ETc_adj = (Ks·Kcb + Ke)·ET₀
- Root-zone water balance: daily Dr update from P, RO, irrigation I, CR, ETc, DP
- Ks = (TAW − Dr)/((1−p)·TAW) for Dr > RAW; Ks = 1 for Dr ≤ RAW
- Net irrigation requirement: net depth = Dr − RAW (trigger); gross depth includes application efficiency
- Emitter design flow: gross depth × zone area / (runtime hours)
- Multi-crop support: crop catalogue (coconut, paddy, banana, vegetables) with GDD-based stage advancement (Palakkad climate priors)
- Salinity stress multiplier: Maas & Hoffman (1977) threshold-slope model `Yr = 1 − s(ECe − ECthreshold)` as additive yield-stress factor

**Live parameters (A0):** Kcb, Ke parameters (Kr, few, Kcmax), p (MAD fraction), TAW/RAW, ET₀ input bias offsets per weather source.

---

## 6. Post-Processing — FarmTwin Studio Output

**Technology:** Python 3.11 (postprocess.py) + ReportLab (PDF generation) + Matplotlib (embedded charts). BoM export via a JSON→PDF pipeline. WhatsApp share via Twilio or the official WhatsApp Business API.

**Functional requirements:**

- Network results table: node pressures (m head, kPa), link flows (L/h, m³/h), velocities (m/s)
- Emitter summary: discharge per emitter, EU (emission uniformity), DU(lq) (distribution uniformity low-quarter), CV (coefficient of variation); flag zones below EU 85%
- Pump duty report: operating Q and H, HP, wire-to-water efficiency, motor sizing recommendation (matched to standard Indian motor frames: 1, 1.5, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 50 HP)
- Lateral pressure profile chart: inlet vs end pressure variation with distance (PNG embedded in PDF)
- Bill of Materials (BoM): pipe by diameter and length (rounded up to stock lengths), fittings by type and count, emitters by type and count, pumps, valves, sensors, edge controller, solar panels; unit prices from a catalogue JSON (updatable); total capital cost
- Crop water and yield forecast: seasonal ETc by month, gross irrigation requirement, expected yield vs rainfed baseline (FAO-33 Ky model)
- Design comparison report (top 3 NSGA-II Pareto designs): side-by-side cost/EU/yield table with recommendation reasoning
- Export formats: PDF (print-ready A4), JSON (as-built hand-off to Runtime), CSV (for FPO record-keeping)

---

## 7. Runtime — FarmTwin Runtime

### 7.1 Edge Decision Engine (edge/)

**Technology:** **C++ 17** executable on Raspberry Pi 4 / CM4 or equivalent ARM SBC running Debian/Raspbian. C++ chosen over Python for deterministic real-time control loop, low latency on sensor data ingest, and embeddability on ARM without full CPython. Links against the C solver core (`libkrishiflow.so`) and the C FAO-56 module.

**Functional requirements:**

- Irrigation trigger: `Dr ≥ MAD × TAW` AND forecast rain < threshold within 48 h horizon AND inside allowed irrigation window AND source available (sump level / inlet pressure OK)
- Duration: `t = d_net × zone_area / (system_Q from GGA) / efficiency`; close-loop override on soil-moisture sensor reading up to field capacity; cap to prevent deep percolation
- Zone sequencing: limited by pump capacity (max simultaneous zones from GGA solver); pump↔valve interlock ordering (open zone valve before pump start; stop pump before closing last valve)
- All sensor inputs pass B6 QC gate before use; on missing/failed critical inputs, engine fails safe (hold or conservative schedule) — never actuates on bad data
- Operates fully offline from cached weather and last-known parameters during cloud connectivity gap; reconciles with cloud on reconnection
- Logs all actuation events (timestamp, zone, duration, trigger reason, actual vs planned) to local SQLite; syncs to cloud
- OTA firmware updates received from cloud over MQTT; applied at next maintenance window

### 7.2 Fertigation Control (control/)

**Technology:** **C** firmware on STM32 or ESP32 microcontroller (fertigation node); communicates with edge controller via LoRa. PID loop runs at 1 Hz.

**Functional requirements:**

- Target EC and pH per crop stage from agronomy nutrient plan
- PID + feed-forward control: dose rate = Kp·ΔEC + Ki·∫ΔEC dt + Kd·dEC/dt + feed-forward from flow meter (proportional dosing: dose tracks flow)
- Multi-channel injection: up to 4 nutrient tanks (N, P, K, acid) with individual dosing pumps (peristaltic or diaphragm)
- Safety interlocks: inject only when irrigation flow > threshold (no-flow lockout); EC-high cutoff; pH outside window cutoff; end-of-cycle clean-water flush (60 s); stock-tank-empty detection; backflow prevention valve
- Inline sensors: EC and pH downstream of mixing point; mainline flow meter; readings pass QC gate
- All dosing events logged; parameters (PID tunings, EC/pH setpoints) are live (A0)

---

## 8. IoT & Edge Control Layer

### 8.1 Wireless Network

**Technology:** LoRa/LoRaWAN IN865 (865–867 MHz India ISM band, license-free per TEC/WPC) — star topology with private LoRaWAN gateway at farm. 500 m field radius trivially covered; penetrates coconut/banana canopy.

**Functional requirements:**

- Field sensor nodes: soil moisture (capacitive, 3-zone depth), AWS (temperature, RH, wind, rain gauge), inline flow meters (magnetic or ultrasonic), pressure transducers, water-level sensors (sump/open channel), EC/pH probes
- Valve RTU nodes: ESP32 or STM32 + LoRa + H-bridge for DC latching solenoid valves (near-zero idle power); optional local pressure/flow sensing; solar + LiFePO4; IP65
- Edge gateway/ICU: Raspberry Pi CM4 + LoRa concentrator (SX1302 or SX1303) + 4G/NB-IoT cellular backhaul; runs edge decision engine; MQTT broker (Mosquitto); LoRaWAN network server (ChirpStack self-hosted)
- Pump/motor controller: Modbus-RTU VFD for 1–50 HP motors or DOL starter with contactor; dry-run protection (sump-level interlock); thermal overload; phase-failure relay; Modbus register map aligns with components.py motor sizing
- Acknowledged LoRa commands with 3× retry + last-safe-state failover on link loss; hardware watchdog on every node

**Reference standards:** LoRaWAN 1.0.4 Regional Parameters IN865 (LoRa Alliance); OASIS MQTT 5.0; Eclipse Sparkplug B (device birth/death certificates, birth-payload self-description); W3C Web of Things Thing Description; CoAP RFC 7252 (constrained fallback).

### 8.2 Device Onboarding (Plug-and-Play)

**Functional requirements:**

- Each node carries a LoRaWAN DevEUI + AppKey printed as a QR code on its label
- Installation person scans QR code in the commissioning app → sends OTAA join credentials to gateway → node joins network → publishes Sparkplug B BIRTH payload (sensor types, units, ranges, sample rate)
- Cloud registry auto-creates device shadow (desired vs reported) and maps declared metrics to canonical variable names (semantic interop ontology: e.g., any soil-moisture brand maps to `theta_vwc`)
- Declared ranges feed the B6 QC gate automatically (no per-device QC configuration)

### 8.3 Solar Energy Budget

- Sensor/valve nodes: 6 W PV + 10 Ah LiFePO4 + MPPT; MCU in deep-sleep between 15-min sample cycles; DC latching solenoids (zero holding power); 5-day monsoon autonomy at nominal load
- Gateway: 20 W PV + 40 Ah LiFePO4 or mains co-located with pump; never duty-cycled (always-on edge controller)
- Low-battery telemetry surfaced as a B6 health signal; alert pushed to installation person WhatsApp

---

## 9. Data Assimilation & Digital Twin Layer

### 9.1 Assimilation Algorithm

**Technology:** Python 3.11 with NumPy for EKF (linear-ish) and EnKF (nonlinear, large ensemble). The assimilation loop runs on the cloud server (not the edge), triggered every 15 minutes on arriving sensor batches.

**Mathematical reference:**
- Evensen (2003) *Ocean Dynamics* 53:343-367 doi:10.1007/s10236-003-0036-9: comprehensive EnKF theory + implementation — analysis scheme in ensemble space, nonlinear measurement handling, model-error/bias treatment, subroutine listings. **Primary reference for the twin variant when nonlinearity is strong (Richards + soil parameters)**
- EnKF for water distribution networks with PDD (2024) *Water Resour. Manage.* doi:10.1007/s11269-024-03809-9: demonstrates multi-step EnKF assimilation of pressure/flow in water networks with pressure-dependent demand and parameter estimation — closest published use case to FarmTwin's hydraulic twin
- Kalman (1960) *J. Basic Eng.* 82(1):35-45: original linear Kalman filter — basis for EKF used in the hydraulic network twin where linearization is acceptable

**Functional requirements:**

- EKF for hydraulic network twin: augmented state = [Q, H, emitter_k, pipe_C, pump_curve_coeffs]; linearize GGA Jacobian from solver; update on each pressure/flow sensor arrival
- EnKF for soil twin: ensemble of Richards model runs (N=50 default); update on each soil-moisture sensor reading; parameter state includes van Genuchten α, n, Ks per zone
- Data guard: only QC-passed sensor data (B6 flags = PASS) enters the assimilation; suspect data excluded; fail data rejected and alarm raised
- Parameter promotion: estimated parameters that pass a confidence check (uncertainty σ < threshold AND stable for > 7 days) are promoted to the shared core as updated priors, with governance log entry
- Twin state logged to time-series database (TimescaleDB or InfluxDB); queryable for retrospective analysis

### 9.2 Data Quality (quality/qc.py)

**Technology:** Python 3.11; can import `ioos_qc` package directly.

**Mathematical reference:**
- IOOS QARTOD real-time QC manuals https://ioos.noaa.gov/project/qartod/: gross-range, spike/rate-of-change, flatline, and climatology tests with PASS/SUSPECT/FAIL flags — the authoritative framework
- ioos_qc Python package https://ioos.github.io/ioos_qc/: direct reuse possible for standard tests
- Hampel (1974) *JASA* 69(346):383-393 doi:10.1080/01621459.1974.10482962: Hampel filter (rolling median ± k·MAD) for robust outlier detection — used because mean/σ tests are skewed by the outliers they are meant to detect

**B6 QC gate — required checks on every ingest:**

1. Gross-range check: value within declared sensor min/max (from device self-description)
2. Climatological range check: value within historical percentile bounds for date/time
3. Spike check: |value − previous| > threshold (per-sensor type)
4. Rate-of-change check: |Δvalue/Δt| > max_rate
5. Flatline check: sensor stuck at same value for > N consecutive readings
6. Hampel outlier check: rolling median ± 3·MAD window

All six must pass for PASS flag. Any failure → SUSPECT or FAIL; FAIL data excluded from all downstream uses.

---

## 10. Weather Data Integration

**Technology:** Python 3.11 async HTTP client (httpx). Source precedence managed in weather/ module with automatic fallback cascade.

**Source precedence (highest to lowest priority):**

1. On-farm AWS (Campbell Scientific or Davis instruments) — real-time, highest spatial accuracy
2. Nearby IMD AWS station (within 10 km) — real-time via IMD API
3. Open-Meteo ERA5 reanalysis + forecast https://open-meteo.com/en/docs — free, no API key, CC BY 4.0; hourly T, RH, wind, radiation, soil; self-hostable for offline use
4. NASA POWER reanalysis https://power.larc.nasa.gov/docs/ — free global daily T, RH, wind, solar radiation, precipitation for agriculture community; default radiation gap-fill and historical climate source

**Reference:**
- NASA POWER ETo validation (*Agronomy* 2021, 11(10), 2077 https://www.mdpi.com/2073-4395/11/10/2077): validates POWER-derived ET₀ against station measurements across tropical/subtropical Asia

**Functional requirements:**

- Hourly fetch from primary source; 6-hour fetch from fallback sources
- Missing variables filled in order of the precedence cascade
- Each weather variable carries a `source_tag` and `quality_flag` passed to FAO-56 inputs
- ET₀ input bias offsets (A0 live parameters) correct systematic differences between sources
- 5-day forecast used by edge decision engine for rain prediction in irrigation trigger logic
- Historical weather archive (ERA5, 30+ years) used by Studio for design-climate statistics (P-exceedance irrigation requirement)

---

## 11. Component CFD (Offline)

**Technology:** OpenFOAM 10+ (FVM, RANS k-ε/RSM or LES); ParaView for post-processing; CalculiX or deal.II for structural (FSI); preCICE coupler for OpenFOAM↔structure coupling. Runs on HPC cluster (IIT Palakkad collaboration) or cloud HPC (AWS ParallelCluster). Results cached as JSON K-library and emitter curve catalogue consumed by components.py / emitters.py.

**Mathematical reference:**
- Li et al. (2008) *Irrig. Sci.* 26(5) doi:10.1007/s00271-008-0108-1: 3-D CFD of drip-emitter labyrinth channels with particle tracking; derives `q = k H^x` emitter curve and anti-clogging wall-shear maps
- Lequette et al. (2024): SKE/RSM/LES comparison for labyrinth emitter channels — guides turbulence model selection
- "Performance of Emitters... CFD" (*Water* 2025, 17(5), 689): recent 2025 study on emitter CFD methodology
- PC-emitter diaphragm FSI (*Irrig. & Drain.* doi:10.1002/ird.2601): fluid-structure interaction for pressure-compensating diaphragm deformation
- ISO 9261:2004: emitter discharge classification and field test protocol (validation standard)

**Functional requirements:**

- Emitter labyrinth CFD: derive k and x exponent for `q = k H^x`; turbulent dissipation map; anti-clog index (wall shear vs particle size)
- Venturi injector CFD: pressure loss dP(Q) and suction flow vs differential pressure at mainline
- Tee/manifold CFD: K-value table for branch/run configurations at relevant velocity ranges
- PC emitter FSI: diaphragm deformation vs inlet pressure → piecewise-linear q-P curve for PC band
- All CFD runs are offline and periodic (not per-design); outputs versioned in the K-library JSON; consumed as cached inputs by components.py/emitters.py at solve time

---

## 12. Design Optimization

**Algorithm:** NSGA-II (Non-dominated Sorting Genetic Algorithm II); multi-objective evolutionary; elitism + crowding distance; constraint handling.

**Technology:** Python 3.11 with pymoo library (canonical NSGA-II implementation). Each candidate evaluation calls the C GGA solver + Python FAO-56 + agronomy yield model. Parallel candidate evaluation with Python multiprocessing (one process per CPU core).

**Mathematical reference:**
- Deb, Pratap, Agarwal & Meyarivan (2002) *IEEE Trans. Evol. Comput.* 6(2):182-197 doi:10.1109/4235.996017: NSGA-II — fast non-dominated sorting O(MN²), crowding-distance diversity, elitism, constraint handling. **Primary algorithm reference.**
- Savic & Walters (1997) *J. Water Resour. Plan. Manage.* 123(2): GANET least-cost pipe-network design with GA — single-objective baseline the multi-objective optimizer generalizes
- Deb (2001) *Multi-Objective Optimization using Evolutionary Algorithms* (Wiley): extended treatment for constraint-handling and decision-variable encoding

**Functional requirements:**

- Decision variables: pipe diameter selection (discrete, from catalogue) per link; pump model selection (discrete catalogue); emitter type and spacing per zone; zone on/off sequencing
- Objective functions (simultaneously minimized/maximized):
  - Total capital cost (BoM cost from catalogue prices)
  - Distribution uniformity DU(lq) (maximized; penalize < 85%)
  - Estimated seasonal yield (from FAO-33 Ky model; maximized)
  - Energy consumption kWh/season (pump operating point × hours; minimized)
- Constraints: pressure at all emitters within [10, 400] kPa; velocity in all pipes within [0.3, 2.0] m/s; pump within Q-H operating range; all demands satisfied
- NSGA-II parameters: population N = 100, generations = 200, crossover probability = 0.9, mutation probability = 1/n_variables; tournament selection
- Output: top 3 Pareto-front designs, ranked by a weighted scalar for farmer-facing display (cost weight 0.4, yield 0.4, EU 0.2, user-adjustable)
- Each candidate evaluation < 500 ms (C solver + Python agronomy); full NSGA-II run < 60 s on 8-core server

---

## 13. Agronomy Layer

**Technology:** Python 3.11 (agronomy/ package). Crop catalogue as JSON. Yield model and nutrient plan as pure-Python functions.

### 13.1 Yield Model

**Mathematical reference:**
- Doorenbos & Kassam (1979) FAO-33 / FAO-66 (2012) https://www.fao.org/4/i2800e/i2800e.pdf: water-production function `(1 − Ya/Ym) = Ky·(1 − ETa/ETc)` — lightweight real-time yield estimate; Ky values per crop and growth stage
- Steduto, Hsiao, Raes & Fereres (2009) *Agronomy Journal* 101(3):426-437 doi:10.2134/agronj2008.0139s: AquaCrop — transpiration→biomass via normalized water-productivity; used offline to calibrate the lightweight FAO-33 Ky parameters and harvest index
- Maas & Hoffman (1977) *J. Irrig. Drain. Div.* ASCE 103(IR2): crop salt tolerance threshold-slope model `Yr = 1 − s(ECe − ECthreshold)` — yield-stress multiplier for saline groundwater (Palakkad rain-shadow belt context)

**Functional requirements:**

- Real-time yield tracking: `Ya/Ym = 1 − Ky·(1 − ETa/ETc)` updated daily; Ky applied per growth stage
- AquaCrop offline calibration: run AquaCrop for local crop × climate to derive Ky and WP* priors for the real-time model
- Salinity stress: `Yr = 1 − s·max(0, ECe − ECt)` applied as multiplier on Ya/Ym
- Yield recording: end-of-season actual yield entered by farmer (or FPO); stored in crop log; used to calibrate Ky via the twin parameter estimation loop
- Crop catalogue: coconut, paddy (kharif/rabi), banana (Nendran), vegetables (tomato, okra, capsicum); GDD-based stage boundaries; Kcb, Ky, ECt, root depth, p (MAD) per stage; expandable by agronomist

### 13.2 Nutrient Plan (Fertigation)

**Functional requirements:**

- N-P-K dosing schedule per crop, growth stage, and yield target (from Kerala Agricultural University recommendations for Palakkad district)
- EC setpoint per stage derived from total dissolved nutrients
- pH target: 5.5–6.5 (slightly acidic, optimal for drip fertigation)
- Output: daily dose (g/m²) per nutrient tank; translated to stock-solution concentration and injection rate at prevailing flow
- Fertiliser compatibility checker: flag incompatible combinations before dosing (e.g., calcium nitrate + phosphates)

---

## 14. Cloud & Dashboard

**Technology:** FastAPI (Python 3.11) backend; PostgreSQL + TimescaleDB for time-series; React + Tailwind CSS for the farmer PWA; WhatsApp Business API (Meta) for push alerts; Firebase Cloud Messaging (FCM) for in-app push; AWS or Hetzner cloud hosting.

**Farmer PWA functional requirements:**

- Home screen (above the fold on a 5-inch phone):
  - Farm status line: "Irrigating Zone 2 — 40 min remaining" or "All off — Next: Tue 06:00"
  - Soil moisture bars per zone (3 levels: dry / adequate / saturated; colour-coded)
  - Last alert with timestamp
  - One-tap override: "Irrigate Now" or "Pause 24h"
- Trend charts: soil moisture 7-day, ET₀ vs ETc weekly, fertiliser dose history — swipe-accessible, not home screen
- Yield tracker: current season progress bar (% of target yield based on ETa/ETc)
- Alert preferences: set allowed irrigation window (e.g., 04:00–07:00); set WhatsApp phone number; toggle voice alerts
- Multi-language: Malayalam (primary) and English; date/time in local format

**Installation person PWA functional requirements:**

- Commissioning checklist with QR-scan node registration
- Live pre-flight view: pressure map and flow readings during pre-delivery test
- Network diagram: pipe layout on satellite map base, colour-coded by pressure
- BoM export and share

---

## 15. Technology Stack Summary

| Layer | Component | Technology | Rationale |
|---|---|---|---|
| Pre-processing | Farm survey app | React Native + Mapbox GL | Offline maps, GPS, cross-platform tablet |
| Pre-processing | Network pre-processor | Python 3.11 | Rapid prototyping; preprocess.py already exists |
| Pre-processing | Component library | Python 3.11 | Same |
| Solver — GGA | Core solver | **C** (libkrishiflow.so) | Performance on RPi edge; SuiteSparse CHOLMOD |
| Solver — MOC | Transient | **C** (standalone lib) | Explicit time march; deterministic timing |
| Solver — Surface | Zero-inertia Saint-Venant | **C** (standalone lib) | Tight advance/recession loops |
| Solver — Richards | Soil water | **C** (standalone lib) | Tridiagonal solves; real-time twin loop |
| Solver — FAO-56 | ET & crop water | Python 3.11 + C (edge) | Python for Studio; C for edge runtime |
| Optimization | NSGA-II | Python 3.11 + pymoo | Mature library; parallel eval via multiprocessing |
| Component CFD | Offline emitter/fitting CFD | OpenFOAM 10+ | Industry-standard FVM; open source; HPC-ready |
| Component CFD | FSI (PC emitter) | OpenFOAM + CalculiX + preCICE | Standard FSI coupling stack |
| Edge runtime | Decision engine | **C++ 17** (ARM SBC) | Deterministic real-time; links C solver lib |
| Edge runtime | Fertigation PID | **C** (STM32/ESP32 firmware) | Hard real-time on MCU |
| IoT | Field-to-gateway wireless | LoRa/LoRaWAN IN865 | Long range, solar-compatible, India-licensed |
| IoT | Gateway/broker | ChirpStack + Mosquitto (MQTT) | Self-hosted LoRaWAN NS; open source |
| IoT | Cloud messaging | MQTT over TLS (4G/NB-IoT) | Standard; OASIS MQTT 5.0 |
| IoT | Device self-description | Eclipse Sparkplug B + W3C WoT TD | Plug-and-play onboarding |
| Data assimilation | Hydraulic twin (EKF) | Python 3.11 + NumPy | Cloud-side; not latency-critical |
| Data assimilation | Soil twin (EnKF) | Python 3.11 + NumPy | Cloud-side; ensemble N=50 |
| Data quality | QC gate (B6) | Python 3.11 + ioos_qc | QARTOD-aligned; reusable library |
| Time-series DB | Sensor + twin state | TimescaleDB (PostgreSQL ext) | SQL + time-series; open source |
| Cloud API | Backend | FastAPI (Python 3.11) | Async; OpenAPI docs auto-generated |
| Farmer UI | Mobile PWA | React + Tailwind CSS | Offline-capable; lightweight |
| Farmer alerts | Push notifications | WhatsApp Business API + FCM | WhatsApp is primary rural channel in Kerala |

---

## 16. Non-Functional Requirements

### 16.1 Performance

| Scenario | Target |
|---|---|
| GGA solve, 500-node network, Studio (Python+C) | < 2 s |
| GGA solve, 500-node network, edge (C, RPi 4) | < 50 ms |
| NSGA-II full run, 100 population × 200 generations | < 60 s (8-core server) |
| FAO-56 daily balance, 20 zones | < 10 ms (C on RPi 4) |
| EnKF update, N=50, 20 soil zones | < 30 s (cloud server) |
| LoRa sensor-to-edge latency | < 5 s |
| Edge-to-cloud sync (MQTT, 4G) | < 10 s |
| Farmer PWA home screen load (4G) | < 2 s |

### 16.2 Reliability & Availability

- Edge controller: operates fully offline for ≥ 30 days without cloud connectivity; local cache covers 30-day weather history and parameter set
- Sensor node: ≥ 5-day solar autonomy during monsoon overcast conditions
- Cloud API: 99.5% uptime target; rolling deployments with zero downtime
- Data loss: no sensor reading lost on connectivity gap; store-and-forward at gateway

### 16.3 Security

- LoRaWAN: per-device AES-128 OTAA session keys; replay protection
- MQTT: TLS 1.3; per-device client certificates
- Cloud API: JWT authentication; role-based access (farmer / installer / agronomist / admin)
- OTA firmware: signed binary verification before flash
- No plaintext credentials in firmware or config files

### 16.4 Internationalisation

- UI languages: Malayalam (primary), English (secondary); i18n via i18next
- Date/time: IST (UTC+5:30); all internal timestamps in UTC
- Units: metric throughout; farmer-facing display uses familiar units (litre, metre, kg, rupee)

### 16.5 Accessibility

- Farmer PWA: WCAG 2.1 AA; minimum touch target 48×48 px; colour-blind-safe palette (avoid red/green without shape coding); voice alert option in Malayalam

---

## 17. Reference White Papers

Listed by solver/module. **[ESSENTIAL]** = must read before coding the module.

### Network Hydraulic Solver

- **[ESSENTIAL]** Todini, E. & Pilati, S. (1988). "A gradient algorithm for the analysis of pipe networks." In *Computer Applications in Water Supply* vol. 1. Research Studies Press. https://www.scirp.org/reference/referencespapers?referenceid=990969
- **[ESSENTIAL]** Todini, E. & Rossman, L.A. (2013). "Unified framework for the analysis of hydraulic networks." *J. Hydraul. Eng.* ASCE. + Rossman, L.A. (2000). EPANET 2 Users Manual. USEPA. https://www.epa.gov/water-research/epanet
- **[ESSENTIAL]** Elhay, S. & Simpson, A.R. (2011). "An alternative formulation of the penalty method for pipe networks." *J. Hydraul. Eng.* doi:10.1061/(ASCE)HY.1943-7900.0000411 [zero-flow regularization]
- **[SUPPORTING]** Giustolisi, O. & Todini, E. (2010). "Pipe hydraulic resistance correction in WDN analysis." *J. Hydroinformatics.* doi:10.2166/hydro.2010.164 [extended-period / tank GGA]

### Transient Solver

- **[ESSENTIAL]** Wylie, E.B. & Streeter, V.L. (1993). *Fluid Transients in Systems.* Prentice Hall. [MOC, device equations, Courant condition]
- **[ESSENTIAL]** Chaudhry, M.H. *Applied Hydraulic Transients.* Springer. [practical implementation]
- **[SUPPORTING]** Urbanowicz, K. et al. (2021). "Numerical Approaches to Water Hammer Modelling." *Water* 13(11):1597. https://www.mdpi.com/2073-4441/13/11/1597 [MOC vs FDM vs FVM; Brunone unsteady friction]

### Surface Irrigation Solver

- **[ESSENTIAL]** Strelkoff, T. & Katopodes, N.D. (1977). "Border irrigation hydraulics with zero inertia." *J. Irrig. Drain. Div.* ASCE 103(IR3):257-269. [zero-inertia justification]
- **[ESSENTIAL]** Bautista, E., Clemmens, A.J., Strelkoff, T.S. & Schlegel, J. (2009). "Modern analysis of surface irrigation systems with WinSRFR." *Agric. Water Manage.* 96(7). doi:10.1016/j.agwat.2009.03.007 [WinSRFR reference design]
- **[SUPPORTING]** Bautista, E. et al. SRFR 5. doi:10.1061/(ASCE)IR.1943-4774.0000938 [updated engine, computational-incident handling]

### Soil Water Solver

- **[ESSENTIAL]** Celia, M.A., Bouloutas, E.T. & Zarba, R.L. (1990). "A general mass-conservative numerical solution for the unsaturated flow equation." *Water Resour. Res.* 26(7):1483-1496. doi:10.1029/WR026i007p01483 [Modified Picard, mixed form — the key reference]
- **[ESSENTIAL]** van Genuchten, M.Th. (1980). "A closed-form equation for predicting the hydraulic conductivity of unsaturated soils." *SSSAJ* 44(5):892-898. doi:10.2136/sssaj1980.03615995004400050002x [retention and conductivity functions]

### Reference ET & Crop Water

- **[ESSENTIAL]** Allen, R.G., Pereira, L.S., Raes, D. & Smith, M. (1998). *Crop evapotranspiration: Guidelines for computing crop water requirements.* FAO Irrigation & Drainage Paper 56. https://www.fao.org/4/x0490e/x0490e00.htm
- **[ESSENTIAL]** ASCE-EWRI (2005). *The ASCE Standardized Reference Evapotranspiration Equation.* doi:10.1061/9780784408056
- **[SUPPORTING]** Thorp, K.R. (2022). "pyfao56: FAO-56 evapotranspiration in Python." *SoftwareX* 19:101208. [independent cross-check implementation]
- **[SUPPORTING]** Peng, L. et al. (2021). "Evaluation of NASA POWER for Estimating Daily Global Solar Radiation and Reference Evapotranspiration." *Agronomy* 11(10):2077. https://www.mdpi.com/2073-4395/11/10/2077

### Yield & Agronomy

- **[ESSENTIAL]** Doorenbos, J. & Kassam, A.H. (1979). *Yield Response to Water.* FAO Irrigation & Drainage Paper 33. Successor: FAO-66 (2012). https://www.fao.org/4/i2800e/i2800e.pdf
- **[SUPPORTING]** Steduto, P., Hsiao, T.C., Raes, D. & Fereres, E. (2009). "AquaCrop — the FAO crop model." *Agronomy Journal* 101(3):426-437. doi:10.2134/agronj2008.0139s
- **[SUPPORTING]** Maas, E.V. & Hoffman, G.J. (1977). "Crop salt tolerance — current assessment." *J. Irrig. Drain. Div.* ASCE 103(IR2).

### Design Optimization

- **[ESSENTIAL]** Deb, K., Pratap, A., Agarwal, S. & Meyarivan, T. (2002). "A fast and elitist multiobjective genetic algorithm: NSGA-II." *IEEE Trans. Evol. Comput.* 6(2):182-197. doi:10.1109/4235.996017 [primary algorithm]
- **[SUPPORTING]** Savic, D.A. & Walters, G.A. (1997). "Genetic algorithms for least-cost design of water distribution networks." *J. Water Resour. Plan. Manage.* 123(2). [single-objective baseline]

### Digital Twin / Data Assimilation

- **[ESSENTIAL]** Evensen, G. (2003). "The Ensemble Kalman Filter: theoretical formulation and practical implementation." *Ocean Dynamics* 53:343-367. doi:10.1007/s10236-003-0036-9
- **[SUPPORTING]** Kalman, R.E. (1960). "A new approach to linear filtering and prediction problems." *J. Basic Eng.* 82(1):35-45. [original EKF basis]
- **[SUPPORTING]** Karimanzira, D. et al. (2024). "EnKF for water distribution networks with pressure-dependent demand." *Water Resour. Manage.* doi:10.1007/s11269-024-03809-9 [closest published use case to hydraulic twin]

### Sensors & Data Quality

- **[ESSENTIAL]** IOOS QARTOD Real-Time QC Manuals. https://ioos.noaa.gov/project/qartod/ + ioos_qc Python. https://ioos.github.io/ioos_qc/ [B6 QC gate framework]
- **[SUPPORTING]** Hampel, F.R. (1974). "The influence curve and its role in robust estimation." *JASA* 69(346):383-393. doi:10.1080/01621459.1974.10482962 [Hampel filter, rolling MAD outlier]
- **[SUPPORTING]** Ostfeld, A. et al. (2008). "The battle of the water sensor networks." *J. Water Resour. Plan. Manage.* 134(6):556. doi:10.1061/(ASCE)0733-9496(2008)134:6(556) [sensor placement benchmark]

### Component CFD

- **[ESSENTIAL]** Li, Y. et al. (2008). "Computational fluid dynamics analysis of labyrinth emitter for drip irrigation." *Irrig. Sci.* 26(5). doi:10.1007/s00271-008-0108-1
- **[SUPPORTING]** "Performance of Emitters for Drip Irrigation... CFD Modelling." *Water* 2025, 17(5), 689. [latest 2025 CFD methodology]
- **[SUPPORTING]** PC-emitter diaphragm FSI. *Irrig. & Drain.* doi:10.1002/ird.2601
- **[SUPPORTING]** Lequette, L. et al. (2024). SKE/RSM/LES turbulence model comparison for labyrinth emitter channels. [recent model selection guidance]

### IoT & Edge Standards

- LoRaWAN 1.0.4 Regional Parameters IN865. LoRa Alliance. https://lora-alliance.org/resource_hub/
- OASIS MQTT v5.0. https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html
- Eclipse Sparkplug B. https://sparkplug.eclipse.org/
- W3C Web of Things Thing Description. https://www.w3.org/TR/wot-thing-description/
- CoAP RFC 7252. https://datatracker.ietf.org/doc/html/rfc7252

---

*End of requirements.md — version 1.0.0*
