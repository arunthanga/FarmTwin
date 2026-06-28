# On-Farm Pilot Protocol (15-acre Eruthempathy site)

The MVP (`index.html`) is the digital twin. This is how we calibrate and validate
it on the real farm so the demo numbers become defensible field evidence.

## 1. Instrument the field (low-cost, hardware-light)
- Divide the 15 acres into the same zone mesh used in the app (start coarse:
  8-16 zones by soil type / crop / emitter line).
- Place 1 soil-moisture sensor per representative zone (capacitive, ~Rs.1-2k each)
  + 1 small weather station / use IMD + open ET data for the Chittur grid.
- Log emitter flow rates and irrigation events (start: manual logbook is fine).

## 2. Calibrate the solver
- Set each zone's field capacity / soil type from a basic soil test.
- Run the twin in parallel with real irrigation for 2-3 weeks.
- Tune the water-balance + lateral-flow parameters until simulated soil moisture
  tracks sensor readings within a target error band (e.g. ±15%).

## 3. Validate the saving
- Pick 2 comparable blocks: one on farmer's normal schedule, one on
  twin-optimized recommendations.
- Measure water applied (flow x time) and yield/quality at harvest.
- Success target: >=30% water saving at equal-or-better yield (the headline KPI
  the app reports for the simulated case).

## 4. Outputs for the application
- Calibration error chart (sim vs sensor).
- Side-by-side water + yield table for the two blocks.
- A 90-second screen recording of the app's flood-vs-optimized comparison.
- These feed directly into the Idea Grant pitch (doc 04) and AgriNext (doc 05).

## Mapping app -> field
| App element | Real-world counterpart |
| --- | --- |
| Zone mesh | Soil/crop/emitter blocks of the farm |
| Water-balance solver | Calibrated against soil-moisture sensors |
| Climate scenario | IMD/open weather + ET for Chittur |
| "Twin-optimized" strategy | The daily recommendation farmers act on |
| Comparison table | The two-block field trial result |
