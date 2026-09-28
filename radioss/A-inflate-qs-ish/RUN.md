# A-inflate QS-ish (qs-ish-pload-400ms) — RUN

Cloud VM job. OpenRadioss linux64_gf (`latest-20260728`). SI deck. **μ and ρ not retuned.**

**Load family `qs-ish-pload-400ms`** — QS-ish slower `/PLOAD` + `/ADYREL`. Not `dynamic-pload-40ms` (that tape first λ≥2 at ~36 kPa). Not a μ/ρ retune.

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
  /PLOAD  0 → 65000 Pa in 0.4 s, hold to 0.5 s (not MONVOL)
  loadFamily = qs-ish-pload-400ms
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

- **frame 34** (`Ainflate_A035.vtk` / `artifacts/warn-lambda2.png`)
- t = **0.17 s**
- λ_max = **2.327**
- p = **27625 Pa** (PLOAD ramp `qs-ish-pload-400ms`; **QS-ish** (target ABC warn class ~54100 Pa). Dynamic `dynamic-pload-40ms` first λ≥2 was ~35769 Pa.)
- V = **752.6 mL**
- Ψ = **8.043 J**
- mesh fingerprint = `d9c56487`
- Overlay: `WARN  first λ_max ≥ 2`

## Load family vs dynamic

| | dynamic-pload-40ms | this tape |
|---|---:|---:|
| loadFamily | `dynamic-pload-40ms` | `qs-ish-pload-400ms` |
| /PLOAD | 0→65000 Pa in 0.04 s | 0→65000 Pa in 0.4 s |
| μ₁ / ρ / H0 | locked | **same lock** (not retuned) |
| /ADYREL | yes | yes |
| first λ≥2 p | 35769 Pa | **27625 Pa** |
| first λ≥2 λ_max | 2.1404 | **2.327** |
| first λ≥2 V | 901.8 mL | **752.6 mL** |

Do not mix families in one Themis table. web-mbd `compare:inflate` stays the dynamic gate. This golden is for `compare:inflate:qs` after Daedalus accepts the load-family tag (today the toy lock is `qs-ish-dead-pressure` with pMax=54100, tRamp=0 — ingest notes in `WEBMBD-INGEST.md`).

## ABC ~54 kPa blocker (load schedule, not μ)

Slowing `/PLOAD` 10× moved first λ≥2 **from 35769 Pa down to 27625 Pa** (rel vs ABC 54100 Pa = **48.9%**). That is the QS direction (stretch tracks p) and it goes **away** from 54 kPa. A dead p=54100 Pa fork (`forks/dead-pressure`) CFL-explodes (λ 1→5.21 in 2 ms). `/AMS` not used (not a CFL-before-λ≥2 case; AMS ruptured this film on A-finest). **Do not retune μ.** This tape is the honest Radioss QS-ish golden, not a 54 kPa neighborhood claim.

## Correctness tape

λ from CST membrane principals on ANIM/VTK (rest = frame 0). Ψ = Σ ½ μ (I1−3) H0 A0, λ3=1/(λ1 λ2).

