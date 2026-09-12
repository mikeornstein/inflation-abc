# C-refine — mesh convergence (Chiron/Themis lock)

Quad-only `/SHELL` + free-free `/ADYREL` OpenRadioss C inflate. **Not** the old tri/`SH3N` + 3-2-1 `/BCS` deck. μ and ρ are locked; load law is **fixed** across the ladder. This deck is the **Quality PASS desk** (p@λ≥2 still **dynamic** — NOT-YET apples vs ABC/Chiron QS).

## Locked law (never retuned)

- μ₁ = `(800 * 6894.757) / 1.75` = 3151888.9 Pa · α₁=2
- ρ = **1130 kg/m³** (Desmopan 85085A ISO 1183-1)
- H0 = 0.015×0.0254 m · Gapmin = CONTACT_KISS = 2·H0
- `/PROP` Ishell=**1** (Belytschko) N=1 Ismstr=10 · no `/SH3N` · no `/BCS`
- `/PLOAD` 0→65 kPa in 0.04 s (same ramp on every density unless a labeled fork)
- Hang guard is **`/DT/NODA/STOP`** (not CST). If CFL dies before λ≥2, `/AMS` once; if AMS ruptures the film, drop AMS and lower STOP Tmin only enough to run.

## Metrics lock (2026-09-11 / same-load 2026-09-12)

Treat as `briefs/2026-09-11-openradioss-mesh-convergence-metrics.md`.

At **first λ_max ≥ 2** on each mesh N (historical crossing, not the grade):

- Report **p, λ_max, V, Ψ**
- Mike (2026-09-12): **grade at the same load**, not first λ≥2. Same p → same strain/deformation. Peak stretch at the hole/creases is the climbing quantity.
- Same-load stations: **~32.5 kPa** (t≈20 ms) and **~35.8 kPa** (t≈22 ms). If ANIM frames differ, pick the frames whose **p** matches those loads.
- Successive nested N: **ΔV ≤ 5%**, **Δλ_max ≤ 2%**, **Δλ_aw ≤ 2%**
- λ_max stays in **[2.0, 2.35]** at that frame
- Ψ ≥ 0 required; contact viol / gap is **report-only**
- If CFL dies before λ≥2: **/AMS or slower PLOAD** fork (Kareem) — not NODA/CST; Ishell=1; no μ/ρ retune
- Peak λ_max climbing at holes/creases is a **sharp-hole singularity** in the geometry input (real creases have a small radius). Do **not** chase λ_max with more global refine. Volume / λ_aw settling is the useful signal. Do not declare mesh-failed just because λ_max climbs.
- **Converged dynamic ≠ ABC apples claim** vs Chiron QS (~54 kPa)

## Ladder

| density | N | /SHELL | plan |
|---------|--:|-------:|------|
| ship | 988 | 986 | ship meshes/C.json — paired orphans; even-patch ate 4 leftover tris (+0 cap Steiners; boundary fan, no Steiner) |
| fine | 3946 | 3944 | linear 1-to-4 of closed all-quad ship shell (nested 2× h; N×4 on a surface) |
| finer | 15778 | 15776 | linear 1-to-4 of closed all-quad fine shell (nested 2× h of fine; N=4×fine) |

## Wall-clock (OpenRadioss ELAPSED TIME — not Python post)

Solve time is starter + engine from `Ainflate_0001.out`. Contact-gap / GIF post is **not** in this column. OMP threads = 4 unless noted.

| density | N | engine ELAPSED | starter | cycles | threads | timed |
|---------|--:|---------------:|--------:|-------:|--------:|-------|
| ship | 988 | 1.39 s | 0.35 s | 1473 | 4 | this session |
| fine | 3946 | 7.99 s | 0.35 s | 2649 | 4 | this session |
| finer | 15778 | 52.56 s | 0.55 s | 7079 | 4 | this session |

## Same load (the grade) — nested family only

Mike: same p → same strain/deformation. Stations are PLOAD **32.5 kPa** (t≈20 ms) and **35.8 kPa** (t≈22 ms); if ANIM frames differ, the table uses the closest **p**. Coarse Gmsh remesh is excluded. Peak λ_max at holes/creases is a sharp-hole singularity — volume / λ_aw is the signal.

### 32.5 kPa (t≈20 ms)

| N | density | t [ms] | p [Pa] | λ_max | λ_aw | V [mL] | Ψ [J] |
|--:|---------|-------:|-------:|------:|-----:|-------:|------:|
| 988 | ship | 20 | 32537 | 1.9072 | 1.2706 | 1806 | 7.652 |
| 3946 | fine | 20 | 32504 | 1.7446 | 1.2202 | 1425 | 6.054 |
| 15778 | finer | 20 | 32506 | 1.8414 | 1.2117 | 1413 | 5.861 |

