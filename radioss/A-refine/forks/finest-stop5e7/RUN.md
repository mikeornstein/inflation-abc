# A-refine finest STOP 5e-7 — RUN

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
- ANIM cells: 99456 quads, 0 tris

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

- **frame 9** (`Ainflate_A010.vtk` / `artifacts/warn-lambda2.png`)
- t = **0.018 s**
- λ_max = **2.137**
- p = **29250 Pa** (PLOAD ramp; **dynamic**, not Chiron QS — JS warn was ~54100 Pa at equilibrium)
- V = **693.4 mL**
- Overlay: `WARN  first λ_max ≥ 2`

## Correctness tape

λ from CST membrane principals on ANIM/VTK (rest = frame 0). Ψ = Σ ½ μ (I1−3) H0 A0, λ3=1/(λ1 λ2).

| frame | t [s] | p [Pa] | λ_max | V [mL] | Ψ [J] |
|------:|------:|-------:|------:|-------:|------:|
| 0 | 0 | 0 | 1.0000 | 354 | 0 |
| 1 | 0.002 | 3250 | 1.7145 | 425 | 0.05237 |
| 2 | 0.0040002 | 6500 | 1.6874 | 440.3 | 0.0962 |
| 3 | 0.006001 | 9752 | 1.5813 | 471.4 | 0.2881 |
| 4 | 0.0080006 | 13001 | 1.5195 | 492.2 | 0.5256 |
| 5 | 0.01 | 16250 | 1.6041 | 516.4 | 0.857 |
| 6 | 0.012001 | 19501 | 1.7074 | 546.2 | 1.305 |
| 7 | 0.014001 | 22751 | 1.8211 | 583.9 | 1.916 |
| 8 | 0.016001 | 26001 | 1.9633 | 631.3 | 2.749 |
| 9 | 0.018 | 29250 | 2.1370 | 693.4 | 3.927 |
| 10 | 0.02 | 32501 | 2.3513 | 776.2 | 5.651 |
| 11 | 0.022 | 35751 | 2.6529 | 897.2 | 8.511 |

Ψ(t) ≥ 0: **yes**  (min 0 J)
Enclosed V(t) ** > 0 every frame** (no global inside-out)
Contact: `/INTER/TYPE19` Gapmin = **0.762 mm** (= CONTACT_KISS). A plane-distance heuristic is too noisy for a min-gap column.

## Blockers (CFL / AMS)

- dtmin armed: MINIMUM TIME STEP . . . . . . . . . . . .  1.0000000000000E-06
- Belytschko N=1, 99456 quads. `/DT/NODA/STOP 0.9 1e-6` hang guard (not NODA/CST). No /AMS on this tape.
- Working PROP: Belytschko Ishell=1, Ismstr=10, N=1. μ and ρ unchanged.
- Tape is **dynamic** PLOAD+/ADYREL until a QS-ish run exists. Quality PASS desk; converged dynamic ≠ ABC apples claim vs Chiron QS.
- Post is **metrics-only**: contact gap skipped (report-only anyway); no per-frame PNG/GIF. p, λ_max, V, Ψ at first λ≥2 are still in warn.json.

## Artifacts

- `artifacts/A-inflate.gif` / `A-inflate.mp4` — rest → past first λ≥2 (warn frame labeled)
- `artifacts/warn-lambda2.png` (or `last-frame.png` if λ<2)
- `artifacts/metrics.csv`
- `law-card.txt`
