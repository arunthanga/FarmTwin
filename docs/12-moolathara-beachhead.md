# 12 — Moolathara RBC: Immediate-Win Beachhead & Opportunity Sizing

The business case behind Slide 8-9 of the pitch (doc 11). It (a) documents the real,
verifiable facts, (b) defines exactly where FarmTwin fits and how it earns money, (c) sizes
the opportunity from our backyard to the world, and (d) gives an action plan.

> **Honesty note.** Items marked **[fact]** are sourced (links below). Items marked
> **[est.]** are our assumptions for sizing — deliberately conservative and shown so they
> can be challenged. We are a deeptech software + IoT + services startup, **not** a civil
> contractor; our realistic role is the *intelligence layer*, won with/alongside the civil
> contractor and via government-funded pilots.

---

## 1. The situation (facts)

### 1.1 The system
- The **Chitturpuzha Irrigation Project** (Palakkad) has a total ayacut of **20,440 ha**
  across Chittur/Palakkad/Alathur taluks; water is shared with Tamil Nadu under the
  **Parambikulam-Aliyar** agreement (~205 Mm³/yr). The **Moolathara regulator** feeds the
  **Left Bank Canal (LBC)** and **Right Bank Canal (RBC)**. **[fact]**
  (irrigation.kerala.gov.in; indiawris.gov.in)

### 1.2 The new project (the opportunity)
- **Extension of Moolathara RBC (Korayar → Varattayar)** — KIIFB-funded, **AS ≈ ₹262.10
  cr** (also listed ₹255.18 cr), executed by **K K Constructions** under **KIIDC**;
  started 2021; **>80% complete (Jul 2025); commissioning early 2026**. **[fact]**
- **Phase I:** 6.43 km, 10 m wide → **3,575 ha**, drip + lift, **up to 70% water saving**;
  explicitly serves rain-shadow **Eruthempathy, Vadakarapathy, Kozhinjampara** (<1,000 mm
  rain/yr). **[fact]** (New Indian Express, Jul 2025; Manorama)
- **Phase II:** Varattayar → Velanthavalam (8.2 km) → benefits **10,000+ ha**. **[fact]**
- **Community Micro Irrigation (CMI)** packages on the ayacut have been **tendered by
  KIIDC** in three zones — **~₹40.5 cr already on the table** for this one canal extension
  **[fact]** (kiidc.kerala.gov.in):

  | Zone | Work | Tender ID | Value | Closing date |
  | --- | --- | --- | --- | --- |
  | Zone-I | General Civil Work | 2026_KIIDC_831857_1 | ₹13,22,54,848 | 20-Feb-2026 |
  | Zone-II | CMI General Civil Work | 2026_KIIDC_833052_1 | ₹13,14,55,994 | 25-Feb-2026 |
  | Zone-III | CMI DPR Preparation Work | 2026_KIIDC_833031_1 | ₹14,18,53,391 | 25-Feb-2026 |

  **Status (as of mid-2026): these three closed in Feb 2026** — so they are *evidence of an
  active, repeating procurement pipeline*, not packages we can still bid. KIIDC is also
  rolling out CMI elsewhere (e.g. **Chinnar river, Idukki**, ₹2.26 cr, closed Mar 2026)
  **[fact]**, confirming the model is being replicated statewide. **Our window is the next
  packages**: Phase-II (Varattayar→Velanthavalam) CMI zones, **O&M / performance-monitoring**
  contracts on Phase-I once commissioned, and CMI in other command areas.

### 1.3 Why the intelligence layer matters (the failure we fix)
- The **old Moolathara lift canal** has had **no summer water for 7 years**, hitting
  **~1,000 acres of coconut** within a 10 km radius; a **₹2-cr clean-up was announced and
  never executed**. **[fact]** (The Hindu)
- The RBC tail-end has been **politically neglected for decades** — at one point farmers
  floated an "RBC" group and voted **NOTA** in protest. **[fact]** (KochiPost)
- **Conclusion:** the region's problem is no longer only *building* infrastructure — it is
  **operating it so water actually reaches roots, and proving it.** That is software,
  sensing, control and O&M — i.e. **FarmTwin**.

---

## 2. Where FarmTwin fits (our winnable role)

| Need in the Moolathara CMI program | FarmTwin offering | Product |
| --- | --- | --- |
| Hydraulic design / optimisation of CMI zones; DPR support | Survey → optimise → best layouts, BoM, sensor/valve plan | **Studio** |
| Make water actually reach the tail-end; auto-operate | Edge + IoT control of pumps/valves, fertigation, weather-aware scheduling | **Runtime** |
| Stop "built but not maintained" failures | Continuous **performance monitoring & O&M dashboard**; alerts on under-delivery | **Runtime + twin** |
| Prove water-saving & yield to government/funders | Digital-twin reports, distribution-uniformity, water/yield KPIs | **Engine + twin** |

