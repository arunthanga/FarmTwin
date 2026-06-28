# 11 — FarmTwin: KSUM Pitch Deck

> A pitch deck you can read aloud or paste into slides. It blends a true, local,
> emotional story with hard engineering and a concrete, fundable first win.
> Tone: heart + rigour. Numbers labelled **[fact]** are sourced (see doc 12); numbers
> labelled **[est.]** are our assumptions, shown transparently.

---

## Slide 1 — Title

**FarmTwin**
*A digital twin that makes sure every drop of water reaches the last farmer's roots.*

Founder-built in **Eruthempathy, Chittur (Palakkad)** — Kerala's rain-shadow belt.
From 20 years of CAE simulation for the world's factories → to water for our own village.

---

## Slide 2 — The story (why this is personal)

I grew up beside a paradox: a land of farmers that runs out of water.

In **Eruthempathy**, we get less than **1,000 mm of rain a year** — one-third of Kerala's
average **[fact]**. I have watched coconut palms wither, neighbours queue for hours at the
Kunnamattupathy regulator for a tanker's worth of drinking water, and young people leave
because the soil could not pay them back.

For 20 years I built simulation software — meshing algorithms, virtual assembly lines —
so global manufacturers could test a factory before they built it. One day it struck me:
**I can simulate a Mercedes line in a computer, but my own village can't predict whether
water will reach a field next week.**

FarmTwin is me bringing that toolset home.

---

## Slide 3 — The problem (the head, after the heart)

Palakkad's eastern belt is Kerala's driest region. Water is **contested** (shared with
Tamil Nadu under the Parambikulam-Aliyar agreement), **scarce**, and **badly distributed**:

- 26 development blocks in Palakkad are rated **unsafe** on groundwater **[fact]**.
- Tail-end farmers on the Moolathara Right Bank Canal have been **neglected for decades**;
  the old Moolathara lift canal has had **no summer water for 7 years**, hitting **~1,000
  acres of coconut** **[fact]**.
- A ₹2-crore canal clean-up was announced years ago — **and nothing happened** **[fact]**.

The lesson: **building canals is not the same as delivering water to roots.** Concrete
arrives; outcomes don't. That last mile — *who gets water, when, how much, did the crop
actually benefit* — is an **information and control problem**, not a civil-works problem.

---

## Slide 4 — Why now

After decades of neglect, the money is finally flowing into our exact region:

- The **Moolathara Right Bank Canal Extension** (KIIFB, ~**₹262 crore**) — Kerala's
  **largest community micro-irrigation project** — is being commissioned **early 2026**,
  serving **3,575 ha** in Phase I and **10,000+ ha** in Phase II, explicitly targeting
  **Eruthempathy, Vadakarapathy, Kozhinjampara** **[fact]**.
- **Community Micro Irrigation (CMI)** on its ayacut is an **active, repeating
  procurement pipeline** — KIIDC has already tendered **~₹40.5 cr across 3 zones** (Zone I-III,
  closed Feb 2026), and is replicating CMI in other command areas **[fact]**. More zones,
  Phase-II and O&M packages are coming.
- Farmers can get **up to 85% subsidy** on micro-irrigation (PDMC 55% + Kerala Samrudhi
  30%) **[fact]** — capital is subsidised; what's missing is the intelligence layer.

**The canal is being built in our backyard. The intelligence to make it actually work is
the gap we fill.**

---

## Slide 5 — The solution: FarmTwin

**A self-calibrating digital twin for irrigation** — two products on one physics +
agronomy engine:

1. **FarmTwin Studio** — *before installation.* Survey the land (altitude, flow, soil,
   crop) → our solver designs and **optimises** the network (pumps, pipes, valves, drips,
   sensors, fertigation) and returns the **2-3 best layouts** by cost, energy, uniformity
   and yield.
2. **FarmTwin Runtime** — *after installation.* Edge + IoT controllers (solar, wireless)
   read sensors + weather + cloud and **decide when/how long to irrigate and fertigate**,
   acting on pumps and valves — with guards that reject bad sensor data.

Underneath: **FarmTwin Engine** — a hydraulic + FAO-56 agronomy solver whose parameters
**keep learning** from live field data, so accuracy improves every season.

> In one line: **IRRICAD's design power + a living digital twin that runs the farm — built
> in India, for Indian water.**

---

## Slide 6 — How it works (the engineering moat)

```
 Survey ─▶ FarmTwin Studio ─▶ optimal design + BoM + sensor/valve plan
                                        │
                                        ▼
                      install (rides on govt/PDMC capex)
                                        │
                                        ▼
 sensors+weather ─▶ FarmTwin Runtime (edge) ─▶ pumps/valves/fertigation
                                        │
                                        ▼
                FarmTwin Engine digital twin assimilates reality,
                recalibrates parameters ──▶ better design next time (learning loop)
```

This is the same discipline I used in CAE: discretise the domain, solve the physics,
compare to reality, correct the model. Most "agritech" stops at dashboards. **We predict,
optimise and control** — and get smarter with every farm.

---

## Slide 7 — Why us (unfair advantages)

- **20 years of CAE / simulation** (meshing, solvers, virtual lines) — the rare skill set
  this actually needs.
