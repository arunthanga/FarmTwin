# 22 — White Papers Needed for Implementation (summaries + links)

The key papers/standards an engineer should read **before coding each module**, each with
a short summary, what we implement from it, and a link. Grouped by module. This expands
the one-line entries in [16-annotated-bibliography.md](16-annotated-bibliography.md).

Legend: **[ESSENTIAL]** = read before writing the module · **[SUPPORTING]** = read for
robustness/extension.

---

## 1. Network hydraulic solver — `solver.py`, `headloss.py`

### [ESSENTIAL] Todini & Pilati (1988) — Global Gradient Algorithm
The original "gradient method for the solution of looped pipe networks." Formulates a
pipe network as coupled energy (head-loss per link) and continuity (mass at nodes)
equations, with unknowns being link flows `Q` and nodal heads `H`. Solves the nonlinear
system by Newton-Raphson, decomposed into a two-step update where the head sub-problem is
a sparse symmetric-positive-definite linear solve. This is the exact method EPANET uses
and that IRRICAD/IrriPro effectively implement. It is the mathematical backbone of
`solver.py`. We implement its `A11/A12/A21` matrix assembly, the `G` gradient diagonal,
and the iterative SPD solve. Reference (book chapter, no DOI):
https://www.scirp.org/reference/referencespapers?referenceid=990969

### [ESSENTIAL] Todini & Rossman (2013) / EPANET 2 manual — unified GGA + head-loss
Restates and unifies the GGA as used in EPANET 2.2, including head-loss formulas
(Hazen-Williams, Darcy-Weisbach with Swamee-Jain friction factor), minor losses, pumps
and valves as link types, and convergence criteria. This is the most practical
implementation reference and our validation target — we cross-check `solver.py` against
EPANET on the same `.inp`. EPANET official page:
https://www.epa.gov/water-research/epanet ; unsteady/extended GGA derivation:
https://doi.org/10.2166/hydro.2010.164

### [SUPPORTING] Elhay & Simpson (2011) — zero-flow regularization
Hazen-Williams head-loss has a singular derivative as `Q -> 0`, which makes the GGA
gradient matrix ill-conditioned and can stall convergence. This paper gives a clean
regularization that keeps the system invertible at near-zero flows (common in drip
laterals where many emitters carry tiny flows). We apply it in the head-loss gradient.
https://doi.org/10.1061/(ASCE)HY.1943-7900.0000411

---

## 2. Transients / water hammer — `transient.py` (planned)

### [ESSENTIAL] Wylie & Streeter — Fluid Transients in Systems (MOC)
The standard treatment of the Method of Characteristics: converting the hyperbolic
mass+momentum PDEs into ODEs along characteristic lines `dx/dt = ±a`, the C+/C-
compatibility equations, the Courant stability condition, and boundary-device equations
(valve closure, pump trip, surge protection). We implement MOC for `transient.py` to size
air/relief valves and pump-trip protection, and to justify the pump<->valve sequencing
interlocks in the controller. (Book; see also the open review below.)

### [SUPPORTING] "Numerical Approaches to Water Hammer Modelling" — Water (2021)
Open-access review comparing MOC vs FDM vs FVM for transient pipe flow, with guidance on
unsteady-friction (Brunone) corrections. Helps choose discretization and damping models.
https://www.mdpi.com/2073-4441/13/11/1597

---

## 3. Surface irrigation — `surface.py` (planned)

### [ESSENTIAL] Bautista, Clemmens, Strelkoff & Schlegel (2009) — WinSRFR
Describes the USDA WinSRFR architecture and the zero-inertia/unsteady 1-D surface-flow
engine (SRFR) for basin/border/furrow irrigation, coupled to infiltration. This is our
reference design and validation target for `surface.py`. The companion USDA WinSRFR user
manual documents the SRFR 5 engine, Kostiakov-Lewis and Green-Ampt infiltration, and the
volume-balance procedures we mirror. Paper: https://doi.org/10.1016/j.agwat.2009.03.007 ;
USDA manual: https://www.ars.usda.gov/ARSUserFiles/20200515/WinSRFR4_UserManual.pdf

### [SUPPORTING] Strelkoff & Katopodes (1977) — zero-inertia
The foundational paper deriving the zero-inertia simplification of the Saint-Venant
equations for border irrigation (valid at low Froude number — i.e., all practical
fields). It justifies dropping the acceleration terms we omit. *J. Irrig. Drain. Div.*
ASCE 103(IR3):257-269 (search ASCE Library).

---

## 4. Soil water — `richards.py` (planned)

