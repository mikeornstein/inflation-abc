# C /PLOAD proof

Letter **A** refine is accepted as-is. This note is **C only**. μ/ρ not retuned. No finest. Quad-only `/ADYREL`.

## Convention (Altair, not invented)

Positive `/PLOAD` in 3D acts along

$$n = (N_3-N_1)\times(N_4-N_2)$$

on the `/SURF` segment (`/SURF/PART` = `/SHELL` winding). Outward = **out of the enclosed volume**. A global `V<0` flip is not enough: same-direction interior edges mean a patch of `/SHELL` is reversed, so `+PLOAD` on those faces pushes *into* V. Count = BFS orientation vs that outward winding. C is a closed genus-0 extrusion (euler 2).

Deck card (2024 fields): `surf_ID fct_IDT sens_ID Ipinch Idel Itypfun Ascale_x Fscale_y`. Direction is the segment normal; there is no Idir on `/PLOAD`.

## 1) Inward vs outward

### Before the side-wall flip

| density | N | faces | outward | inward | degenerate | manifold same-dir | V mL (as-wound) | V mL if oriented |
|---------|--:|------:|--------:|-------:|-----------:|------------------:|----------------:|-----------------:|
| ship | 988 | 986 | **780** | **206** | 0 | 416 | 385.8 | 448.2 |
| fine | 3946 | 3944 | **3120** | **824** | 0 | 832 | 385.8 | 448.2 |
| finer | 15778 | 15776 | **12480** | **3296** | 0 | 1664 | 385.8 | 448.2 |

All inward faces were **extrusion side-walls** (nested 1-to-4 inherited the ship patch: 206 / 824 / 3296). Those faces pushed **into** enclosed V.

### After `orient_outward_closed` (this tape)

| density | N | faces | outward | inward | degenerate | manifold same-dir | V mL (as-wound) | V mL if oriented |
|---------|--:|------:|--------:|-------:|-----------:|------------------:|----------------:|-----------------:|
| ship | 988 | 986 | **986** | **0** | 0 | 0 | 448.2 | 448.2 |
| fine | 3946 | 3944 | **3944** | **0** | 0 | 0 | 448.2 | 448.2 |
| finer | 15778 | 15776 | **15776** | **0** | 0 | 0 | 448.2 | 448.2 |

**Zero inward faces** on ship, fine, and finer (manifold-consistent, V>0). `/PLOAD` n agrees with the outward shell winding.

`anim_to_vtk` used to skip existing VTK; a shorter re-run then mixed leftover A0xx frames. Post now drops ANIM/VTK older than the copied engine `.rad` and reconverts when ANIM is newer.

Glyph stills: green = +PLOAD out of enclosed V. Same camera as the C refine ladder (`az=0.55 el=0.38`). Frames are rest (`Ainflate_A001.vtk`) and the refine-ladder pressures (`A011` ≈ 32.5 kPa, `A012` ≈ 35.8 kPa). On the outward tape, **35.8 kPa is a CFL blow-up** (λ tens, V tens of litres) — labeled as such.

### Same-load after the flip (honest VTK)

| N | density | t [ms] | p [kPa] | λ_max | λ_aw | V [mL] | Ψ [J] |
|--:|---------|-------:|--------:|------:|-----:|-------:|------:|
| 988 | ship | 20.01 | 32.5 | 2.822 | 1.5505 | 1720.5 | 30.1 |
| 3946 | fine | 20.00 | 32.5 | 2.982 | 1.5326 | 1751.1 | 30.3 |
| 15778 | finer | 20.00 | 32.5 | 3.234 | 1.5305 | 1779.1 | 31 |

32.5 kPa ship→fine ΔV = **1.78%**. Mixed-winding tapes had ship **1806 mL** vs fine **1425 mL** — that gap was the inward side-wall patch, not coarseness alone.

35.8 kPa (`A012`) on this outward tape is **CFL blow-up** (ship λ_max=18.9, fine λ_max=57.5). Not a grade station. Hang guard `/DT/NODA/STOP` fires immediately after. μ/ρ not retuned.


## 2) TYPE19 — field that actually exists

Engine ANIM listing on these tapes:

- `CONTACT FORCES` = 1 → VTK `VECTORS Contact_Forces` (`/ANIM/VECT/CONT`)
- `CONTACT PRESSURE (VECTORS)` = 0 → **no PCONT**
- no gap scalar in VTK

`/TH/INTER DEF` is in the starter but the T01 file was not kept in `run/` (VTK-only). Time history below is **Contact_Forces** from every ANIM VTK, plus engine INTER / REMOVE SECONDARY.

| density | first |CONT|>0 | first INTER limiting | first REMOVE SECONDARY | n REMOVE |
|---------|------:|---------------------:|----------------------:|---------:|
| ship | none | 5.85 ms | 22.15 ms | 33 |
| fine | 2.00 ms (Ainflate_A002.vtk) | 21.35 ms | 21.91 ms | 20 |
| finer | none | 21.47 ms | 21.80 ms | 74 |

First ANIM |Contact_Forces| > **1 N** is the TYPE19 field (not invented). On this outward tape that event is **fine A002 t=2.00 ms**: 14 nodes, 2.15 N on the **inner hole** (Gapmin), not a film folding onto itself. CONT is **0** at 32.5 kPa on all three densities. Ship never exceeds 1 N. Finer INTER-limits at 21.5 ms as the balloon CFL-blows; no ANIM |CONT|>1 N. Mixed-winding self-collapse at A016 ~28 ms does not appear — `/DT/NODA/STOP` fires at ~22 ms.

Heuristic `contact_gap` in `radioss_post.py` is **not** TYPE19 — not used here.

## Locks

LAW42 μ₁=(800×6894.757)/1.75, α₁=2, ρ=1130, H0, Gapmin=CONTACT_KISS, Ishell=1 N=1 Ismstr=10, `/ADYREL`, `/PLOAD` 0→65 kPa in 0.04 s, `/DT/NODA/STOP`. No finest. No merge. No retarget. Finer vanilla STOP 1e-6 CFL'd at t≈2 ms; working tape `radioss/C-refine/forks/finer-stop5e7` (STOP Tmin=5e-7, not CST).

## Reproduce

```bash
python3 tools/c_pload_proof.py --root radioss/C-refine --out radioss/C-pload-proof
```

