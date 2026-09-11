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

## ρ source

ρ = **1130 kg/m³** — Desmopan 85085A **ISO 1183-1**.
McMaster-Carr 1446T11 (85A film) **does not publish density**; the ISO 1183-1
Desmopan 85085A value is the desked label. Not invented, not retuned.

## λ ≥ 2 frame

- **frame 4** (`AinflateA005` / `artifacts/warn-lambda2.png`)
- t = **0.00800 s**
- λ_max = **2.224**
- p = **13007 Pa** (PLOAD ramp; **dynamic**, not Chiron QS — JS warn was ~54100 Pa at equilibrium)
- V = **487.2 mL** (rest 354 mL)
- Overlay: `WARN  first λ_max ≥ 2`

## Correctness tape

λ from CST membrane principals on ANIM/VTK (rest = frame 0). Ψ = Σ ½ μ (I1−3) H0 A0, λ3=1/(λ1 λ2).

| frame | t [s] | p [Pa] | λ_max | V [mL] | Ψ [J] |
|------:|------:|-------:|------:|-------:|------:|
| 0 | 0 | 0 | 1.000 | 354.0 | 0 |
| 1 | 0.00200 | 3251 | 1.223 | 410.1 | 0.089 |
| 2 | 0.00400 | 6506 | 1.394 | 442.1 | 0.517 |
| 3 | 0.00600 | 9755 | 1.747 | 467.3 | 0.886 |
| 4 | 0.00800 | 13007 | **2.224** | 487.2 | 1.561 |
| 5 | 0.01001 | 16260 | 2.708 | 509.6 | 2.561 |
| 6 | 0.01201 | 19510 | 3.177 | 534.5 | 3.960 |
| 7 | 0.01400 | 22760 | 3.615 | 563.5 | 5.852 |
| 8 | 0.01600 | 26000 | 4.022 | 598.1 | 8.417 |
| 9 | 0.01801 | 29260 | 4.429 | 641.8 | 12.02 |
| 10 | 0.02001 | 32520 | 4.891 | 699.9 | 16.00 |
| 11 | 0.02200 | 35750 | 5.417 | 782.6 | 17.73 |
| 12 | 0.02401 | 39010 | 6.147 | 923.4 | 24.67 |
| 13 | 0.02600 | 42250 | 7.191 | 1267 | 43.35 |
| 14 | 0.02800 | 45500 | 8.696 | 4351 | 149.3 |

- Ψ(t) ≥ 0: **yes** (min 0 J at rest)
- Enclosed V(t) **> 0** every frame (no global inside-out)
- Contact: `/INTER/TYPE19` Gapmin = **0.762 mm** (= CONTACT_KISS). A plane-distance heuristic is too noisy for a min-gap column (reports ~0 even at rest when a far face’s plane grazes a node). **No global punch-through through warn** (V>0, glyph still reads). Frame 14 is the CFL blow-up, not a kiss soften.

## Blockers (CFL / AMS)

- **Try-first QEPH (`Ishell=24`) + `Ismstr=10` ruptured at rest** with no PLOAD and no contact. Working first light: **Belytschko `Ishell=1`**, `Ismstr=10`, **N=1**.
- Natural CFL ≈ **1.33e-5 s**. `/DT/NODA/CST 0.9 1e-6` armed (added mass ~0 until the crash).
- Engine **CFL collapsed at t ≈ 28 ms** (dt ~ 1e-15, ERR=−99.9%). ANIM A001–A015 kept; A015 is the blow-up (V=4351 mL). **No `/AMS`.**
- First λ≥2 is **on the explicit dynamic tape** (8 ms, 13 kPa). Chiron QS warn (~54 kPa) is a different process; do not retune μ to match.

## Artifacts

- `artifacts/A-inflate.gif` / `A-inflate.mp4` — rest → past first λ≥2 (frame 4 labeled)
- `artifacts/warn-lambda2.png`
- `artifacts/metrics.csv`
- `law-card.txt`
