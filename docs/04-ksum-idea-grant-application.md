# 04 — KSUM Idea Grant Application (Ready-to-Submit Draft)

Scheme: **Idea Grant**, up to **Rs.3 lakh**, for Ideation/PoC/MVP stage.
Apply at <https://startupmission.kerala.gov.in/schemes/idea-grant>.
Note: company incorporation + KSUM Unique ID are required only before *disbursal*.

Fill the portal fields with the content below; shortlisted applicants pitch.

---

## 1. Startup / Product name
FarmTwin

## 2. Founder
20 years in CAE / engineering simulation — meshing algorithms and virtual
assembly-line simulation. Based in Eruthempathy, Chittur, Palakkad; owns the
15-acre pilot farm.

## 3. Sector & stage
Agritech + Deeptech (simulation/AI). Stage: working MVP (prototype), pre-revenue.

## 4. Problem (max impact, 100-150 words)
Kerala's rain-shadow belt in Chittur (Palakkad) gets one-third of the state's
rainfall. The 2025 Moolathara canal extension finally delivers irrigation water
to ~3,575 ha, but farmers still irrigate by calendar/habit, not by crop-and-soil
need. The result: scarce canal water is over-applied in some plots and
under-applied in others, wasting 30-50% of water and losing 10-25% of potential
yield to mistimed irrigation and nutrient stress. There is no plot-level,
day-by-day decision tool tuned to this microclimate, and FPOs have no shared
layer to budget water and plan harvests across 650+ ha of vegetable clusters.

## 5. Solution / innovation (150-200 words)
FarmTwin is a **farm digital twin**. We discretize a field into a computational
**mesh** of zones — the same technique used in finite-element meshing — and run a
time-stepped **water-balance + crop-growth solver** (the same class of model as a
virtual assembly-line simulation) over each zone. The twin ingests soil type,
crop, emitter layout, weather/ET and low-cost soil-moisture readings, then
predicts moisture, stress and growth per zone per day and **optimizes the
irrigation/fertigation schedule** to minimize water and cost subject to a yield
constraint.

The defensible innovation is the **simulation + optimization engine**, not a
sensor dashboard: farmers can run what-if scenarios (flood vs drip vs optimized,
heat wave, skipped irrigation) and see water saved, stress-days avoided and
projected yield *before* acting. A working MVP already demonstrates this on a
modelled 15-acre layout. The founder's 20 years building validated engineering
simulation software is the core technical moat.

## 6. Innovation vs existing solutions
Existing agritech in Kerala is mostly IoT dashboards (show data) or generic
advisory. FarmTwin **predicts and optimizes** — a true twin with a calibrated
solver, validated against field data like an engineering model. Hardware-light:
IP is software, using cheap/existing sensors and free weather/ET data.

## 7. Target customer & market
Beachhead: FPOs/FPCs in the Chittur rain-shadow cluster (1,500+ farmers, 650 ha),
routed through the KERA/AgriNext program. Expansion: Krishi Bhavans and other
rain-shadow districts via Kerala's **Government as a Marketplace (GAAM)** policy —
departments can procure directly from KSUM-registered startups **up to Rs.50 lakh
(ex-GST) without tender** (GO Ms No 2/2022/SPD), which covers a district-scale
SaaS + sensor deployment. Then pan-India water-stressed horticulture.

## 8. Pilot & traction plan
Live pilot on the founder's 15-acre Eruthempathy farm + 8-12 neighbours.
Calibrate the twin over one crop cycle; target >=30% simulated water saving at
equal yield; convert to >=1 signed FPO pilot MoU (template in doc 08).

## 9. Use of Idea Grant funds (Rs.3,00,000)
| Item | Amount (Rs.) |
| --- | --- |
| Field instrumentation: soil-moisture + weather sensors, gateway for pilot zones | 90,000 |
| Cloud + dev tooling (compute, hosting, data) for 12 months | 60,000 |
| Solver/MVP hardening: developer/agronomy contractor time | 90,000 |
| Calibration & field validation (travel, agronomist consult, soil tests) | 45,000 |
| IP/legal (provisional patent search, incorporation costs) | 15,000 |
| **Total** | **3,00,000** |

## 10. Milestones (grant is milestone-disbursed)
1. M1 (month 2): sensors deployed on pilot farm; twin ingesting live data.
2. M2 (month 4): solver calibrated to defined soil-moisture error band.
3. M3 (month 6): scenario engine shows >=30% water saving; 1 FPO pilot MoU.

## 11. Team & ask
Solo founder at filing (see doc 06 on adding a co-founder/team). Ask: Rs.3 lakh
Idea Grant + KSUM incubation + AgriNext deployment introductions + GAAM buyer
intros (Krishi Bhavan / Agriculture Dept) for post-pilot scale.

## 12. Attachments
- MVP link/screenshots (`../mvp/index.html`)
- Pitch deck — any of: `../pitch/pitch-deck.html`, `../pitch/pitch-deck.pdf`, `../pitch/pitch-deck.pptx`
- One-pager (`../pitch/one-pager.md`)
- Founder CAE portfolio / résumé
- Skill map (`02-problem-statement.md`)

---

### Pitch-day talking points
- Open with the canal: "Water just arrived; scheduling is now the bottleneck."
- Show the MVP scenario toggle: flood vs optimized -> live water-saving number.
- Land the moat: "I have spent 20 years meshing and simulating physical systems;
  a farm is just another domain to mesh and solve — and I own the test rig."
- Close the GTM loop: "Kerala lets departments buy from KSUM startups up to Rs.50
  lakh without a tender — a Krishi Bhavan cluster deployment fits that band. We
  enter through AgriNext/FPO pilots, then scale via GAAM direct procurement."
