# 16 — Annotated Bibliography

Consolidated references, grouped by topic. Each entry: citation + 1-2 line summary +
where it fits in FarmTwin Engine. DOIs/links are given where stable.

## A. Pressurized network hydraulics (GGA) — [12 §A1](12-solver-mathematics.md)

- **Todini & Pilati (1988)** "A gradient algorithm for the analysis of pipe networks."
  The original Global Gradient Algorithm. *Our core network solver* (`solver.py`).
- **Todini & Rossman (2013)** *J. Hydraul. Eng.* — unified GGA framework. Reference
  formulation we follow.
- **Rossman (2000)** EPANET 2 Users Manual, US EPA. The open reference implementation;
  our validation target.
- **Elhay & Simpson (2011)** doi:10.1061/(ASCE)HY.1943-7900.0000411 — zero-flow
  singularity regularization for Hazen-Williams. *Robustness of the GGA near Q=0.*
- **Giustolisi & Todini (2010)** doi:10.2166/hydro.2010.164 — unsteady/extended-period
  GGA. *Tank/EPS extension.*

## B. Transients / water hammer (MOC) — [12 §A2](12-solver-mathematics.md)

- **Wylie & Streeter (1993)** *Fluid Transients in Systems.* Standard MOC text. *Basis of
  `transient.py`.*
- **Chaudhry** *Applied Hydraulic Transients.* Boundary devices, surge protection.
- **"Numerical Approaches to Water Hammer Modelling"** *Water* 2021, 13(11), 1597 — MOC
  vs FDM vs FVM trade-offs. *Method choice justification.*

## C. Surface irrigation (zero-inertia) — [12 §A3](12-solver-mathematics.md)

- **Strelkoff & Katopodes (1977)** *J. Irrig. Drain. Div.* 103(3) — zero-inertia border
  irrigation. *Governing simplification we adopt.*
- **Bautista, Clemmens, Strelkoff, Schlegel (2009)** WinSRFR, *Agric. Water Manage.*
  96(7), doi:10.1016/j.agwat.2009.03.007 — the reference product. *Validation target for
  `surface.py`.*
- **Bautista et al.** SRFR 5, doi:10.1061/(ASCE)IR.1943-4774.0000938 — computational
  incident handling.
- **Lyn & Goodwin (1987)** — Preissmann scheme stability.

## D. Soil water (Richards) — [12 §A4](12-solver-mathematics.md)

- **Richards (1931)** — the unsaturated-flow PDE.
- **Celia, Bouloutas & Zarba (1990)** *WRR* 26(7), doi:10.1029/WR026i007p01483 —
  mass-conservative mixed-form (Modified Picard). *The scheme `richards.py` must use.*
- **van Genuchten (1980)** *SSSAJ* — retention/conductivity model. *theta(psi), K(psi).*
- **Simunek et al.** HYDRUS — validation reference.

## E. Reference ET & crop water (FAO-56/ASCE) — [12 §A5](12-solver-mathematics.md)

- **Allen, Pereira, Raes & Smith (1998)** FAO Irrigation & Drainage Paper 56. *The ET0 +
  dual-Kc basis of `fao56.py`.*
- **ASCE-EWRI (2005)** Standardized Reference ET, doi:10.1061/9780784408056 —
  standardized constants.
- **Thorp (2022)** pyfao56, *SoftwareX* — open implementation to cross-check against.

## F. Component CFD — [12 §A6](12-solver-mathematics.md)

- **Li et al. (2008)** labyrinth CFD + particle tracking, *Irrig. Sci.* 26(5),
  doi:10.1007/s00271-008-0108-1 — emitter internal flow + anti-clog.
- **Lequette et al. (2024)** SKE/RSM/LES labyrinth comparison — turbulence-model choice.
- **"Performance of Emitters... CFD"** *Water* 2025, 17(5), 689 — emitter curve from CFD.
- **PC-emitter diaphragm FSI** *Irrig. & Drain.* doi:10.1002/ird.2601 — fluid-structure
  interaction for pressure-compensating emitters.
- **preCICE** — OpenFOAM-FEM coupling library for FSI.

## G. Design optimization — [20](20-design-optimization.md)

- **Savic & Walters (1997)** GANET least-cost pipe-network design, *JWRPM.* *GA baseline.*
- **Deb et al. (2002)** NSGA-II, *IEEE Trans. Evol. Comput.*, doi:10.1109/4235.996017.
  *Our multi-objective optimizer.*
- **Reca & Martinez (2006)** GESTAR genetic optimization of irrigation networks,
  *Comput. Electron. Agric.*
