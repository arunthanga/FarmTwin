# 01 — Lead Venture Decision

## Decision

**Lead with the agri-deeptech digital twin (product name: FarmTwin).**
Agri-fintech is sequenced as a Phase-2 layer on top of the same data; pure CAE
SaaS is kept as an optional parallel/fallback, not the KSUM entry vehicle.

## Why this lead (scored against the three candidates)

| Criterion (weight) | Agri digital twin | Agri-fintech | Pure CAE SaaS |
| --- | --- | --- | --- |
| Clears KSUM "innovative tech product" test (must-have) | Yes | Yes | Yes |
| Leverages the 15-acre Eruthempathy farm as pilot (high) | Strong | Weak | None |
| Rides the World Bank KERA / AgriNext wave + 40k-farmer distribution (high) | Strong | Medium | None |
| Directly reuses meshing + assembly-line simulation skills (high) | Strong | Weak | Strong |
| Time-to-first-revenue / first pilot (medium) | Fast (own farm) | Slow (needs license/partners) | Medium |
| Regulatory load at start (medium) | Low | High (RBI/lending/insurance) | Low |
| Combines all three stated interests: finance + agri + tech (medium) | Yes (fintech as phase 2) | Partial | No |

The digital twin is the only option that scores strongly on *every* high-weight
criterion. Crucially, it converts the farm from a liability ("I own land") into
the single biggest startup asset most agritech founders lack: a controllable,
instrumented pilot site that produces demo footage, validation data, and yield
evidence for grant reviewers.

## The one-line pitch

> FarmTwin builds a simulation-driven digital twin of a farm — a "mesh" of
> the field where each cell models soil moisture, evapotranspiration, nutrients
> and crop growth — so farmers and FPOs irrigate and fertilize by precise need
> instead of habit, cutting water/input use 30-50% while protecting yield.

## Why the simulation framing is defensible (not just another IoT dashboard)

Most "agritech" entrants stop at sensors + dashboards. FarmTwin's moat is the
**physics/agronomy simulation engine** — the same competency as virtual
assembly-line simulation and FE meshing:

- The field is discretized into a **mesh** of zones (cells), exactly like an FE
  mesh. Each cell carries state and exchanges water/nutrients with neighbours.
- A **water-balance + crop-growth solver** steps the twin forward in time, the
  same way an assembly-line sim steps stations forward through a shift.
- This lets us run **what-if scenarios** ("flood vs drip vs optimized", "skip
  irrigation 2 days", "heat wave") *before* acting in the field — the core value
  of any digital twin.

## Scope discipline (what we are NOT building first)

- No bespoke hardware. Use existing/cheap soil + weather sensors and public
  weather/ET data; the IP is the simulation + optimization layer.
- No lending/insurance product yet (Phase 2 — see `09-agri-fintech-phase2.md`).
- No manufacturing CAE features. Keep the engine general but the GTM agri-only.

## Immediate consequence for the application

We apply to KSUM and AgriNext as a **software/deeptech product company** whose
pilot happens to run on the founder's farm — never as a "farm" or "agribusiness"
(those are KSUM-ineligible). See `02-problem-statement.md`.
