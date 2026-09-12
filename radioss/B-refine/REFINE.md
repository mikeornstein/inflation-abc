# B-refine — mesh convergence (Chiron/Themis lock)

Quad-only `/SHELL` + free-free `/ADYREL` OpenRadioss B inflate. **Not** the old tri/`SH3N` + 3-2-1 `/BCS` deck. μ and ρ are locked; load law is **fixed** across the ladder. This deck is the **Quality PASS desk** (p@λ≥2 still **dynamic** — NOT-YET apples vs ABC/Chiron QS).

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
| ship | 4450 | 4452 | ship meshes/B.json — paired orphans; even-patch skipped (would change euler -2→2 — through-holes stay open); mixed 1-to-4 of remaining 96 unpaired tris (no /SH3N) |
| fine | 17806 | 17808 | linear 1-to-4 of closed all-quad ship shell (nested 2× h; N×4 on a surface) |
| finer | 71230 | 71232 | linear 1-to-4 of closed all-quad fine shell (nested 2× h of fine; N=4×fine) |

## Wall-clock (OpenRadioss ELAPSED TIME — not Python post)

Solve time is starter + engine from `Ainflate_0001.out`. Contact-gap / GIF post is **not** in this column. OMP threads = 4 unless noted.

| density | N | engine ELAPSED | starter | cycles | threads | timed |
|---------|--:|---------------:|--------:|-------:|--------:|-------|
| ship | 4450 | 13.54 s | 0.37 s | 5799 | 4 | this session |
| fine | 17806 | 103.93 s | 0.61 s | 14623 | 4 | this session |
| finer | 71230 | 1068.66 s | 1.96 s | 44029 | 4 | this session |

Session forks (same μ/ρ; not nested-grade rows):

| fork | engine ELAPSED | starter | cycles | threads | note |
|------|---------------:|--------:|-------:|--------:|------|
| fine-ams | — | 0.56 s | 7400 | 4 | B-refine fine — Kareem /AMS (not the grade row) |
| fine-stop5e7 | 103.93 s | 0.61 s | 14623 | 4 | B-refine fine — STOP Tmin=5e-7 |
| finer-ams | — | 2.12 s | 3000 | 4 | B-refine finer — Kareem /AMS ruptured |
| finer-stop1e7 | 1068.66 s | 1.96 s | 44029 | 4 | B-refine finer — STOP Tmin=1e-7 |
| finer-stop5e7 | 19.41 s | 2.11 s | 739 | 4 | B-refine finer — STOP Tmin=5e-7 (not enough) |
| fine-vanilla | 2.94 s | 0.57 s | 455 | 4 | vanilla fine STOP 1e-6 (not the nested-grade row; see forks/) |
| finer-vanilla | 17.17 s | 2.10 s | 719 | 4 | vanilla finer STOP 1e-6 (not the nested-grade row; see forks/) |

## Same load (the grade) — nested family only

Mike: same p → same strain/deformation. Stations are PLOAD **32.5 kPa** (t≈20 ms) and **35.8 kPa** (t≈22 ms); if ANIM frames differ, the table uses the closest **p**. Coarse Gmsh remesh is excluded. Peak λ_max at holes/creases is a sharp-hole singularity — volume / λ_aw is the signal.

### 32.5 kPa (t≈20 ms)

| N | density | t [ms] | p [Pa] | λ_max | λ_aw | V [mL] | Ψ [J] |
|--:|---------|-------:|-------:|------:|-----:|-------:|------:|
| 4450 | ship | 20 | 32514 | 2.1466 | 1.2354 | 801.3 | 6.936 |
| 17806 | fine | 20 | 32503 | 2.4834 | 1.2259 | 802.4 | 6.801 |
| 71230 | finer | 20 | 32500 | 2.9054 | 1.2215 | 802.2 | 6.751 |

| pair | N_c → N_f | ΔV | Δλ_max | Δλ_aw | pass |
|------|-----------|---:|-------:|------:|:----:|
| ship→fine | 4450 → 17806 | 0.14% | 15.69% | 0.77% | **FAIL** |
| fine→finer | 17806 → 71230 | 0.03% | 16.99% | 0.36% | **FAIL** |

