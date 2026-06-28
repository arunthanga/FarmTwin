# FarmTwin Pitch Deck

A 13-slide investor/grant pitch deck for **FarmTwin**, synthesised from the
venture and engine documents in this repository (`docs/`, `engine/docs/`).

## Files

| File | Open with |
| --- | --- |
| [`FarmTwin-pitch.pdf`](FarmTwin-pitch.pdf) | Any PDF viewer / browser |
| [`FarmTwin-pitch.pptx`](FarmTwin-pitch.pptx) | PowerPoint, Keynote, Google Slides, LibreOffice Impress |
| [`build_deck.py`](build_deck.py) | The generator (single source of slide content) |

## Slides

1. Title
2. The Problem
3. Quantified Pain
4. The Solution
5. Why It's Defensible (CAE-to-agri skill map)
6. Two Products, One Shared Engine
7. Product & MVP
8. Market & Beachhead
9. Why Now
10. Pilot & Traction Plan
11. Funding Roadmap
12. Use of Funds & The Ask
13. Closing

## Regenerate

Both formats are rendered from the same `SLIDES` content list, so edits stay in
sync. To rebuild after editing `build_deck.py`:

```bash
pip install python-pptx reportlab
python build_deck.py
```