| frame | t [s] | p [Pa] | λ_max | V [mL] | Ψ [J] |
|------:|------:|-------:|------:|-------:|------:|
| 0 | 0 | 0 | 1.0000 | 354 | 0 |
| 1 | 0.0050177 | 815 | 1.2921 | 420.4 | 0.2096 |
| 2 | 0.010001 | 1625 | 1.3346 | 419.7 | 0.233 |
| 3 | 0.015006 | 2438 | 1.3303 | 428 | 0.2414 |
| 4 | 0.02 | 3250 | 1.3459 | 436.7 | 0.2726 |
| 5 | 0.025022 | 4066 | 1.3526 | 446.5 | 0.3014 |
| 6 | 0.030002 | 4875 | 1.3567 | 458.7 | 0.3353 |
| 7 | 0.035007 | 5689 | 1.3617 | 472.7 | 0.3739 |
| 8 | 0.040014 | 6502 | 1.3752 | 487.6 | 0.4172 |
| 9 | 0.045022 | 7316 | 1.3888 | 500.9 | 0.4653 |
| 10 | 0.050009 | 8126 | 1.4014 | 508.9 | 0.5216 |
| 11 | 0.055018 | 8940 | 1.4135 | 509.2 | 0.5871 |
| 12 | 0.060005 | 9751 | 1.4263 | 497.8 | 0.6559 |
| 13 | 0.065015 | 10565 | 1.4386 | 472.3 | 0.7403 |
| 14 | 0.070023 | 11379 | 1.4516 | 437.3 | 0.8354 |
| 15 | 0.075008 | 12189 | 1.4629 | 400.1 | 0.94 |
| 16 | 0.080018 | 13003 | 1.4740 | 373.7 | 1.058 |
| 17 | 0.085007 | 13814 | 1.4851 | 366.7 | 1.189 |
| 18 | 0.09002 | 14628 | 1.4957 | 381 | 1.327 |
| 19 | 0.095011 | 15439 | 1.5081 | 413.8 | 1.467 |
| 20 | 0.1 | 16250 | 1.5158 | 459 | 1.626 |
| 21 | 0.10502 | 17066 | 1.5260 | 502.8 | 1.786 |
| 22 | 0.11002 | 17877 | 1.5402 | 528.8 | 1.964 |
| 23 | 0.11501 | 18689 | 1.5514 | 529.4 | 2.171 |
| 24 | 0.12001 | 19501 | 1.5630 | 502 | 2.38 |
| 25 | 0.12501 | 20314 | 1.5738 | 456.6 | 2.587 |
| 26 | 0.13001 | 21126 | 1.5854 | 410.8 | 2.819 |
| 27 | 0.13501 | 21939 | 1.5961 | 383.2 | 3.062 |
| 28 | 0.14001 | 22752 | 1.6179 | 382.9 | 3.332 |
| 29 | 0.14502 | 23565 | 1.6726 | 409 | 3.627 |
| 30 | 0.15002 | 24378 | 1.8648 | 448.9 | 4.022 |
| 31 | 0.15501 | 25189 | 1.7536 | 497.1 | 4.154 |
| 32 | 0.16 | 26001 | 1.8241 | 598 | 5.263 |
| 33 | 0.165 | 26813 | 1.9957 | 683.5 | 6.985 |
| 34 | 0.17 | 27625 | 2.3271 | 752.6 | 8.043 |
| 35 | 0.175 | 28438 | 2.8746 | 632.4 | 10.74 |
| 36 | 0.18 | 29250 | 3.3980 | 584 | 13.74 |
| 37 | 0.185 | 30063 | 3.4216 | 336.8 | 15.95 |
| 38 | 0.19 | 30875 | 4.0912 | 297.5 | 19.04 |
| 39 | 0.195 | 31688 | 4.7126 | 302.6 | 23.46 |
| 40 | 0.2 | 32500 | 4.6396 | 507.1 | 24.69 |
| 41 | 0.205 | 33313 | 4.5770 | 360.4 | 28.93 |
| 42 | 0.21 | 34125 | 7.7277 | 244 | 35.67 |
| 43 | 0.215 | 34938 | 5.9518 | 368.1 | 48.77 |
| 44 | 0.22 | 35750 | 6.9686 | 844.4 | 64.73 |
| 45 | 0.22356 | 36329 | 21.6295 | 1.766e+04 | 515.1 |

Ψ(t) ≥ 0: **yes**  (min 0 J)
Enclosed V(t) ** > 0 every frame** (no global inside-out)
Contact: `/INTER/TYPE19` Gapmin = **0.762 mm** (= CONTACT_KISS). A plane-distance heuristic is too noisy for a min-gap column.

## Blockers (CFL / AMS)

- engine NORMAL TERMINATION (see /DT/NODA/STOP if cycles << T_END)
- CFL: /DT/NODA/STOP fired (nodal dt ≤ 1e-6). ANIM through last written frame kept. No /AMS.
- dtmin armed: MINIMUM TIME STEP . . . . . . . . . . . .  1.0000000000000E-06
- Belytschko N=1, 1554 quads. `/DT/NODA/STOP 0.9 1e-6` hang guard (not NODA/CST). No /AMS on this tape.
- Working PROP: Belytschko Ishell=1, Ismstr=10, N=1. μ and ρ unchanged.
- Tape is **QS-ish** `qs-ish-pload-400ms`: slower `/PLOAD` 0→65000 Pa in 0.4 s + `/ADYREL`. Distinct from `dynamic-pload-40ms` (first λ≥2 ≈ 36 kPa). Not a true implicit static solve. Do not retune μ.
- At first λ≥2: p=27625 Pa vs ABC QS ~54100 Pa (rel 48.9%) and vs dynamic 35769 Pa.

## Artifacts

- `artifacts/A-inflate.gif` / `A-inflate.mp4` — rest → past first λ≥2 (warn frame labeled)
- `artifacts/warn-lambda2.png` (or `last-frame.png` if λ<2)
- `artifacts/metrics.csv` / `metrics.json` / `warn.json`
- `artifacts/inflate-a-radioss-qs-golden.json` — freeze-frame golden for web-mbd `compare:inflate:qs`
- `law-card.txt`