### 35.8 kPa (t≈22 ms)

| N | density | t [ms] | p [Pa] | λ_max | λ_aw | V [mL] | Ψ [J] |
|--:|---------|-------:|-------:|------:|-----:|-------:|------:|
| 4450 | ship | 22 | 35760 | 2.3923 | 1.2867 | 907 | 10.49 |
| 17806 | fine | 22 | 35753 | 2.7698 | 1.2770 | 908.3 | 10.34 |
| 71230 | finer | 22 | 35750 | 3.2470 | 1.2721 | 908.2 | 10.28 |

| pair | N_c → N_f | ΔV | Δλ_max | Δλ_aw | pass |
|------|-----------|---:|-------:|------:|:----:|
| ship→fine | 4450 → 17806 | 0.14% | 15.78% | 0.76% | **FAIL** |
| fine→finer | 17806 → 71230 | 0.01% | 17.23% | 0.38% | **FAIL** |


## First λ_max ≥ 2 (historical crossing — not the grade)

| N | density | t [ms] | p [Pa] | λ_max | V [mL] | Ψ [J] | λ∈[2.0,2.35] | Ψ≥0 | contact |
|--:|---------|-------:|-------:|------:|-------:|------:|:------------:|:---:|---------|
| 4450 | ship | 18 | 29257 | 2.0014 | 732.8 | 4.857 | yes | yes | gap=5.94e-06 mm; punch=False (report-only) |
| 17806 | fine | — | — | — | — | — | — | — | CFL before λ≥2 |
| 71230 | finer | — | — | — | — | — | — | — | CFL before λ≥2 |

All values are **dynamic** (explicit `/PLOAD` + `/ADYREL`), not Chiron QS.

λ field at that frame (area-weighted; report-only, not a gate):

| N | density | λ_aw_mean | λ_p90 |
|--:|---------|----------:|------:|
| 4450 | ship | 1.1995 | 1.3081 |
| 17806 | fine | — | — |
| 71230 | finer | — | — |

## Successive pairs (relative change vs coarser N)

| pair | N_c → N_f | Δp | ΔV | Δλ_max | λ band | Ψ≥0 | pass |
|------|-----------|---:|---:|-------:|:------:|:---:|:----:|
| ship→fine | 4450 → 17806 | — | — | — | — | — | skipped (fine CFL) |
| fine→finer | 17806 → 71230 | — | — | — | — | — | skipped (fine CFL, finer CFL) |

## Verdict

**letter B: volume / λ_aw settled on last nested pair; λ_max climbing at holes/creases is a sharp-hole singularity (Mike 2026-09-12 — perfectly sharp hole in the geometry input; real creases have a small radius). Do not chase λ_max with more global refine. Not mesh-failed. p325 fine→finer ΔV=0.03% Δλ_max=16.99% Δλ_aw=0.36%; p358 fine→finer ΔV=0.01% Δλ_max=17.23% Δλ_aw=0.38%**

Converged dynamic on this explicit tape is **not** an ABC apples-to-apples claim against the JS Chiron QS warn (~54 kPa).

## Forks

CFL `/DT/NODA/STOP` before λ≥2 on: **fine, finer**. Kareem fork: `/AMS` or slower PLOAD (not NODA/CST). Ishell=1; μ/ρ locked.

B/C ladder is ship / fine / finer only (no coarse Gmsh row, no finest / N≈99k). Hang guard remains STOP. `/AMS` only if CFL dies before λ≥2; drop AMS if it ruptures.

## Reproduce

```bash
bash radioss/install_openradioss.sh
python3 tools/refine_letter_a.py --letter B
bash radioss/B-refine/run.sh
python3 tools/refine_same_load.py --root radioss/B-refine --session-rerun ship --session-rerun fine --session-rerun finer
python3 tools/refine_report.py --root radioss/B-refine
```