### [ESSENTIAL] Celia, Bouloutas & Zarba (1990) — mass-conservative Richards
Shows that the head-based form of the Richards equation loses mass badly, while the
**mixed form** solved with a **Modified Picard** iteration and a **lumped (diagonal) time
matrix** conserves mass exactly at no extra cost, and yields smooth infiltration
profiles. This is the scheme `richards.py` must use — we follow its mixed-form
discretization for the root-zone soil-water twin. *WRR* 26(7):1483-1496.
https://doi.org/10.1029/WR026i007p01483

### [ESSENTIAL] van Genuchten (1980) — retention & conductivity
Provides the closed-form soil-water retention `theta(psi)` and the Mualem-based
unsaturated hydraulic conductivity `K(theta)` used inside Richards. We implement these
constitutive relations (parameters `alpha, n, theta_r, theta_s, Ks`) as live-calibrated
parameters. *SSSAJ* 44(5):892-898.
https://doi.org/10.2136/sssaj1980.03615995004400050002x

---

## 5. Reference ET & crop water — `fao56.py`

### [ESSENTIAL] Allen, Pereira, Raes & Smith (1998) — FAO-56
The global standard for crop water requirements: the FAO Penman-Monteith ET0 equation,
the single and dual crop-coefficient (`Kcb + Ke`) approach, the soil-evaporation balance
for `Ke`, the water-stress coefficient `Ks`, and the root-zone water balance (TAW, RAW,
MAD). Almost all of `fao56.py` derives from this paper. Read chapters 2-4 and 6-8.
Full text: https://www.fao.org/4/x0490e/x0490e00.htm

### [ESSENTIAL] ASCE-EWRI (2005) — Standardized Reference ET
Standardizes Penman-Monteith with fixed `Cn/Cd` constants for short (grass, ETos) and
tall (alfalfa, ETrs) references, removing ambiguity and enabling crop-coefficient
transfer between regions. We implement this as the canonical ET0 mode. doi:
https://doi.org/10.1061/9780784408056

---

## 6. Yield & agronomy — `agronomy/`

### [ESSENTIAL] Doorenbos & Kassam (1979) FAO-33 — yield response to water
Introduces the water-production function `(1 - Ya/Ym) = Ky (1 - ETa/ETc)` linking relative
yield loss to relative ET deficit via a crop-specific factor `Ky`. This is the
lightweight, real-time yield model in `agronomy/yield`. The modern, freely-available
successor (FAO-66, 2012) restates it and underpins AquaCrop. FAO-66 PDF (contains the
equation): https://www.fao.org/4/i2800e/i2800e.pdf

### [SUPPORTING] Steduto, Hsiao, Raes & Fereres (2009) — AquaCrop
The FAO canopy/biomass water-driven crop model: transpiration -> biomass via a
normalized water-productivity parameter, biomass -> yield via harvest index. We use it
**offline** to calibrate the lightweight FAO-33 model and crop parameters; too heavy for
the real-time loop. *Agronomy Journal* 101(3):426-437.
https://doi.org/10.2134/agronj2008.0139s

### [SUPPORTING] Maas & Hoffman (1977) — crop salt tolerance
The threshold-slope model `Yr = 1 - s (ECe - ECthreshold)` for yield loss under salinity,
which we add as a stress multiplier on the yield estimate (relevant for the saline/hard
groundwater common in the rain-shadow belt). *J. Irrig. Drain. Div.* ASCE 103(IR2).

---

## 7. Design optimization — `optimize.py` (planned)

### [ESSENTIAL] Deb, Pratap, Agarwal & Meyarivan (2002) — NSGA-II
The multi-objective evolutionary algorithm we use to search the design space and return a
Pareto front of trade-off designs. Gives fast non-dominated sorting (O(MN^2)), elitism,
and crowding-distance for diversity, plus constraint handling. We implement NSGA-II to
return the top 2-3 setups (least-cost / most-uniform / best-balanced). doi:
https://doi.org/10.1109/4235.996017 (open PDF:
https://www.cp.eng.chula.ac.th/~prabhas/teaching/ec/ec2010/nsga2-ieee-trans-ec-2002.pdf)

### [SUPPORTING] Savic & Walters (1997) — GANET least-cost design
Classic genetic-algorithm formulation of least-cost pipe-network design (discrete
diameter selection under pressure constraints), the single-objective baseline our
optimizer generalizes. *J. Water Resour. Plan. Manage.* 123(2).

---

## 8. Digital twin / data assimilation — `twin/assimilation.py` (planned)