| pair | N_c → N_f | ΔV | Δλ_max | Δλ_aw | pass |
|------|-----------|---:|-------:|------:|:----:|
| ship→fine | 988 → 3946 | 21.10% | 8.52% | 3.96% | **FAIL** |
| fine→finer | 3946 → 15778 | 0.86% | 5.55% | 0.70% | **FAIL** |

### 35.8 kPa (t≈22 ms)

| N | density | t [ms] | p [Pa] | λ_max | λ_aw | V [mL] | Ψ [J] |
|--:|---------|-------:|-------:|------:|-----:|-------:|------:|
| 988 | ship | 22 | 35763 | 2.0436 | 1.3060 | 2221 | 10.29 |
| 3946 | fine | 22 | 35761 | 1.8709 | 1.2595 | 1863 | 8.6 |
| 15778 | finer | 22 | 35752 | 1.9853 | 1.2504 | 1845 | 8.359 |

| pair | N_c → N_f | ΔV | Δλ_max | Δλ_aw | pass |
|------|-----------|---:|-------:|------:|:----:|
| ship→fine | 988 → 3946 | 16.13% | 8.45% | 3.56% | **FAIL** |
| fine→finer | 3946 → 15778 | 0.99% | 6.11% | 0.72% | **FAIL** |


## First λ_max ≥ 2 (historical crossing — not the grade)

| N | density | t [ms] | p [Pa] | λ_max | V [mL] | Ψ [J] | λ∈[2.0,2.35] | Ψ≥0 | contact |
|--:|---------|-------:|-------:|------:|-------:|------:|:------------:|:---:|---------|
| 988 | ship | 22 | 35763 | 2.0436 | 2221 | 10.29 | yes | yes | gap=0.000184 mm; punch=False (report-only) |
| 3946 | fine | 4.01 | 6519 | 2.2353 | 471.4 | 0.3928 | yes | yes | gap=1.14e-06 mm; punch=False (report-only) |
| 15778 | finer | 24 | 39005 | 2.1653 | 2492 | 12.64 | yes | yes | metrics-only (gap skipped; report-only) |

All values are **dynamic** (explicit `/PLOAD` + `/ADYREL`), not Chiron QS.

λ field at that frame (area-weighted; report-only, not a gate):

| N | density | λ_aw_mean | λ_p90 |
|--:|---------|----------:|------:|
| 988 | ship | 1.3060 | 1.4525 |
| 3946 | fine | 1.0685 | 1.1125 |
| 15778 | finer | 1.3043 | 1.4587 |

## Successive pairs (relative change vs coarser N)

| pair | N_c → N_f | Δp | ΔV | Δλ_max | λ band | Ψ≥0 | pass |
|------|-----------|---:|---:|-------:|:------:|:---:|:----:|
| ship→fine | 988 → 3946 | 81.77% | 78.78% | 9.38% | yes | yes | **FAIL** |
| fine→finer | 3946 → 15778 | 498.36% | 428.70% | 3.13% | yes | yes | **FAIL** |

## Verdict

**letter C: volume / λ_aw settled on last nested pair; λ_max climbing at holes/creases is a sharp-hole singularity (Mike 2026-09-12 — perfectly sharp hole in the geometry input; real creases have a small radius). Do not chase λ_max with more global refine. Not mesh-failed. p325 fine→finer ΔV=0.86% Δλ_max=5.55% Δλ_aw=0.70%; p358 fine→finer ΔV=0.99% Δλ_max=6.11% Δλ_aw=0.72%**

Converged dynamic on this explicit tape is **not** an ABC apples-to-apples claim against the JS Chiron QS warn (~54 kPa).

## Forks

CFL `/DT/NODA/STOP` **after** first λ≥2 on: **ship, fine, finer** (metric frame is valid; no Kareem fork — lock only forks if CFL dies before λ≥2). Hang guard remains STOP (not NODA/CST). Ishell=1; μ/ρ locked.

B/C ladder is ship / fine / finer only (no coarse Gmsh row, no finest / N≈99k). Hang guard remains STOP. `/AMS` only if CFL dies before λ≥2; drop AMS if it ruptures.

## Reproduce

```bash
bash radioss/install_openradioss.sh
python3 tools/refine_letter_a.py --letter C
bash radioss/C-refine/run.sh
python3 tools/refine_same_load.py --root radioss/C-refine --session-rerun ship --session-rerun fine --session-rerun finer
python3 tools/refine_report.py --root radioss/C-refine
```

