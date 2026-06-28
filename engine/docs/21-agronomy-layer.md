# 21 — Agronomy Layer (crops, water, fertilization, yield)

The agronomy layer is the domain knowledge that turns hydraulics into **outcomes**:
which crops, how they grow, how much water and nutrients they need, and what yield
results. It drives FAO-56 ([12-...](12-solver-mathematics.md) §A5) and fertigation
([18-...](18-iot-control-architecture.md) §E5), gives the optimizer
([20-...](20-design-optimization.md)) a yield/profit objective, and is continuously
recalibrated by recorded yield.

> **Why it matters.** Water and pressure are means; yield and profit are the ends. The
> agronomy layer is what lets both products optimize for the end, and the
> **yield-recording loop** is the most valuable feedback the system collects.

## F1. Crop knowledge base

Per-crop parameter sets (live, see [12-...](12-solver-mathematics.md) §A0) for the
Palakkad belt — banana, coconut, mango, paddy, groundnut, and vegetables (selectable).
Each crop record holds:

| Group | Fields |
| --- | --- |
| Phenology | stage lengths (initial / development / mid / late) **or** GDD thresholds + base temperature Tb |
| Water | Kcb / Kc by stage (FAO-56 Tbl 12/17), root depth Zr by stage, depletion fraction p (MAD), crop height |
| Yield | potential yield Ym, water yield-response factor Ky (FAO-33), salinity threshold + slope (Maas-Hoffman) |
| Nutrients | N-P-K (and micros) uptake/removal by stage, target EC & pH, fertigation recipe |
| Calendar | planting / harvest windows, region |

Seeded from FAO-56 / FAO-33 / FAO-66 tables and the local **KAU (Kerala Agricultural
University) Package of Practices**; refined per-farm by recorded data (F4).

**Module:** `agronomy/cropdb` (data) + a `Crop` parameter object the models read.

## F2. Crop water — stage-driven, real-time

The crop's **current stage** sets `Kcb`, `Zr` and `p` each day; `ETc = (Kcb + Ke) ET0`
([12-...](12-solver-mathematics.md) §A5). Stage advance is **GDD-driven** from AWS
temperature ([13-...](13-sensors-and-instrumentation.md) §B4):

```
GDD_day = max(0, (Tmax + Tmin)/2 - Tb)
cumulative GDD crosses a stage threshold  ->  advance stage  ->  new Kcb, Zr, p
```

So the same crop in a hot year progresses faster automatically, rather than by a fixed
calendar. The water-stress coefficient `Ks` from the root-zone balance feeds the yield
estimate (F3) and can tighten scheduling.

## F3. Fertilization & yield models

**Fertilization.** Stage nutrient demand -> fertigation setpoints (target EC/pH and
N-P-K split) consumed by the fertigation node ([18-...](18-iot-control-architecture.md)
§E5); dose is scaled to ETc / growth (proportional dosing) and corrected by EC/pH
feedback (and optional periodic leaf/soil tests).

**Yield (real-time estimate).** Water-limited relative yield via the FAO-33 production
function, stage-weighted:

```
(1 - Ya/Ym) = Ky * (1 - ETa/ETc)                         (per stage, then combined)
```

Extended with salinity (Maas-Hoffman `Yr = 1 - s (ECe - ECthreshold)`) and a
nutrient-stress factor. This produces a running, updateable **yield forecast** through
the season.

**Higher fidelity (offline / optional).** AquaCrop (canopy/biomass, daily water-driven)
or DSSAT / APSIM (process-based) for calibration and research with IIT Palakkad / KAU —
mirroring the online-lightweight / offline-detailed split used for component CFD
([12-...](12-solver-mathematics.md) §A6). The lightweight FAO-33 model runs in the
real-time loop; the heavy models run offline to calibrate it.

## F4. Yield recording layer (ground truth -> back into the system)

A layer to **record actual outcomes** per zone/plot/season:

| Recorded | Examples |
| --- | --- |
| Crop + dates | crop, variety, sowing, harvest |
| Inputs applied | water volume, N-P-K mass, agro-chemicals |
| Output | harvest quantity, quality grade |
| Economics | input cost, sale price |

Captured by mobile app / manual entry, optionally a yield monitor / weigh-scale or
grading data. This ground truth:

1. **Calibrates crop parameters** (Ky, Kc, nutrient response, MAD) through the A0
   learning loop — governed, B6-checked write-back ([14-...](14-digital-twin-data-assimilation.md)).
2. **Becomes the optimizer's objective** ([20-...](20-design-optimization.md)): design
   for expected yield / profit and water productivity (kg per m3), not just hydraulic
   uniformity.
3. **Aggregates into regional benchmarks** (crop x practice x climate) — an agronomic
   data moat valuable to FPOs and for AgriNext.

**Module:** `agronomy/yield` records + a calibration job that proposes parameter
updates.

## F5. How agronomy enters the real-time solver

Agronomy state (crop, stage, GDD, accumulated stress, expected yield) is part of the
digital-twin state ([14-...](14-digital-twin-data-assimilation.md)). Each timestep:

```
advance phenology (GDD from AWS) -> update Kcb, Zr, p, nutrient demand (live params, A0)
   -> FAO-56 sets water requirement (A5)  and  E5 sets dosing setpoints
   -> edge control acts (E2)
   -> soil-moisture + EC/pH sensors assimilated (C1) correct the state
   -> real-time yield estimate (F3) updates
```

Recorded yield (F4) closes the **slow outer loop**, recalibrating crop parameters so
next season's water/nutrient plans and the Design Studio's recommendations get sharper.
Agronomy is thus a first-class, continuously-calibrated driver of both runtime control
and the design optimizer — not a static lookup.

## F6. Module map

| Concern | Module | Consumed by |
| --- | --- | --- |
| Crop database | `agronomy/cropdb` | FAO-56, optimizer, twin |
| GDD phenology | `agronomy/phenology` | FAO-56 (Kc/Zr/p), fertigation |
| Yield model | `agronomy/yield` (FAO-33) | optimizer objective, twin |
| Yield records + calibration | `agronomy/records` | learning loop (params.py) |

## F7. References

- Allen, Pereira, Raes & Smith (1998) FAO-56 — Kc tables, dual-Kc, stress.
- Doorenbos & Kassam (1979) FAO-33 — yield response to water (Ky).
- Steduto, Hsiao, Fereres, Raes (2012) FAO-66 / AquaCrop — water-driven yield.
- Maas & Hoffman (1977) — crop salt tolerance (salinity-yield).
- Jones et al. (2003) DSSAT-CSM; Holzworth et al. (2014) APSIM.
- KAU (Kerala Agricultural University) Package of Practices — local crop calendars,
  Kc, fertigation schedules.
