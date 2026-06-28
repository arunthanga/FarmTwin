# FarmTwin — Agri Digital-Twin & Precision-Operations Platform

A deeptech venture that applies 20 years of CAE / simulation expertise (meshing,
virtual assembly-line simulation) to agriculture: a **farm digital twin** that
simulates irrigation, soil-moisture, nutrient and yield dynamics so farmers and
FPOs can cut water/input use and raise yields. The 15-acre rain-shadow farm in
**Eruthempathy, Chittur (Palakkad)** is the live pilot and demonstration site.

This repository is the execution package for the Kerala Startup Mission (KSUM)
application. It contains the business/application artifacts, synced pitch
materials (Markdown, Marp, HTML), and a working MVP.

## What's here

| Path | Purpose | Plan to-do |
| --- | --- | --- |
| [docs/01-venture-decision.md](docs/01-venture-decision.md) | Lead-venture decision + rationale | choose-lead |
| [docs/02-problem-statement.md](docs/02-problem-statement.md) | Problem, target user, CAE-to-agri skill map | sharpen-problem |
| [docs/03-dpiit-ksum-registration.md](docs/03-dpiit-ksum-registration.md) | Step-by-step DPIIT + KSUM Unique ID guide | dpiit-ksum |
| [docs/04-ksum-idea-grant-application.md](docs/04-ksum-idea-grant-application.md) | Ready-to-submit Idea Grant application draft | idea-grant |
| [docs/05-agrinext-problem-statement.md](docs/05-agrinext-problem-statement.md) | AgriNext / KERA problem-statement submission | idea-grant |
| [mvp/index.html](mvp/index.html) | Working farm digital-twin precision-irrigation simulator | mvp-pilot |
| [pitch/](pitch/README.md) | Synced pitch deck (MD, HTML, PDF, PPTX, one-pager, script) | idea-grant |
| [docs/06-incorporation-guide.md](docs/06-incorporation-guide.md) | Pvt Ltd vs LLP decision + incorporation steps | incorporate |
| [docs/07-funding-roadmap.md](docs/07-funding-roadmap.md) | Grant -> seed -> scale-up funding sequence | scale-funding |
| [docs/08-fpo-pilot-mou-template.md](docs/08-fpo-pilot-mou-template.md) | FPO pilot MoU template | scale-funding |
| [docs/09-agri-fintech-phase2.md](docs/09-agri-fintech-phase2.md) | Phase-2 agri-fintech layer | scale-funding |
| [docs/10-branding-and-trademark.md](docs/10-branding-and-trademark.md) | Brand decision (FarmTwin) + trademark due diligence | branding |
| [docs/11-ksum-pitch-deck.md](docs/11-ksum-pitch-deck.md) | KSUM pitch deck — emotional + professional, 14 slides | pitch |
| [docs/12-moolathara-beachhead.md](docs/12-moolathara-beachhead.md) | Moolathara RBC immediate-win + opportunity sizing | pitch |
| [docs/13-pitch-narrative-and-one-pager.md](docs/13-pitch-narrative-and-one-pager.md) | 3-min spoken script, one-pager, elevator lines | pitch |
| [docs/14-partnership-mou-and-vendor-registration.md](docs/14-partnership-mou-and-vendor-registration.md) | Partner MoU template + govt vendor-registration checklist | pitch |
| [pitch/deck.html](pitch/deck.html) | Presentable reveal.js slide deck (now incl. command-area map) | pitch |
| [pitch/moolathara-map.svg](pitch/moolathara-map.svg) | Moolathara command-area schematic (standalone SVG) | pitch |
| [pitch/build_pptx.py](pitch/build_pptx.py) | Generates `FarmTwin-KSUM.pptx` (run: `pip install python-pptx; python pitch/build_pptx.py`) | pitch |

## Engine & design documents (FarmTwin Engine)

The deep-tech core — a self-calibrating irrigation hydraulic + agronomy engine, split
into two products (**FarmTwin Studio** pre-install, **FarmTwin Runtime**
operations) on one shared engine — lives under [`engine/`](engine/README.md).

- [engine/README.md](engine/README.md) — engine overview, install, and the full
  design-doc index (docs 10-22: solver math, sensors, digital twin, IoT/fertigation,
  optimization, agronomy).
- [engine/docs/19-two-product-architecture.md](engine/docs/19-two-product-architecture.md) — the two-product split and shared core.
- [engine/docs/22-implementation-whitepapers.md](engine/docs/22-implementation-whitepapers.md) — the key white papers per module, with summaries and links.

## Run the MVP & pitch deck

No build step. Open `mvp/index.html` or `pitch/pitch-deck.html` in any modern browser, or serve locally:

```bash
cd mvp
python -m http.server 8000
# MVP:        http://localhost:8000
# Pitch deck: http://localhost:8000/../pitch/pitch-deck.html
```

Export Marp deck to PDF/PPTX: see [pitch/README.md](pitch/README.md).

## Status legend

These documents are decision-ready drafts. Items requiring real-world action
(government portals, bank accounts, signatures) are clearly marked as
**[ACTION]** with the exact steps and inputs prepared in advance.
