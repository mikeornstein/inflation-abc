# C /PLOAD proof

Letter **A** refine is accepted as-is. This note is **C only**. μ/ρ not retuned. No finest. Quad-only `/ADYREL`.

## Convention (Altair, not invented)

Positive `/PLOAD` in 3D acts along

$$n = (N_3-N_1)\times(N_4-N_2)$$

on the `/SURF` segment (`/SURF/PART` = `/SHELL` winding). Outward = **out of the enclosed volume**. A global `V<0` flip is not enough: same-direction interior edges mean a patch of `/SHELL` is reversed, so `+PLOAD` on those faces pushes *into* V. Count = BFS orientation vs that outward winding. C is a closed genus-0 extrusion (euler 2).

Deck card (2024 fields): `surf_ID fct_IDT sens_ID Ipinch Idel Itypfun Ascale_x Fscale_y`. Direction is the segment normal; there is no Idir on `/PLOAD`.

## 1) Inward vs outward

| density | N | faces | outward | inward | degenerate | manifold same-dir | V mL (as-wound) | V mL if oriented |
|---------|--:|------:|--------:|-------:|-----------:|------------------:|----------------:|-----------------:|
| ship | 988 | 986 | **780** | **206** | 0 | 416 | 385.8 | 448.2 |
| fine | 3946 | 3944 | **3120** | **824** | 0 | 832 | 385.8 | 448.2 |
| finer | 15778 | 15776 | **12480** | **3296** | 0 | 1664 | 385.8 | 448.2 |

**Inward faces found (side-wall patch).** Glyphs: green = +PLOAD out of V, red = inward. Next step on this PR: flip those quads, regenerate **C ship/fine/finer only**, re-run. μ/ρ unchanged. No finest. A not relaunched.

Glyph stills: green = +PLOAD out of enclosed V. Same camera as the C refine ladder (`az=0.55 el=0.38`). Frames are rest (`Ainflate_A001.vtk`) and the refine-ladder pressures (`A011` ≈ 32.5 kPa, `A012` ≈ 35.8 kPa).

## 2) TYPE19 — field that actually exists

Engine ANIM listing on these tapes:

- `CONTACT FORCES` = 1 → VTK `VECTORS Contact_Forces` (`/ANIM/VECT/CONT`)
- `CONTACT PRESSURE (VECTORS)` = 0 → **no PCONT**
- no gap scalar in VTK

`/TH/INTER DEF` is in the starter but the T01 file was not kept in `run/` (VTK-only). Time history below is **Contact_Forces** from every ANIM VTK, plus engine INTER / REMOVE SECONDARY.

| density | first |CONT|>0 | first INTER limiting | first REMOVE SECONDARY | n REMOVE |
|---------|------:|---------------------:|----------------------:|---------:|
| ship | 28.61 ms (Ainflate_A016.vtk) | 5.24 ms | 28.43 ms | 68 |
| fine | 28.55 ms (Ainflate_A016.vtk) | 27.26 ms | 28.47 ms | 651 |
| finer | 28.40 ms (Ainflate_A016.vtk) | 27.98 ms | 28.35 ms | 94 |

First kiss = first ANIM frame where max |Contact_Forces| exceeds **1 N** (TYPE19 self-collapse, not Inacti dust). Finer can show 0.02–0.1 N trace from t≈2 ms with no node above 0.1 N — not a kiss. Stills at the 1 N frame are `*_first_kiss_cont.png`.

Heuristic `contact_gap` in `radioss_post.py` is **not** TYPE19 — not used here.

## Locks

LAW42 μ₁=(800×6894.757)/1.75, α₁=2, ρ=1130, H0, Gapmin=CONTACT_KISS, Ishell=1 N=1 Ismstr=10, `/ADYREL`, `/PLOAD` 0→65 kPa in 0.04 s, `/DT/NODA/STOP`. No finest. No merge. No retarget.

## Reproduce

```bash
python3 tools/c_pload_proof.py --root radioss/C-refine --out radioss/C-pload-proof
```

