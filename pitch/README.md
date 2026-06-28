# FarmTwin — Pitch Materials

Synced presentation assets for KSUM Idea Grant, AgriNext/KERA, and GAAM Demo Day.
All content aligns with `docs/01`–`07` and the live MVP.

## Files

| File | Format | Use |
| --- | --- | --- |
| [pitch-deck.md](pitch-deck.md) | **Marp** (Markdown slides) | Source; export via `npm run build` in this folder |
| [pitch-deck.html](pitch-deck.html) | **HTML slides** (browser) | Open directly; arrow keys / space to navigate |
| [pitch-deck.pdf](pitch-deck.pdf) | **PDF** (exported) | Attach to applications, email |
| [pitch-deck.pptx](pitch-deck.pptx) | **PowerPoint** (exported) | Edit in PowerPoint / Google Slides |
| [one-pager.md](one-pager.md) | **One-pager** (Markdown) | Attach to KSUM profile, email intros, print to PDF |
| [pitch-script.md](pitch-script.md) | **Talk track** | 5–7 min script synced with deck slides |

## Export commands

### Marp → PDF / PPTX / HTML

```bash
cd pitch
npm install          # first time only
npm run build        # generates pitch-deck.pdf, .pptx, pitch-deck-marp.html
```

### One-pager → PDF

```bash
# any Markdown-to-PDF tool, e.g. pandoc:
pandoc one-pager.md -o one-pager.pdf
```

### HTML deck

No build step. Open `pitch-deck.html` in any modern browser.

## Key pitch messages (synced everywhere)

1. **Hook:** Canal water arrived → scheduling is the bottleneck.
2. **Product:** Simulation-driven digital twin (mesh + solver), not an IoT dashboard.
3. **Proof:** MVP shows ≥30% water saving vs flood at protected yield.
4. **Moat:** 20 years CAE/simulation + owned 15-acre pilot farm.
5. **GTM:** FPO beachhead via AgriNext → Krishi Bhavan scale via **GAAM** (≤ Rs.50L ex-GST, no tender).
6. **Ask:** Idea Grant Rs.3L + AgriNext pilot + FPO/GAAM introductions.

## Source of truth

When updating pitch content, edit in this order and keep in sync:

1. `docs/02-problem-statement.md` (problem, GTM, GAAM section)
2. `docs/04-ksum-idea-grant-application.md` (portal copy + talking points)
3. `pitch/*` (all presentation formats)
4. `mvp/index.html` (demo + pitch snapshot panel)
