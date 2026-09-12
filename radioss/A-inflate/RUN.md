# A-inflate first light — RUN

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
- ANIM cells: 1554 quads, 0 tris
- Starter listing: `NUMELC=1554` 4-node shells, `NUMELTG=0` 3-node, `NUMBCS=0`

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
- t = **0.022012 s**
- λ_max = **2.14**
- p = **35769 Pa** (PLOAD ramp; **dynamic**, not Chiron QS — JS warn was ~54100 Pa at equilibrium)
- V = **901.8 mL**
- Overlay: `WARN  first λ_max ≥ 2`

## Correctness tape

λ from CST membrane principals on ANIM/VTK (rest = frame 0). Ψ = Σ ½ μ (I1−3) H0 A0, λ3=1/(λ1 λ2).

| frame | t [s] | p [Pa] | λ_max | V [mL] | Ψ [J] |
|------:|------:|-------:|------:|-------:|------:|
| 0 | 0 | 0 | 1.0000 | 354 | 0 |
| 1 | 0.0020219 | 3286 | 1.3130 | 432.4 | 0.2379 |
| 2 | 0.0040116 | 6519 | 1.6245 | 421.3 | 0.6375 |
| 3 | 0.006013 | 9771 | 1.4070 | 475.8 | 0.7572 |
| 4 | 0.0080131 | 13021 | 1.4740 | 500.5 | 0.9466 |
| 5 | 0.010014 | 16272 | 1.5529 | 524.1 | 1.309 |
| 6 | 0.012007 | 19512 | 1.5357 | 554.1 | 1.79 |
| 7 | 0.014022 | 22785 | 1.5647 | 592.1 | 2.49 |
| 8 | 0.016004 | 26007 | 1.6369 | 638.2 | 3.4 |
| 9 | 0.018021 | 29285 | 1.7542 | 699.2 | 4.667 |
| 10 | 0.020004 | 32506 | 1.9158 | 780.9 | 6.493 |
| 11 | 0.022012 | 35769 | 2.1404 | 901.8 | 9.502 |
| 12 | 0.024013 | 39022 | 2.5225 | 1112 | 15.51 |
| 13 | 0.026003 | 42255 | 3.5664 | 1754 | 37.08 |
| 14 | 0.027673 | 44968 | 60.9733 | 4.839e+04 | 1700 |

Ψ(t) ≥ 0: **yes**  (min 0 J)
Enclosed V(t) ** > 0 every frame** (no global inside-out)
Contact: `/INTER/TYPE19` Gapmin = **0.762 mm** (= CONTACT_KISS). A plane-distance heuristic is too noisy for a min-gap column.

## Blockers (CFL / AMS)

- engine **NORMAL TERMINATION** via `/DT/NODA/STOP` (nodal dt ≤ 1e-6 at t≈27.7 ms). ANIM through frame 14 kept. **No `/AMS`.**
- Natural CFL ~2.3e-5 s (Belytschko N=1, 1554 quads). First-light `/DT/NODA/CST` added mass but still hung at dt~1e-15; STOP is the hang guard, not a μ/ρ retune.
- Try-first QEPH (`Ishell=24`)+`Ismstr=10` ruptured at rest. Working first light: **Belytschko `Ishell=1`**, `Ismstr=10`, **N=1**.
- `/ADYREL` damps the explicit tape: first λ≥2 is **frame 11 / 22 ms / 36 kPa** (undamped 3-2-1 first light was 8 ms / 13 kPa). Still **dynamic**, not Chiron QS (~54 kPa). Do not retune μ.
- Frame 14 is the CFL blow-up (λ=61, V=48 L); GIF/MP4 stop before that frame.

## Artifacts

- `artifacts/A-inflate.gif` / `A-inflate.mp4` — rest → past first λ≥2 (warn frame labeled)
- `artifacts/warn-lambda2.png` (or `last-frame.png` if λ<2)
- `artifacts/metrics.csv`
- `law-card.txt`
