# A-refine — mesh convergence (Chiron/Themis lock)

Quad-only `/SHELL` + free-free `/ADYREL` OpenRadioss A inflate. **Not** the old tri/`SH3N` + 3-2-1 `/BCS` deck. μ and ρ are locked; load law is **fixed** across the ladder. This deck is the **Quality PASS desk** (p@λ≥2 still **dynamic** — NOT-YET apples vs ABC/Chiron QS).

## Locked law (never retuned)

- μ₁ = `(800 * 6894.757) / 1.75` = 3151888.9 Pa · α₁=2
- ρ = **1130 kg/m³** (Desmopan 85085A ISO 1183-1)
- H0 = 0.015×0.0254 m · Gapmin = CONTACT_KISS = 2·H0
- `/PROP` Ishell=**1** (Belytschko) N=1 Ismstr=10 · no `/SH3N` · no `/BCS`
- `/PLOAD` 0→65 kPa in 0.04 s (same ramp on every density unless a labeled fork)
- Hang guard is **`/DT/NODA/STOP`** (not CST). Finest nested CFL sits at ~9.7e-7; working tape uses STOP Tmin=**5e-7**.

## Metrics lock (2026-09-11)

Treat as `briefs/2026-09-11-openradioss-mesh-convergence-metrics.md`.

At **first λ_max ≥ 2** on each mesh N:

- Report **p, λ_max, V, Ψ**
- Mike (2026-09-12): **grade at the same load**, not first λ≥2. Same p → same strain/deformation. Peak stretch at the hole/creases is the climbing quantity.
- Same-load stations: **~32.5 kPa** (t≈20 ms) and **~35.8 kPa** (t≈22 ms).
- Successive nested N (ship/fine/finer/finest): **ΔV ≤ 5%**, **Δλ_max ≤ 2%**, **Δλ_aw ≤ 2%**
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
| finest | 99456 | 99456 | linear 1-to-4 of closed all-quad finer shell (nested 2× h of finer; N=4×finer) |

## Wall-clock (OpenRadioss ELAPSED TIME — not Python post)

Solve time is starter + engine from `Ainflate_0001.out`. Contact-gap / GIF post is **not** in this column. OMP threads = 4 unless noted.

| density | N | engine ELAPSED | starter | cycles | threads | timed |
|---------|--:|---------------:|--------:|-------:|--------:|-------|
| ship | 1554 | 4.44 s | 0.32 s | 3361 | 4 | from existing .out |
| fine | 6216 | 19.44 s | 0.37 s | 3837 | 4 | from existing .out |
| finer | 24864 | 148.18 s | 0.80 s | 9085 | 4 | from existing .out |
| finest | 99456 | 1290.11 s | 4.24 s | 27058 | 4 | this session |

Session forks (same μ/ρ; not nested-grade rows):

| fork | engine ELAPSED | starter | cycles | threads | note |
|------|---------------:|--------:|-------:|--------:|------|
| finest-vanilla | 0.73 s | 4.32 s | 1 | 4 | STOP Tmin=1e-6 died at t=0 (nodal dt 9.74e-7). Mesh CFL, not a hang. |
| finest-ams | — | 4.41 s | 0 | 4 | Kareem /AMS Tmin=5e-6: ERROR TERMINATION, shells ruptured. Same μ/ρ. Hang guard still STOP. |

## Same load (the grade) — nested family only

Mike: same p → same strain/deformation. Stations are PLOAD **32.5 kPa** (t≈20 ms, frame 10) and **35.8 kPa** (t≈22 ms, frame 11). Coarse Gmsh remesh is excluded.

### 32.5 kPa (t≈20 ms)

| N | density | t [ms] | p [Pa] | λ_max | λ_aw | V [mL] | Ψ [J] |
|--:|---------|-------:|-------:|------:|-----:|-------:|------:|
| 1554 | ship | 20 | 32506 | 1.9158 | 1.2522 | 780.9 | 6.493 |
| 6216 | fine | 20 | 32511 | 1.9920 | 1.2264 | 780.2 | 5.876 |
| 24864 | finer | 20 | 32505 | 2.1479 | 1.2162 | 778.3 | 5.731 |
| 99456 | finest | 20 | 32501 | 2.3513 | 1.2116 | 776.2 | 5.651 |

| pair | N_c → N_f | ΔV | Δλ_max | Δλ_aw | pass |
|------|-----------|---:|-------:|------:|:----:|
| ship→fine | 1554 → 6216 | 0.09% | 3.98% | 2.06% | **FAIL** |
| fine→finer | 6216 → 24864 | 0.24% | 7.83% | 0.84% | **FAIL** |
| finer→finest | 24864 → 99456 | 0.27% | 9.47% | 0.38% | **FAIL** |

### 35.8 kPa (t≈22 ms)