- **Keller & Karmeli (1974)** trickle-irrigation emitter design — uniformity basis.

## H. Sensors, placement & QA/QC — [13](13-sensors-and-instrumentation.md)

- **Perez et al. (2011)** leak isolation by pressure sensitivity, *Control Eng. Practice.*
- **Sarrate/Casillas/Puig** sensor placement (branch-and-bound + clustering),
  doi:10.2166/ws.2014.037.
- **Information-theory placement** *Sensors* 2022, 22(2), 443.
- **Ostfeld et al. (2008)** Battle of the Water Sensor Networks (BWSN), *JWRPM* —
  benchmark.
- **IOOS QARTOD** real-time QC manuals — pass/suspect/fail flag framework.
- **Hampel (1974)** robust outlier identifier (median + MAD).
- **WMO-No. 8** Guide to Instruments & Methods of Observation — QC + siting.
- **Branisavljevic, Prodanovic & Kapelan (2011)** sensor data validation in water
  systems, *Water Sci. Technol.* doi:10.2166/wst.2011.412.
- *Sci. Agric.* (2018) EM vs ultrasonic upstream-disturbance CFD,
  doi:10.1590/1678-992x-2018-0208.

## I. Digital twin / data assimilation — [14](14-digital-twin-data-assimilation.md)

- **Evensen (2003)** Ensemble Kalman Filter — formulation/practice.
- **Bar-Shalom et al. (2001)** *Estimation with Applications* — EKF + innovation gating.
- **3-EnKF-WDN** multi-step assimilation with PDD, *Water Resour. Manage.* (2024),
  doi:10.1007/s11269-024-03809-9.
- **EKF online state estimation in WDS** (state-space from 1-D Saint-Venant), NSF PAR
  10537042; **Corr-EKF** process-noise covariance, NSF PAR 10653477.
- **End-to-end DT with wireless pressure sensing** (Unalakleet), *ACS ES&T Water*,
  doi:10.1021/acsestwater.5c01515.

## J. Weather data — [17](17-weather-data-integration.md)

- **NASA POWER** API docs (power.larc.nasa.gov); daily ETo from POWER, *Agronomy* 2021,
  11(10), 2077 — free solar + met for FAO-56.
- **Open-Meteo** (open-meteo.com) — free forecast + ERA5 archive, CC BY 4.0.
- **OpenWeather AgroMonitoring** — satellite NDVI/soil API (paid).
- **IMD GKMS / Agromet-DSS / Meghdoot** — official India agromet.
- **Copernicus ERA5**; **NOAA GEFS** — reanalysis / ensemble forecast.

## K. Edge / IoT / control — [18](18-iot-control-architecture.md)

- **LoRaWAN 1.0.4 Regional Parameters (IN865)** — LoRa Alliance; India 865-867 MHz
  license-free (TEC/WPC).
- **OASIS MQTT 3.1.1 / v5**; **MQTT-SN** — pub/sub messaging.
- **Eclipse Sparkplug B** — state-aware device birth/death + payloads.
- **W3C Web of Things** (Thing Description) — device self-description.
- **CoAP (RFC 7252)**; **Matter/Thread** — IP-stack alternatives.
- Solar-powered LoRa WSN for agriculture (MDPI *Sensors*) — energy-harvesting node design.

## L. Agronomy & yield — [21](21-agronomy-layer.md)

- **Allen et al. (1998)** FAO-56 — Kc tables.
- **Doorenbos & Kassam (1979)** FAO-33 — yield response to water (Ky).
- **Steduto et al. (2012)** FAO-66 / AquaCrop — water-driven yield.
- **Maas & Hoffman (1977)** — crop salt tolerance (salinity-yield).
- **Jones et al. (2003)** DSSAT-CSM; **Holzworth et al. (2014)** APSIM — process crop
  models (offline calibration).
- **KAU Package of Practices** (Kerala) — local crop calendars, Kc, fertigation.

## M. IIT Palakkad — [15](15-iitpkd-collaboration-brief.md)

- **IROMS-C2D** river-ocean FV (Sridharan, Cea, Kuiry), zenodo.8128928.
- **Nithila Devi et al. (2020)** retention-storage urban flooding, *Water* 12(10), 2875.
- **Varghese & Mitra (2024)** ETo variability & ET paradox, doi:10.1007/s11269-024-03931.
- **Saminathan, Medina, Mitra, Tian (2021)** GEFS precipitation forecast, *J. Hydrology*
  598:126431.
