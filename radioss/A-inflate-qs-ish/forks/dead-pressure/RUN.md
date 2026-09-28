# A-inflate QS-ish dead-pressure 54100 Pa — RUN

Cloud VM job. OpenRadioss linux64_gf (`latest-20260728`). SI deck. **μ and ρ not retuned.**

**Load family `qs-ish-dead-pressure`** — QS-ish slower `/PLOAD` + `/ADYREL`. Not `dynamic-pload-40ms` (that tape first λ≥2 at ~36 kPa). Not a μ/ρ retune.

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
  /PLOAD  0 → 54100 Pa in 0.001 s, hold to 0.08 s (not MONVOL)
  loadFamily = qs-ish-dead-pressure
```

## Quad-only (no triangle bleed)

- Inflate part is **`/SHELL` only**. No `/SH3N`.
- Ship `meshes/A.json` midplane is already quad (`nMidTris=0`); **not remeshed to tris**.
- 28 orphan cap `faceTris` are **paired along shared edges into 14 quads** at convert time (same V0).
- ANIM/VTK + GIF/warn still are drawn as **nice quads** (uniform fill per shell + perimeter edges; no CST diagonal).
- ANIM cells: 1554 quads, 0 tris

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

- **frame 1** (`Ainflate_A002.vtk` / `artifacts/warn-lambda2.png`)
- t = **0.0020015 s**
- λ_max = **5.213**
- p = **54100 Pa** (PLOAD ramp `qs-ish-dead-pressure`; **QS-ish** (target ABC warn class ~54100 Pa). Dynamic `dynamic-pload-40ms` first λ≥2 was ~35769 Pa.)
- V = **3827 mL**
- Ψ = **126.5 J**
- mesh fingerprint = `d9c56487`
- Overlay: `WARN  first λ_max ≥ 2`

## Load family vs dynamic

| | dynamic-pload-40ms | this tape |
|---|---:|---:|
| loadFamily | `dynamic-pload-40ms` | `qs-ish-dead-pressure` |
| /PLOAD | 0→65000 Pa in 0.04 s | 0→54100 Pa in 0.001 s |
| μ₁ / ρ / H0 | locked | **same lock** (not retuned) |
| /ADYREL | yes | yes |
| first λ≥2 p | 35769 Pa | **54100 Pa** |
| first λ≥2 λ_max | 2.1404 | **5.213** |
| first λ≥2 V | 901.8 mL | **3827 mL** |

Do not mix families in one Themis table. web-mbd `compare:inflate` stays the dynamic gate. This golden is for `compare:inflate:qs` after Daedalus accepts the load-family tag (today the toy lock is `qs-ish-dead-pressure` with pMax=54100, tRamp=0 — ingest notes in README).

## Correctness tape

λ from CST membrane principals on ANIM/VTK (rest = frame 0). Ψ = Σ ½ μ (I1−3) H0 A0, λ3=1/(λ1 λ2).

| frame | t [s] | p [Pa] | λ_max | V [mL] | Ψ [J] |
|------:|------:|-------:|------:|-------:|------:|
| 0 | 0 | 0 | 1.0000 | 354 | 0 |
| 1 | 0.0020015 | 54100 | 5.2129 | 3827 | 126.5 |
| 2 | 0.002476 | 54100 | 15.0187 | 2.951e+04 | 740 |

Ψ(t) ≥ 0: **yes**  (min 0 J)
Enclosed V(t) ** > 0 every frame** (no global inside-out)
Contact: `/INTER/TYPE19` Gapmin = **0.762 mm** (= CONTACT_KISS). A plane-distance heuristic is too noisy for a min-gap column.

## Blockers (CFL / AMS)

- engine NORMAL TERMINATION (see /DT/NODA/STOP if cycles << T_END)
- CFL: /DT/NODA/STOP fired (nodal dt ≤ 1e-6). ANIM through last written frame kept. No /AMS.
- dtmin armed: MINIMUM TIME STEP . . . . . . . . . . . .  1.0000000000000E-06
- Belytschko N=1, 1554 quads. `/DT/NODA/STOP 0.9 1e-6` hang guard (not NODA/CST). No /AMS on this tape.
- Working PROP: Belytschko Ishell=1, Ismstr=10, N=1. μ and ρ unchanged.
- Tape is **QS-ish** `qs-ish-dead-pressure`: slower `/PLOAD` 0→54100 Pa in 0.001 s + `/ADYREL`. Distinct from `dynamic-pload-40ms` (first λ≥2 ≈ 36 kPa). Not a true implicit static solve. Do not retune μ.
- At first λ≥2: p=54100 Pa vs ABC QS ~54100 Pa (rel 0.0%) and vs dynamic 35769 Pa.

## Artifacts

- `artifacts/A-inflate.gif` / `A-inflate.mp4` — rest → past first λ≥2 (warn frame labeled)
- `artifacts/warn-lambda2.png` (or `last-frame.png` if λ<2)
- `artifacts/metrics.csv` / `metrics.json` / `warn.json`
- `artifacts/inflate-a-radioss-qs-golden.json` — freeze-frame golden for web-mbd `compare:inflate:qs`
- `law-card.txt`