| N | density | t [ms] | p [Pa] | λ_max | λ_aw | V [mL] | Ψ [J] |
|--:|---------|-------:|-------:|------:|-----:|-------:|------:|
| 1554 | ship | 22 | 35769 | 2.1404 | 1.3013 | 901.8 | 9.502 |
| 6216 | fine | 22 | 35762 | 2.2302 | 1.2735 | 901.5 | 8.776 |
| 24864 | finer | 22 | 35752 | 2.4181 | 1.2629 | 899.6 | 8.609 |
| 99456 | finest | 22 | 35751 | 2.6529 | 1.2579 | 897.2 | 8.511 |

| pair | N_c → N_f | ΔV | Δλ_max | Δλ_aw | pass |
|------|-----------|---:|-------:|------:|:----:|
| ship→fine | 1554 → 6216 | 0.03% | 4.20% | 2.14% | **FAIL** |
| fine→finer | 6216 → 24864 | 0.22% | 8.42% | 0.83% | **FAIL** |
| finer→finest | 24864 → 99456 | 0.27% | 9.71% | 0.40% | **FAIL** |


## First λ_max ≥ 2 (historical crossing — not the grade)

| N | density | t [ms] | p [Pa] | λ_max | V [mL] | Ψ [J] | λ∈[2.0,2.35] | Ψ≥0 | contact |
|--:|---------|-------:|-------:|------:|-------:|------:|:------------:|:---:|---------|
| 936 | coarse | 16 | 26006 | 2.2597 | 888.4 | 7.617 | yes | yes | gap=0.000101 mm; punch=False (report-only) |
| 1554 | ship | 22 | 35769 | 2.1404 | 901.8 | 9.502 | yes | yes | gap=2.27e-06 mm; punch=False (report-only) |
| 6216 | fine | 22 | 35762 | 2.2302 | 901.5 | 8.776 | yes | yes | gap=1.81e-06 mm; punch=False (report-only) |
| 24864 | finer | 20 | 32505 | 2.1479 | 778.3 | 5.731 | yes | yes | metrics-only (gap skipped; report-only) |
| 99456 | finest | 18 | 29250 | 2.1370 | 693.4 | 3.927 | yes | yes | metrics-only (gap skipped; report-only) |

All values are **dynamic** (explicit `/PLOAD` + `/ADYREL`), not Chiron QS.

λ field at that frame (area-weighted; report-only, not a gate):

| N | density | λ_aw_mean | λ_p90 |
|--:|---------|----------:|------:|
| 936 | coarse | 1.2897 | 1.4534 |
| 1554 | ship | 1.3013 | 1.4460 |
| 6216 | fine | 1.2735 | 1.4102 |
| 24864 | finer | 1.2162 | 1.3121 |
| 99456 | finest | 1.1776 | 1.2544 |

## Successive pairs (relative change vs coarser N)

| pair | N_c → N_f | Δp | ΔV | Δλ_max | λ band | Ψ≥0 | pass |
|------|-----------|---:|---:|-------:|:------:|:---:|:----:|
| coarse→ship | 936 → 1554 | 37.54% | 1.51% | 5.28% | yes | yes | **FAIL** |
| ship→fine | 1554 → 6216 | 0.02% | 0.03% | 4.20% | yes | yes | **FAIL** |
| fine→finer | 6216 → 24864 | 9.11% | 13.67% | 3.69% | yes | yes | **FAIL** |
| finer→finest | 24864 → 99456 | 10.01% | 10.91% | 0.51% | yes | yes | **FAIL** |

## Verdict

**not-yet — same load, peak stretch at hole/creases still moving. p325 finer→finest ΔV=0.27% Δλ_max=9.47% Δλ_aw=0.38%; p358 finer→finest ΔV=0.27% Δλ_max=9.71% Δλ_aw=0.40%**

Converged dynamic on this explicit tape is **not** an ABC apples-to-apples claim against the JS Chiron QS warn (~54 kPa).

## Forks

CFL `/DT/NODA/STOP` **after** first λ≥2 on: **finer** (metric frame is valid; no Kareem fork — lock only forks if CFL dies before λ≥2). Hang guard remains STOP (not NODA/CST). Ishell=1; μ/ρ locked.

Vanilla finest `/DT/NODA/STOP 0.9 1e-6` died at **t=0** (nodal dt = 9.74e-7). That is mesh CFL, not a 1e-15 hang. Kareem `/AMS` (Tmin 1e-4 and 5e-6) **ruptured** the LAW42 + Belytschko film; slower PLOAD cannot fix rest CFL. Working tape: `forks/finest-stop5e7` keeps STOP (not CST) at Tmin=**5e-7**, same μ/ρ/Ishell=1/`/PLOAD`/`/ADYREL`.

## Reproduce

```bash
bash radioss/install_openradioss.sh
python3 tools/refine_letter_a.py
bash radioss/A-refine/run.sh
python3 tools/refine_letter_a.py --finest-only
python3 tools/mesh_to_radioss.py --allow-n --check \
  --mesh radioss/A-refine/meshes/A-finest.json \
  --out-dir radioss/A-refine/forks/finest-stop5e7 --noda-stop 5e-7
bash radioss/A-refine/run.sh --finest-only
python3 tools/refine_same_load.py --session-rerun finest
python3 tools/refine_report.py
```

