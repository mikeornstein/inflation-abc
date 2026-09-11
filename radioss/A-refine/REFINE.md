# A-refine — mesh convergence (Chiron/Themis lock)

Quad-only `/SHELL` + free-free `/ADYREL` OpenRadioss A inflate. **Not** the old tri/`SH3N` + 3-2-1 `/BCS` deck. μ and ρ are locked; load law is **fixed** across the ladder. This deck is the **Quality PASS desk** (p@λ≥2 still **dynamic** — NOT-YET apples vs ABC/Chiron QS).

## Locked law (never retuned)

- μ₁ = `(800 * 6894.757) / 1.75` = 3151888.9 Pa · α₁=2
- ρ = **1130 kg/m³** (Desmopan 85085A ISO 1183-1)
- H0 = 0.015×0.0254 m · Gapmin = CONTACT_KISS = 2·H0
- `/PROP` Ishell=**1** (Belytschko) N=1 Ismstr=10 · no `/SH3N` · no `/BCS`
- `/PLOAD` 0→65 kPa in 0.04 s (same ramp on every density unless a labeled fork)

## Metrics lock (2026-09-11)

Treat as `briefs/2026-09-11-openradioss-mesh-convergence-metrics.md`.

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
| coarse | 936 | 936 | Gmsh DelQuad remesh of ship A outline + prism walls |
| ship | 1554 | 1554 | ship meshes/A.json (quadify orphan caps; midplane not remeshed) |
| fine | 6216 | 6216 | linear 1-to-4 of closed all-quad ship shell (nested 2× h; N×4 on a surface) |
| finer | 24864 | 24864 | linear 1-to-4 of closed all-quad fine shell (nested 2× h of fine; N=4×fine) |

## First λ_max ≥ 2 (dynamic)

| N | density | t [ms] | p [Pa] | λ_max | V [mL] | Ψ [J] | λ∈[2.0,2.35] | Ψ≥0 | contact |
|--:|---------|-------:|-------:|------:|-------:|------:|:------------:|:---:|---------|
| 936 | coarse | 16 | 26006 | 2.2597 | 888.4 | 7.617 | yes | yes | gap=0.000101 mm; punch=False (report-only) |
| 1554 | ship | 22 | 35769 | 2.1404 | 901.8 | 9.502 | yes | yes | gap=2.27e-06 mm; punch=False (report-only) |
| 6216 | fine | 22 | 35762 | 2.2302 | 901.5 | 8.776 | yes | yes | gap=1.81e-06 mm; punch=False (report-only) |
| 24864 | finer | 20 | 32505 | 2.1479 | 778.3 | 5.731 | yes | yes | metrics-only (gap skipped; report-only) |

All values are **dynamic** (explicit `/PLOAD` + `/ADYREL`), not Chiron QS.

λ field at that frame (area-weighted; report-only, not a gate):

| N | density | λ_aw_mean | λ_p90 |
|--:|---------|----------:|------:|
| 936 | coarse | 1.2897 | 1.4534 |
| 1554 | ship | 1.3013 | 1.4460 |
| 6216 | fine | 1.2735 | 1.4102 |
| 24864 | finer | 1.2162 | 1.3121 |

## Successive pairs (relative change vs coarser N)

| pair | N_c → N_f | Δp | ΔV | Δλ_max | λ band | Ψ≥0 | pass |
|------|-----------|---:|---:|-------:|:------:|:---:|:----:|
| coarse→ship | 936 → 1554 | 37.54% | 1.51% | 5.28% | yes | yes | **FAIL** |
| ship→fine | 1554 → 6216 | 0.02% | 0.03% | 4.20% | yes | yes | **FAIL** |
| fine→finer | 6216 → 24864 | 9.11% | 13.67% | 3.69% | yes | yes | **FAIL** |

## Verdict

**not-yet — successive ~2× N did not meet Δp≤5%, ΔV≤5%, Δλ_max≤2% with λ_max in [2.0, 2.35] and Ψ≥0. fine→finer Δp=9.11%, ΔV=13.67%, Δλ_max=3.69% (locks 5%/5%/2%).**

Converged dynamic on this explicit tape is **not** an ABC apples-to-apples claim against the JS Chiron QS warn (~54 kPa).

## Forks

CFL `/DT/NODA/STOP` **after** first λ≥2 on: **finer** (metric frame is valid; no Kareem fork — lock only forks if CFL dies before λ≥2). Hang guard remains STOP (not NODA/CST). Ishell=1; μ/ρ locked.

## Reproduce

```bash
bash radioss/install_openradioss.sh
python3 tools/refine_letter_a.py
bash radioss/A-refine/run.sh
python3 tools/refine_letter_a.py --finer-only
bash radioss/A-refine/run.sh --finer-only
python3 tools/refine_report.py
```

