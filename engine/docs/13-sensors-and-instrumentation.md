# 13 — Sensors & Instrumentation (taxonomy, placement, QA/QC)

What we measure, with what device, where to put it, and how to keep bad data out. This
serves both products: the Design Studio ([20-...](20-design-optimization.md)) decides
*where* sensors go; the Runtime ([14-...](14-digital-twin-data-assimilation.md),
[18-...](18-iot-control-architecture.md)) reads them.

Contents: B1 device taxonomy · B2 placement engineering · B3 optimal sensor placement ·
B4 environmental instrumentation (AWS) · B5 pointer to weather data · B6 data-quality
guards.

---

## B1. Device taxonomy mapped to model variables

| Quantity | Device (accuracy) | Maps to model variable |
| --- | --- | --- |
| Flow | Electromagnetic magmeter (±0.2-1%, needs conductive water); transit-time ultrasonic (±2-5%, non-invasive) | link flow `Q` (mainline, zone valves) |
| Pressure | Pressure transducer (0-16 bar, ±0.3%) | nodal head `H`; filter dP (clog); pump discharge |
| Level | Sump/tank level (float/ultrasonic/pressure) | reservoir/tank boundary head |
| Soil moisture | TDR (±0.02 m3/m3, costly); FDR/capacitance (cheap, needs site calibration) | Richards/FAO-56 `theta` |
| Weather | On-farm AWS (T, RH, wind, radiation, rain) — see B4 | FAO-56 ET0 inputs |
| Fertigation | EC / pH probes at the mixing point | nutrient transport boundary (EC/pH targets) |
| Telemetry | Valve position, pump VFD status, power | control state / boundary conditions |

## B2. Placement engineering (hydraulics-driven)

Flow meters need straight, unobstructed runs — the **10D upstream / 5D downstream** rule
(magmeter or spool ultrasonic can reach ~3D/2D if lab-certified). Disturbances near
tees/valves/pumps bias readings 15-20%; air pockets zero out ultrasonic meters (install
air vents upstream). Specify per-device standoffs and an optional CFD-checked correction
factor.

Pressure transducers: at junctions of interest, both sides of filters (clog detection),
and pump discharge. Soil-moisture probes: in the root zone at representative
depths/zones, **site-calibrated** (a generic factory curve can be 2-3x off).

**Refs:** USU Extension "Accurate Irrigation Water Flow Measurement in Pipes"; UNL
ultrasonic flow-meter bias study; *Sci. Agric.* (2018) EM vs ultrasonic upstream-
disturbance CFD, doi:10.1590/1678-992x-2018-0208; soil-moisture systematic review,
*Agric. Water Manage.* (2023) S0378377423000136.

## B3. Optimal sensor placement (information-driven)

Where to put a budget-limited set of pressure/flow sensors so the twin is **observable**
and leaks/clogs are **localizable**:

- **Pressure-sensitivity matrix** `S` (dP at candidate nodes vs a leak/demand at each
  node); pick rows maximizing diagnosability/isolability.
- **Clustering** (k-means) + **branch-and-bound** on a structural model to choose a
  near-optimal subset under a count budget.
- **Information-theoretic** selection: maximize relevance, minimize mutual-information
  redundancy between chosen sensors.
- **Benchmark** against the Battle of the Water Sensor Networks (BWSN).

This runs in the Design Studio (it reuses the Jacobian the GGA already forms) so the
recommended design is twin-ready. **Module:** planned `sensors/placement.py`.

**Refs:** Perez et al. (2011) leak isolation by pressure sensitivity, *Control Eng.
Practice*; Sarrate/Casillas/Puig (branch-and-bound + clustering) doi:10.2166/ws.2014.037;
information-theory placement, *Sensors* 2022, 22(2), 443; Ostfeld et al. (2008) BWSN,
*JWRPM*.

## B4. Environmental instrumentation (Automatic Weather Station + agromet sensors)

A small on-farm **AWS** aggregates the meteorological instruments that drive FAO-56 and
the soil/crop twin. Each instrument and the model variable it feeds:

| Instrument | Measures | Feeds |
| --- | --- | --- |
| AWS datalogger / gateway | time-sync + upload | the agromet hub |
| Thermometer (shielded T/RH probe, PT100/SHT) | T_mean, T_min, T_max | ET0, Kc max, heat stress, GDD |
| Hygrometer | relative humidity -> e_a | ET0, leaf-wetness/disease risk |
| Anemometer + wind vane | wind speed (-> u2), direction | ET0 aerodynamic term; spray/drift advice |
| Pyranometer (solar radiation) / optional net radiometer | Rs -> Rn | ET0 energy term (dominant ET driver) |
| Rain gauge (tipping-bucket) | rainfall | effective precip in the water balance; rain skip |
| Soil-moisture sensor (TDR/FDR, multi-depth) | root-zone theta | Richards/FAO-56 state the twin assimilates |
| Leaf-wetness sensor | canopy wetness duration | disease / fertigation timing (auxiliary) |
| Optional: soil temperature, barometric pressure | soil T, atmospheric P | GDD soil, psychrometric constant |
| Optional: EC/pH at mixing point | fertigation water quality | nutrient control (B1) |

**Engineering to specify:** siting per WMO-No. 8 / FAO-56 (sensor height, radiation
shield, fetch), sampling/averaging windows, **solar power** + connectivity
(LoRaWAN/4G/NB-IoT, see [18-...](18-iot-control-architecture.md) §E7), per-sensor
calibration and drift handling, and the QC layer (B6).

**Refs:** Allen et al. (1998) FAO-56 (exposure & u2 height adjustment); WMO-No. 8 Guide
to Instruments & Methods of Observation; soil-moisture review *Agric. Water Manage.*
(2023).

## B5. Public weather data

On-farm instruments are complemented by public weather feeds (gap-fill, no-AWS farms,
forecasts). Specified in [17-weather-data-integration.md](17-weather-data-integration.md)
(NASA POWER, Open-Meteo, OpenWeather/AgroMonitoring, IMD GKMS, ERA5/GEFS).

## B6. Data-quality guards (QA/QC, outlier & bad-signal rejection)

Because every parameter is live-updated from real-time data
([12-...](12-solver-mathematics.md) §A0), bad data must be caught **before** it reaches
FAO-56, control, or parameter write-back — otherwise one faulty sensor poisons the
calibrated core. A QC stage runs at ingestion and tags each reading **pass / suspect /
fail** (QARTOD-style) with provenance.

| Test | What it catches |
| --- | --- |
| Range / physical-limit | RH outside 0-100%, negative flow on a one-way line, pressure beyond rating |
| Spike / rate-of-change | physically impossible jumps between samples |
| Flatline / stuck-sensor | zero-variance persistence (dead / frozen) over a window |
| Robust outlier (Hampel: median ± k·MAD) | statistical outliers without being skewed by them |
| Cross-sensor consistency | mass balance (sum of zone flows vs mainline), RH vs T vs dewpoint, rain vs forecast |
| Drift detection | AWS vs reanalysis bias trend -> recalibration flag |
| Comms integrity | CRC/checksum, monotonic timestamps, de-dup, staleness |

**Handling.** Suspect/fail readings are excluded from estimation and **never written to
parameters**; gaps fall back along the source-precedence chain (on-farm sensor -> public
weather -> last-known-good -> model estimate), all flagged. Control **fails safe** on
missing/failed critical inputs (hold or conservative schedule; no actuation on bad
data — see [18-...](18-iot-control-architecture.md) §E2).

**In assimilation** ([14-...](14-digital-twin-data-assimilation.md) §C1): innovation
(chi-square) gating rejects any measurement whose residual exceeds N-sigma; a robust
(Huber) update plus covariance inflation limit the damage of survivors; only QC-passed
data with enough samples and a real uncertainty reduction is promoted to core priors
(bounded step, governed).

**Module:** planned `quality/qc.py`, upstream of [`fao56.py`](../FarmTwin/fao56.py),
the edge engine, and the twin; it consumes each device's declared ranges (from the
plug-and-play descriptor, §E6) for the range checks, and writes QC flags into the
parameter registry.

**Refs:** U.S. IOOS QARTOD real-time QC manuals; Hampel (1974) robust outlier
identifier; WMO-No. 8 (QC procedures); Branisavljevic, Prodanovic & Kapelan (2011)
sensor data validation in water systems, *Water Sci. Technol.* doi:10.2166/wst.2011.412;
Bar-Shalom et al. (2001) innovation gating in Kalman filtering.