- **A live pilot in the exact project panchayat:** 15 acres in Eruthempathy, on the
  Moolathara RBC ayacut. We can prove it on our own soil first.
- **Working code already:** an open hydraulic + FAO-56 engine (GGA solver, components,
  emitters, agronomy) and a runnable MVP — see the repo.
- **Research on our doorstep:** IIT Palakkad (water resources, HPC) and Kerala
  Agricultural University for validation and credibility.

---

## Slide 8 — The immediate win: Moolathara RBC

We do **not** need to wait years for product-market fit. There is a government-funded,
de-risked beachhead **happening now, 2 km from my home**:

- **Win the intelligence layer** of the Moolathara CMI build-out: hydraulic design /
  DPR support (FarmTwin Studio), the digital-twin monitoring + control system (FarmTwin
  Runtime), and — crucially — **performance/O&M monitoring** that ensures the system
  *keeps* delivering (directly answering the "canal built but no water" failure).
- **Realistic role:** partner with the civil contractor as the **design + digital-twin +
  monitoring** specialist; target the **next** CMI packages (Phase-II zones, Phase-I O&M /
  performance-monitoring) since Zone I-III closed Feb 2026; run a **KSUM-funded pilot** on
  our 15 acres + one CMI zone as the reference site.
- **Addressable on Moolathara alone [est.]:** ~₹4-5 cr one-time (design + twin + IoT
  across Phase I 3,575 ha) and **₹1-2 cr/yr recurring** (SaaS + O&M) once Phase I+II run.
  Full math and assumptions in **doc 12**.

> Immediate, local, fundable — and it makes our pilot the *proof* we sell everywhere else.

---

## Slide 9 — The opportunity size (beachhead → world)

| Tier | Scope | Addressable for FarmTwin's layer |
| --- | --- | --- |
| **SOM (Yr 1-2)** | Moolathara RBC Phase I design + KSUM pilot + monitoring | **₹1-2 cr** [est.] |
| **Beachhead (2-3 yr)** | Moolathara Phase I+II (~13,500 ha) + Chitturpuzha (20,440 ha [fact]) | **₹10-25 cr** [est.] |
| **SAM (3-5 yr)** | Kerala KIIFB CMI + PDMC micro-irrigation projects | **₹100-300 cr** [est.] |
| **TAM (long)** | India PMKSY-PDMC (₹1000s cr/yr [fact]); ~70 M ha micro-irrigation potential; global precision-irrigation market | **very large, double-digit CAGR** |

The wedge is small and winnable; the ladder above it is enormous. **We start with one
canal we can touch — and end with farmers everywhere.**

---

## Slide 10 — Business model

Subsidy-aligned, so the farmer/government capex pays for adoption:

1. **Design & optimisation (Studio):** project/consulting fee, ~₹3-6k/ha [est.].
2. **Digital-twin + IoT (Runtime):** hardware + software per zone — **fundable inside the
   ~85% micro-irrigation subsidy** as part of system cost.
3. **Recurring SaaS + O&M / performance monitoring:** ~₹1,000-1,500/ha/yr [est.] — the
   sticky, scalable line, and the one that fixes the "nobody maintained it" problem.
4. **Later (Phase 2):** data-driven agri-fintech (yield-backed credit, insurance) — see
   doc 09.

---

## Slide 11 — Go-to-market

1. **Prove** on 15 acres in Eruthempathy + one Moolathara CMI zone (KSUM-funded pilot).
2. **Win** Moolathara RBC design/monitoring sub-packages with a civil partner.
3. **Expand** across Chitturpuzha command area and Palakkad FPOs.
4. **Replicate** the KIIFB-CMI model statewide (Kerala) and via PDMC nationally.
5. **Globalise** the software/twin (the marginal cost of software is near zero).

---

## Slide 12 — Traction & assets

- **FarmTwin Engine (open):** GGA hydraulic solver, component/emitter library, FAO-56
  agronomy — written and on GitHub (`github.com/arunthanga/FarmTwin`).
- **MVP:** a runnable farm digital-twin simulator.
- **Deep design dossier:** 13+ technical docs (solver math, sensors, IoT/fertigation,
  agronomy, optimisation, digital-twin assimilation) + an annotated bibliography.
- **Pilot land:** 15 acres in the target panchayat.
- **Brand:** FarmTwin (trademark due-diligence done — doc 10).

---

## Slide 13 — The ask (KSUM)

We're applying for the **KSUM Idea/Seed grant** to:

- Build the field-ready **FarmTwin Runtime** controller (solar, wireless) + sensor kit.
- Deploy a **calibrated pilot** on 15 acres + one Moolathara CMI zone.
- Validate with **IIT Palakkad / KAU** and produce a performance report.
- Use the pilot to **bid the live Moolathara CMI / DPR packages**.

**12-month milestones:** working controller → pilot live → validated water-saving &
yield numbers → first paid design/monitoring contract on the RBC.

---

## Slide 14 — Vision (the close)

A canal reached my village after 60 years of waiting. But concrete alone has failed us
before. **FarmTwin makes sure that this time, the water actually reaches the roots — and
that we can prove it, drop by drop.**

We start with one canal in Chittur. We're building the system that lets **any farmer,
anywhere in the world, grow more with less water.**

*From simulating the world's factories — to securing our farmers' water.*
