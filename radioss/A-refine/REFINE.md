# A-refine — mesh convergence (Chiron/Themis lock)

Quad-only `/SHELL` + free-free `/ADYREL` OpenRadioss A inflate.
**Not** the old tri/`SH3N` + 3-2-1 `/BCS` deck.
μ and ρ are locked; load law is **fixed** across the ladder.

Engine tapes: **pending** (this file is the metrics lock + ladder; table fills after `run.sh`).

## Locked law (never retuned)

- μ₁ = `(800 * 6894.757) / 1.75` = 3.1518889e6 Pa · α₁=2
- ρ = **1130 kg/m³** (Desmopan 85085A ISO 1183-1)
- H0 = 0.015×0.0254 m · Gapmin = CONTACT_KISS = 2·H0
- `/PROP` Ishell=**1** (Belytschko) N=1 Ismstr=10 · no `/SH3N` · no `/BCS`
- `/PLOAD` 0→65 kPa in 0.04 s (same ramp on every density unless a labeled fork)

## Metrics lock (2026-09-11)

Treat as `/workspace/briefs/2026-09-11-openradioss-mesh-convergence-metrics.md`.

At **first λ_max ≥ 2** on each mesh N:

- Report **p, λ_max, V, Ψ**
- Label **dynamic** until a QS-ish tape exists
- Successive ~2× denser N: relative change **p ≤ 5%**, **V ≤ 5%**, **λ_max ≤ 2%**
- λ_max stays in **[2.0, 2.35]** at that frame
- Ψ ≥ 0 required; contact viol / gap is **report-only**
- If CFL dies before λ≥2: **/AMS or slower PLOAD** fork (Kareem) — not NODA/CST; Ishell=1; no μ/ρ retune
- **Converged dynamic ≠ ABC apples claim** vs Chiron QS (~54 kPa)

## Ladder

| density | N | /SHELL | plan |
|---------|--:|-------:|------|
| coarse | 936 | 936 | Gmsh DelQuad remesh of ship A outline + prism walls (lc=0.016, nz=6) |
| ship | 1554 | 1554 | locked `meshes/A.json` (orphan caps quadified; midplane not remeshed) |
| fine | 6216 | 6216 | linear 1-to-4 of closed all-quad ship shell (nested 2× h; N×4 on a surface) |

N ratios: ship/coarse ≈ 1.66; fine/ship = 4 (2× h on a surface). Same LAW42 / PLOAD / `/ADYREL` / Ishell=1.

## First λ_max ≥ 2 (dynamic)

| N | density | t [ms] | p [Pa] | λ_max | V [mL] | Ψ [J] | λ∈[2.0,2.35] | Ψ≥0 | contact |
|--:|---------|-------:|-------:|------:|-------:|------:|:------------:|:---:|---------|
| 936 | coarse | — | — | — | — | — | — | — | pending |
| 1554 | ship | — | — | — | — | — | — | — | pending |
| 6216 | fine | — | — | — | — | — | — | — | pending |

## Verdict

**not-yet** — engine tapes not yet on this revision.

Converged dynamic on this explicit tape is **not** an ABC apples-to-apples claim against the JS Chiron QS warn (~54 kPa).

## Reproduce

```bash
bash radioss/install_openradioss.sh
python3 tools/refine_letter_a.py
bash radioss/A-refine/run.sh
python3 tools/refine_report.py
```
