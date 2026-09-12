# A-refine fine — RUN

Cloud VM job. OpenRadioss linux64_gf (`latest-20260728`). SI deck. **μ and ρ not retuned.**

## Law card dump
```
LAW42 neo-Hookean (Ogden 1-term)
  μ1      = 3151888.914285714 Pa   # grill eng. μ = (800 * 6894.757) / 1.75 ; not invented
  α1      = 2
  μp,αp   = 0 for p=2..10
  ν       = 0.495  (≤ 0.495)
  M       = 0  (no Prony)
  Iform   = 1 (standard Ogden SED)
  H0      = 0.000381 m  (0.015*0.0254)
  ρ       = 1130 kg/m^3  # Desmopan 85085A ISO 1183-1; McMaster 1446T11 density not published
  Gapmin  = 0.000762 m  # CONTACT_KISS = max(2*H0, 1e-4)
  WARN_LAM= 2
  /PROP   N=1  Ismstr=10  Ishell=1 (Belytschko)  Ithick=1
  /INTER/TYPE19  Igap=4  Irem_gap=2  Inacti=6  Gapmin=CONTACT_KISS
  /PLOAD  0 → 65000 Pa in 0.04 s (not MONVOL)
```

## Quad-only (no triangle bleed)

- Inflate part is **`/SHELL` only**. No `/SH3N`.
- Ship `meshes/A.json` midplane is already quad (`nMidTris=0`); **not remeshed to tris**.
- 28 orphan cap `faceTris` are **paired along shared edges into 14 quads** at convert time (same V0).
- ANIM/VTK + GIF/warn still are drawn as **nice quads** (uniform fill per shell + perimeter edges; no CST diagonal).
- ANIM cells: 6216 quads, 0 tris

## Inertial relief / free-free

- **No `/BCS`** — 3-2-1 grounded nodes dropped.
- OpenRadioss explicit analogue of inertial relief is engine **`/ADYREL`** (adaptive dynamic relaxation).
- Radioss has **no `PARAM,INREL`** (that is OptiStruct). Closed `/PLOAD` on a watertight shell is self-equilibrated (net F≈0).
- Kept starter **`/DAMP`** Rayleigh mass α=80 1/s as residual rigid-body sink.

## ρ source

ρ = **1130 kg/m³** — Desmopan 85085A **ISO 1183-1**.
McMaster-Carr 1446T11 (85A film) **does not publish density**; the ISO 1183-1
Desmopan 85085A value is the desked label. Not invented, not retuned.

## λ ≥ 2 frame

- **frame 11** (`Ainflate_A012.vtk` / `artifacts/warn-lambda2.png`)
- t = **0.022007 s**
- λ_max = **2.23**
- p = **35762 Pa** (PLOAD ramp; **dynamic**, not Chiron QS — JS warn was ~54100 Pa at equilibrium)
- V = **901.5 mL**
- Overlay: `WARN  first λ_max ≥ 2`

## Correctness tape

λ from CST membrane principals on ANIM/VTK (rest = frame 0). Ψ = Σ ½ μ (I1−3) H0 A0, λ3=1/(λ1 λ2).

| frame | t [s] | p [Pa] | λ_max | V [mL] | Ψ [J] |
|------:|------:|-------:|------:|-------:|------:|
| 0 | 0 | 0 | 1.0000 | 354 | 0 |
| 1 | 0.0020033 | 3255 | 1.4022 | 431.8 | 0.1445 |
| 2 | 0.0040002 | 6500 | 1.6856 | 441.5 | 0.2113 |
| 3 | 0.0060045 | 9757 | 1.5263 | 472.8 | 0.3782 |
| 4 | 0.0080029 | 13005 | 1.4704 | 494.1 | 0.6282 |
| 5 | 0.010007 | 16261 | 1.4400 | 518.9 | 0.9746 |
| 6 | 0.012005 | 19509 | 1.5111 | 548.8 | 1.434 |
| 7 | 0.014006 | 22760 | 1.5906 | 586.6 | 2.059 |
| 8 | 0.016007 | 26011 | 1.6968 | 634.5 | 2.915 |
| 9 | 0.018008 | 29263 | 1.8263 | 697.2 | 4.126 |
| 10 | 0.020007 | 32511 | 1.9920 | 780.2 | 5.876 |
| 11 | 0.022007 | 35762 | 2.2302 | 901.5 | 8.776 |
| 12 | 0.024007 | 39012 | 2.6404 | 1113 | 14.69 |
| 13 | 0.026007 | 42261 | 3.8062 | 1785 | 37 |
| 14 | 0.027457 | 44618 | 35.0119 | 2.181e+04 | 578.2 |

Ψ(t) ≥ 0: **yes**  (min 0 J)
Enclosed V(t) ** > 0 every frame** (no global inside-out)
Contact: `/INTER/TYPE19` Gapmin = **0.762 mm** (= CONTACT_KISS). A plane-distance heuristic is too noisy for a min-gap column.

## Blockers (CFL / AMS)

- engine NORMAL TERMINATION (see /DT/NODA/STOP if cycles << T_END)
- CFL: /DT/NODA/STOP fired (nodal dt ≤ 1e-6). ANIM through last written frame kept. No /AMS.
- dtmin armed: MINIMUM TIME STEP . . . . . . . . . . . .  1.0000000000000E-06
- Belytschko N=1, 6216 quads. `/DT/NODA/STOP 0.9 1e-6` hang guard (not NODA/CST). No /AMS on this tape.
- Working PROP: Belytschko Ishell=1, Ismstr=10, N=1. μ and ρ unchanged.
- Tape is **dynamic** PLOAD+/ADYREL until a QS-ish run exists. Converged dynamic ≠ ABC apples claim vs Chiron QS.

## Artifacts

- `artifacts/A-inflate.gif` / `A-inflate.mp4` — rest → past first λ≥2 (warn frame labeled)
- `artifacts/warn-lambda2.png` (or `last-frame.png` if λ<2)
- `artifacts/metrics.csv`
- `law-card.txt`
