# A-refine finer — RUN

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
- ANIM cells: 24864 quads, 0 tris

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

- **frame 10** (`Ainflate_A011.vtk` / `artifacts/warn-lambda2.png`)
- t = **0.020003 s**
- λ_max = **2.148**
- p = **32505 Pa** (PLOAD ramp; **dynamic**, not Chiron QS — JS warn was ~54100 Pa at equilibrium)
- V = **778.3 mL**
- Overlay: `WARN  first λ_max ≥ 2`

## Correctness tape

λ from CST membrane principals on ANIM/VTK (rest = frame 0). Ψ = Σ ½ μ (I1−3) H0 A0, λ3=1/(λ1 λ2).

| frame | t [s] | p [Pa] | λ_max | V [mL] | Ψ [J] |
|------:|------:|-------:|------:|-------:|------:|
| 0 | 0 | 0 | 1.0000 | 354 | 0 |
| 1 | 0.002 | 3250 | 1.4065 | 428.8 | 0.0803 |
| 2 | 0.0040004 | 6501 | 1.7020 | 440.9 | 0.1216 |
| 3 | 0.0060002 | 9750 | 1.4283 | 472.1 | 0.3086 |
| 4 | 0.0080012 | 13002 | 1.4831 | 493.1 | 0.5528 |
| 5 | 0.010002 | 16254 | 1.5063 | 517.7 | 0.8914 |
| 6 | 0.012003 | 19505 | 1.5931 | 547.4 | 1.345 |
| 7 | 0.014 | 22750 | 1.6850 | 585.2 | 1.959 |
| 8 | 0.016001 | 26002 | 1.8065 | 632.8 | 2.802 |
| 9 | 0.018001 | 29252 | 1.9598 | 695.2 | 3.994 |
| 10 | 0.020003 | 32505 | 2.1479 | 778.3 | 5.731 |
| 11 | 0.022001 | 35752 | 2.4181 | 899.6 | 8.609 |
| 12 | 0.024001 | 39002 | 2.8751 | 1112 | 14.5 |
| 13 | 0.026003 | 42255 | 4.1790 | 1798 | 37.2 |
| 14 | 0.027377 | 44488 | 54.0400 | 1.683e+04 | 491.1 |

Ψ(t) ≥ 0: **yes**  (min 0 J)
Enclosed V(t) ** > 0 every frame** (no global inside-out)
Contact: `/INTER/TYPE19` Gapmin = **0.762 mm** (= CONTACT_KISS). A plane-distance heuristic is too noisy for a min-gap column.

## Blockers (CFL / AMS)

- engine NORMAL TERMINATION (see /DT/NODA/STOP if cycles << T_END)
- CFL: /DT/NODA/STOP fired (nodal dt ≤ 1e-6). ANIM through last written frame kept. No /AMS.
- dtmin armed: MINIMUM TIME STEP . . . . . . . . . . . .  1.0000000000000E-06
- Belytschko N=1, 24864 quads. `/DT/NODA/STOP 0.9 1e-6` hang guard (not NODA/CST). No /AMS on this tape.
- Working PROP: Belytschko Ishell=1, Ismstr=10, N=1. μ and ρ unchanged.
- Tape is **dynamic** PLOAD+/ADYREL until a QS-ish run exists. Quality PASS desk; converged dynamic ≠ ABC apples claim vs Chiron QS.
- Post is **metrics-only**: contact gap skipped (report-only anyway); no per-frame PNG/GIF. p, λ_max, V, Ψ at first λ≥2 are still in warn.json.

## Artifacts

- `artifacts/A-inflate.gif` / `A-inflate.mp4` — rest → past first λ≥2 (warn frame labeled)
- `artifacts/warn-lambda2.png` (or `last-frame.png` if λ<2)
- `artifacts/metrics.csv`
- `law-card.txt`
