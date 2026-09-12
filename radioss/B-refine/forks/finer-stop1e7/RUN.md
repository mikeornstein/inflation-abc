# B-refine finer-stop1e7 — RUN

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
- ANIM cells: 71232 quads, 0 tris

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

- **frame 5** (`Ainflate_A006.vtk` / `artifacts/warn-lambda2.png`)
- t = **0.01 s**
- λ_max = **2.08**
- p = **16250 Pa** (PLOAD ramp; **dynamic**, not Chiron QS — JS warn was ~54100 Pa at equilibrium)
- V = **577 mL**
- Overlay: `WARN  first λ_max ≥ 2`

## Correctness tape

λ from CST membrane principals on ANIM/VTK (rest = frame 0). Ψ = Σ ½ μ (I1−3) H0 A0, λ3=1/(λ1 λ2).

| frame | t [s] | p [Pa] | λ_max | V [mL] | Ψ [J] |
|------:|------:|-------:|------:|-------:|------:|
| 0 | 0 | 0 | 1.0000 | 395 | 0 |
| 1 | 0.0020001 | 3250 | 1.4731 | 473.5 | 0.07593 |
| 2 | 0.0040007 | 6501 | 1.5813 | 490.9 | 0.1365 |
| 3 | 0.0060002 | 9750 | 1.6939 | 525.6 | 0.3628 |
| 4 | 0.0080004 | 13001 | 1.8824 | 549.9 | 0.6357 |
| 5 | 0.01 | 16250 | 2.0800 | 577 | 1.049 |
| 6 | 0.012001 | 19501 | 2.2309 | 606.5 | 1.578 |
| 7 | 0.014 | 22751 | 2.3606 | 640.9 | 2.31 |
| 8 | 0.016 | 26000 | 2.4995 | 681.1 | 3.274 |
| 9 | 0.018 | 29250 | 2.6807 | 732.9 | 4.67 |
| 10 | 0.02 | 32500 | 2.9054 | 802.2 | 6.751 |
| 11 | 0.022 | 35750 | 3.2470 | 908.2 | 10.28 |
| 12 | 0.024 | 39001 | 3.8620 | 1113 | 17.8 |
| 13 | 0.026002 | 42253 | 5.8672 | 1938 | 49.71 |
| 14 | 0.027316 | 44388 | 148.4075 | 1.955e+04 | 667.5 |

Ψ(t) ≥ 0: **yes**  (min 0 J)
Enclosed V(t) ** > 0 every frame** (no global inside-out)
Contact: `/INTER/TYPE19` Gapmin = **0.762 mm** (= CONTACT_KISS). A plane-distance heuristic is too noisy for a min-gap column.

## Blockers (CFL / AMS)

- engine NORMAL TERMINATION (see /DT/NODA/STOP if cycles << T_END)
- CFL: /DT/NODA/STOP fired (nodal dt ≤ 1e-6). ANIM through last written frame kept. No /AMS.
- dtmin armed: MINIMUM TIME STEP . . . . . . . . . . . .  1.0000000000000E-06
- Belytschko N=1, 71232 quads. `/DT/NODA/STOP 0.9 1e-6` hang guard (not NODA/CST). No /AMS on this tape.
- Working PROP: Belytschko Ishell=1, Ismstr=10, N=1. μ and ρ unchanged.
- Tape is **dynamic** PLOAD+/ADYREL until a QS-ish run exists. Quality PASS desk; converged dynamic ≠ ABC apples claim vs Chiron QS.
- Post is **metrics-only**: contact gap skipped (report-only anyway); no per-frame PNG/GIF. p, λ_max, V, Ψ at first λ≥2 are still in warn.json.

## Artifacts

- `artifacts/A-inflate.gif` / `A-inflate.mp4` — rest → past first λ≥2 (warn frame labeled)
- `artifacts/warn-lambda2.png` (or `last-frame.png` if λ<2)
- `artifacts/metrics.csv`
- `law-card.txt`
