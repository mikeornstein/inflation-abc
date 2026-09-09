# Design bar — A·B·C block letters (Mike redo 2026-09-06)

**Supersedes** flat-outline PASS and prior **10 cm** extrude packs (incl. A PASS at 10 cm).

## Feeling (locked)
**Feeling lock / valid state = warn (first λ≥2)** — not soft mid. Mid optional. Raise-mid for lock cancelled (Mike 2026-09-06).

**Balloon / fat-round vibe** — Mike’s bubbly ref is **vibe, not exact glyphs**. Grade: heavy rounded limbs, soft terminals, generous open counters, almost no sharp corners.

Pipeline: **DynaPuff** (OFL) outlines → extrude **5 cm** **hollow film shell** → pressure inflate into softer film.

## Camera
Letters **upright** in the viewport (beauty pitch near flat — no lean). Grade fail if the glyph tips.

## Type (try-first locked)
| Face | License | Role |
|------|---------|------|
| **DynaPuff** | SIL Open Font License | **Try-first** |

Fallbacks (Design fail only): Chicle, then Fredoka. No Microsoft Comic Sans binaries.

## Stills to grade (per letter)
| Beat | What |
|------|------|
| **01 block rest** | **5 cm** hollow block at P=0 — upright; fat-round; Semi-Clear White; no special seam paint |
| **02 mid** | Optional — not feeling lock |
| **03 warn** | **Feeling lock / valid state** — first λ≥2; upright; glyph must still read; kiss + thickness→opacity |

## Contact (Mike 2026-09-06)
- Lobes / front-back **kiss** — **0-distance contact OK**.
- Visible standoff (e.g. 6 mm air gap) **fails the feel**.
- Punch-through / face intersection **fails**.
- Contact ≠ wrinkle (Chiron): contact stops faces punching through; wrinkle kills in-plane compression.

## Mesh (Mike 2026-09-06)
- Film mesh: **coarse beautiful quads with flow** — not dense DelQuad mush.
- Tris only if needed.
- Continuous shell (no open seams / faces disconnected from edges).
- Kiss look at warn (soft press, no punch-through).
- Kill: dense no-flow remesh that reads as noise under inflate.

## FILM-BAR (Mike 2026-09-06)
- Semi-Clear White · IOR **1.53** (±0.02) estimate · soft industrial gloss
- **No special seam/edge treatment** — do not paint or fake ridges/seams
- **Opacity from thickness** — thinner membrane = more transparent; thicker = more opaque
- Local thickness: **h = H₀ / (λ₁ λ₂)** (Daedalus) — opacity tracks local h, not a constant alpha
- h₀ 0.381 mm · McMaster 1446T11 85A · same μ grill / neo-Hookean / wrinkle
- Kill: wireframe-as-final · opaque plastic · frosted acrylic · optical-clear Estane · solid brick · leaning camera · fake edge chrome · constant opacity ignoring thickness
- Wire OFF on beauty stills
- Local only until Mike says public

## Grade scope (Mike 2026-09-06)
- Design grades **kiss + continuous film** on the **quad path** at warn.
- **Ignore tri-vs-quad Δ** — do not fail because quad ≠ tri-split.
- Ask: does the quad bake look like correct pressurized film?

## Grade when stills land
**Current Design:** A warn **PASS** holds post-pforce (`DESIGN-GRADE-QUADMEM-A-WARN.md` · P54100 V≈1194). Hold B/C. Local only.