### [ESSENTIAL] Evensen (2003) — Ensemble Kalman Filter
The comprehensive theory + practical implementation of the EnKF, including the analysis
scheme in ensemble space, handling of nonlinear measurements, and model-error/bias
treatment — with subroutine listings. Basis for our EnKF twin variant when nonlinearity
is strong. *Ocean Dynamics* 53:343-367.
https://doi.org/10.1007/s10236-003-0036-9 (PDF:
https://www.ecmwf.int/sites/default/files/elibrary/2003/9321-ensemble-kalman-filter-theoretical-formulation-and-practical-implementation.pdf)

### [SUPPORTING] EnKF for water distribution networks with PDD (2024)
Demonstrates multi-step EnKF assimilation of pressure/flow in water networks with
pressure-dependent demand and parameter (roughness/demand) estimation — close to our use
case. *Water Resour. Manage.* https://doi.org/10.1007/s11269-024-03809-9

---

## 9. Sensors, placement & data quality — `sensors/`, `quality/qc.py`

### [ESSENTIAL] IOOS QARTOD — real-time QC manuals (+ `ioos_qc` Python)
The authoritative framework for real-time data quality control: gross-range,
spike/rate-of-change, flatline, and climatology tests with pass/suspect/fail flags. We
model `quality/qc.py` on QARTOD and can reuse the open `ioos_qc` Python package directly.
Manuals: https://ioos.noaa.gov/project/qartod/ ; Python:
https://ioos.github.io/ioos_qc/

### [SUPPORTING] Hampel (1974) — robust outlier identifier
The influence-function basis for the Hampel filter (rolling median ± k·MAD), the robust
outlier test we use because mean/standard-deviation tests are themselves skewed by
outliers. *JASA* 69(346):383-393. https://doi.org/10.1080/01621459.1974.10482962

### [SUPPORTING] Ostfeld et al. (2008) — Battle of the Water Sensor Networks
The benchmark problem + datasets for sensor-placement algorithms; our `sensors/placement.py`
is evaluated against it. *J. Water Resour. Plan. Manage.* 134(6):556.
https://doi.org/10.1061/(ASCE)0733-9496(2008)134:6(556)

---

## 10. Weather data — `weather/`

### [ESSENTIAL] NASA POWER + "ETo from POWER" (Agronomy 2021)
NASA POWER provides free global daily T, RH, wind, **solar radiation** and precipitation
(AG community) suitable for FAO-56; the paper validates reference ETo computed from POWER
reanalysis. We use POWER as the default radiation gap-fill and historical climate source.
API docs: https://power.larc.nasa.gov/docs/ ; validation paper:
https://www.mdpi.com/2073-4395/11/10/2077

### [SUPPORTING] Open-Meteo API
Free (no-key, CC BY 4.0) forecast + ERA5 archive with hourly T, RH, wind, radiation and
soil variables; our default forecast feed and self-hostable for offline use.
https://open-meteo.com/en/docs

---

## 11. Component CFD (offline) — feeds `components.py`, `emitters.py`

### [SUPPORTING] Li et al. (2008) — emitter labyrinth CFD
3-D CFD of drip-emitter labyrinth channels with particle tracking to study flow,
energy dissipation and anti-clogging, and to derive the `q = k H^x` emitter curve. We run
such simulations **offline** (OpenFOAM) to populate the emitter/K-value library. *Irrig.
Sci.* 26(5). https://doi.org/10.1007/s00271-008-0108-1

---

## 12. Edge / IoT / control standards — `edge/`, `control/`, `cloud/`

These are specs/standards rather than papers; read the relevant sections before building
the device protocol and control firmware.

| Standard | Use | Link |
| --- | --- | --- |
| LoRaWAN Regional Parameters (IN865) | Field radio band + join | https://lora-alliance.org/resource_hub/ |
| OASIS MQTT v5 | Pub/sub messaging | https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html |
| Eclipse Sparkplug B | Device birth/death + state | https://sparkplug.eclipse.org/ |
| W3C Web of Things (Thing Description) | Device self-description | https://www.w3.org/TR/wot-thing-description/ |
| CoAP (RFC 7252) | Constrained REST alternative | https://datatracker.ietf.org/doc/html/rfc7252 |

---

## Reading order (fastest path to a build)

1. FAO-56 (Allen 1998) + ASCE-EWRI 2005 — already largely implemented; confirm.
2. Todini & Pilati (1988) + EPANET manual — the network solver.
3. FAO-33/FAO-66 + NSGA-II — agronomy yield + optimizer (Product 1 first).
4. QARTOD + Hampel — the QC guard (protects everything else).
5. Celia (1990) + van Genuchten (1980) — soil twin.
6. Evensen (2003) — assimilation.
7. WinSRFR (2009) and Wylie & Streeter — surface + transient (later phases).
