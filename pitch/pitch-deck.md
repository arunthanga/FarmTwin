---
marp: true
theme: default
paginate: true
size: 16:9
title: FarmTwin — KSUM / AgriNext Pitch
style: |
  section { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  h1 { color: #0d6e5a; }
  strong { color: #0d6e5a; }
---

# FarmTwin
## Simulation-driven farm digital twin

**KSUM Idea Grant · AgriNext / KERA · GAAM B2G**

Eruthempathy, Chittur (Palakkad) · 15-acre live pilot

---

## The problem

Kerala's **rain-shadow belt** (~1,000 mm/yr vs 3,000 mm state average) just received canal water (2025 Moolathara extension → ~3,575 ha).

**Water arrived. Scheduling is now the bottleneck.**

- Farmers irrigate by **calendar/habit**, not crop-and-soil need
- Krishi Bhavan advice is **generic** — no per-zone, day-by-day answer
- FPOs lack a **cluster water-budget** layer across 650+ ha

---

## Quantified pain

| Impact | Magnitude |
| --- | --- |
| Water wasted (flood vs need-based) | **30–50%** |
| Yield lost to mistimed irrigation | **10–25%** |
| Labour reducible with precision scheduling | **~30%** |

**1,500+ vegetable farmers** in the Chittur cluster · **650 ha** · Nallepilly market

---

## Solution — FarmTwin

A **farm digital twin**: discretize the field into a **mesh** of zones; run a daily **water-balance + crop-growth solver**; optimize irrigation/fertigation under a yield constraint.

> *Irrigate or not, how many litres, where, today — and why.*

**Hardware-light.** IP is the simulation engine. Cheap sensors + free weather/ET data.

Working MVP: [`mvp/index.html`](../mvp/index.html)

---

## Live demo headline

**Twin-optimized vs flood baseline** (15-acre model, 90-day season):

- **≥30% water saved** at equal-or-better yield
- Scenario engine: flood · uniform drip · twin-optimized · heat wave · dry spell
- FPO cluster dashboard: water budget · stress map · harvest planner

*Open the MVP and run "Full-season comparison"*

---

## Moat — not another IoT dashboard

| CAE / simulation skill | FarmTwin application |
| --- | --- |
| Meshing | Farm → irrigation zones |
| FE/CFD-style solvers | Water balance + lateral moisture |
| Assembly-line simulation | Time-stepped crop growth + scheduling |
| Validation rigor | Calibrate twin vs sensors like an engineering model |

**20 years** building validated simulation software + **owned 15-acre test rig**

---

## Go-to-market

| Tier | Buyer | Wedge |
| --- | --- | --- |
| Pilot | Founder's farm + 8–12 neighbours | Free pilot → field evidence |
| Beachhead | **FPOs / FPCs** (Chittur) | Paid SaaS via FPO; **AgriNext** deployment |
| Scale | Krishi Bhavans / Agriculture Dept | **GAAM** direct procurement |
| Phase 2 | Lenders, insurers | Data/risk layer (doc 09) |

**Beachhead:** FPOs — one sale reaches hundreds of farmers inside KERA's distribution.

---

## Kerala GAAM — government without tender

**Government as a Marketplace** (GO Ms No 2/2022/SPD):

- KSUM-registered startups: **direct purchase up to Rs.50 lakh (ex-GST), no tender**
- Overall startup procurement ceiling: **Rs.3 crore**
- KSUM channels: Direct Procurement · Demand Day · Demo Day · Innovation Zones

A **district Krishi Bhavan deployment** (SaaS + sensors, 50–200 farms) fits the Rs.50L band.

**AgriNext proves the product. GAAM scales it.**

---

## Funding roadmap

```text
Idea Grant (Rs.3L) → AgriNext/KERA (Rs.25L) → Productisation (Rs.7L)
  → Seed Fund (Rs.15L) → Scale-up (Rs.25L) → KERA Alliance (Rs.2cr)
```

Parallel: **GAAM B2G revenue** once pilot-proven + KSUM Unique ID

18-month target: calibrated twin · FPO MoU · Idea Grant · AgriNext pilot · first paid FPO

---

## Pilot & traction plan

1. Instrument 15-acre Eruthempathy farm (soil sensors + weather/ET)
2. Calibrate solver to **±15%** soil-moisture error over one crop cycle
3. Two-block trial: baseline schedule vs twin-optimized → **≥30% water saving**
4. Sign **≥1 FPO pilot MoU** (Chittur cluster)

Outputs: calibration chart · water/yield table · 90-sec MVP demo video

---

## The ask

| Channel | Ask |
| --- | --- |
| **KSUM Idea Grant** | Rs.3 lakh · incubation · AgriNext introductions |
| **AgriNext / KERA** | Up to Rs.25L pilot funding · FPO matchmaking · GAAM buyer intros |
| **Attachments** | MVP · CAE portfolio · skill map · signed FPO MoU (when ready) |

**FarmTwin** — mesh the field, solve the schedule, protect the yield.