We partner with the **civil contractor** (they pour concrete; we supply brains) and bid the
**DPR / CMI design & monitoring** sub-packages directly.

---

## 3. Opportunity sizing

### 3.1 Assumptions (challenge these) [est.]
- Design + DPR support: **₹4,000/ha** (one-time).
- Digital-twin + IoT supply & install: **₹9,000/ha** (one-time; largely fundable inside
  the micro-irrigation system cost / ~85% subsidy).
- Recurring SaaS + O&M / performance monitoring: **₹1,200/ha/yr**.
- Areas (facts): Phase I **3,575 ha**; Phase I+II **~13,500 ha**; Chitturpuzha **20,440 ha**.

### 3.2 Moolathara RBC — the beachhead
| Line | Phase I (3,575 ha) | Phase I+II (~13,500 ha) |
| --- | --- | --- |
| Design + DPR (one-time) | ₹1.4 cr | ₹5.4 cr |
| Digital-twin + IoT (one-time) | ₹3.2 cr | ₹12.2 cr |
| **One-time total** | **≈ ₹4.6 cr** | **≈ ₹17.6 cr** |
| Recurring SaaS + O&M / yr | ₹0.43 cr/yr | ₹1.6 cr/yr |

> Even capturing a **slice** — Phase I design + a KSUM-funded pilot zone + first
> monitoring contract — is a **₹1-2 cr** Year-1-2 revenue beachhead with a flagship
> reference site. (SOM)

### 3.3 The ladder above the beachhead
| Tier | Scope | Addressable for our layer [est.] |
| --- | --- | --- |
| **SOM (Yr 1-2)** | Phase I design + KSUM pilot + first monitoring deal | **₹1-2 cr** |
| **Beachhead (2-3 yr)** | Moolathara I+II + Chitturpuzha command | **₹10-25 cr** |
| **SAM (3-5 yr)** | Kerala KIIFB-CMI + PDMC micro-irrigation | **₹100-300 cr** |
| **TAM (long)** | India PMKSY-PDMC (₹1000s cr/yr [fact]); ~70 M ha potential; global precision irrigation | **very large** |

National context [fact]: PMKSY-PDMC has covered **80+ lakh ha**; micro-irrigation is a
central+state priority with **85% subsidy in Kerala**. The software/twin/O&M layer is
under-served everywhere — that is our long runway.

---

## 4. Action plan (next 12 months)

1. **Pilot (KSUM-funded):** instrument the 15-acre Eruthempathy farm + secure one Moolathara
   CMI demo zone; deploy Studio design + Runtime control; publish water-saving & yield data.
2. **Partner:** sign an MoU with the CMI civil contractor / a system integrator to be their
   design + digital-twin + monitoring arm.
3. **Position for the next packages:** the Feb-2026 Zone I-III tenders have closed, so
   register as a KIIDC/WRD vendor now and target **Phase-II CMI zones**, **Phase-I O&M /
   performance-monitoring** (post-commissioning), and CMI in other command areas — starting
   with design & monitoring scope, which suits a startup.
4. **Validate:** IIT Palakkad (hydraulics/HPC) + KAU (agronomy) as validation partners for
   credibility with KIIDC/WRD.
5. **Productise:** turn the pilot into a repeatable "CMI-zone-in-a-box" (design + controller
   + dashboard) to scale across Chitturpuzha and Kerala.

## 5. Risks & honest caveats
- **Procurement reality:** prime civil tenders favour established contractors; our path is
  **sub-package + partnership + government-funded pilot**, not prime bidding on day one.
- **Water availability is political** (PAP inter-state sharing) — FarmTwin optimises
  *whatever* water arrives and proves shortfalls with data; it cannot create water.
- **Sizing is indicative** — validate ₹/ha against an actual CMI DPR before quoting.
- **Brand:** "FarmTwin" is descriptive and a same-concept project exists abroad (doc 10);
  proceed with formal TM search.

---

## Sources
- Chitturpuzha Irrigation Project — irrigation.kerala.gov.in/chitturpuzha-irrigation-project
- Chitturpuzha (WRIS) — indiawris.gov.in (Project JI02672)
- MRBC extension (KIIDC) — kiidc.kerala.gov.in/extension-of-moolathara-right-bank-canal-from-korayar-to-varattayar/
- CMI tender (KIIDC) — kiidc.kerala.gov.in (KIIFB-CMI-MRBC … Zone-I General Civil Work)
- "Kerala's largest micro-irrigation project nears completion" — New Indian Express, 18 Jul 2025
- "Lack of water in Moolathara lift irrigation canal…" — The Hindu
- "History of Breaches and Politics of Moolathara Regulator" — KochiPost, 20 Jun 2020
- PDMC subsidy (55%/45%; Kerala up to 85%) — PIB PRID 2003188; Goa Chronicle
