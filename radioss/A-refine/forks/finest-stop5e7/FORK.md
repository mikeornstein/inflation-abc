# Finest N=99456 — hang-guard floor (still `/DT/NODA/STOP`, not CST)

Vanilla STOP Tmin=**1e-6** died at t=0: natural nodal dt = **9.74e-7** (node 99081). That is mesh CFL, not a 1e-15 hang.

Kareem `/AMS` was tried first (as specified), same μ/ρ/Ishell=1/`/PLOAD`:

- Tmin=1e-4: shells **ruptured** at ~0.3 ms
- Tmin=5e-6: shells **ruptured** at t=0 (ERROR TERMINATION; no standard ELAPSED footer)

AMS mass scaling is incompatible with this LAW42 + Belytschko film. Slower PLOAD cannot help **rest** CFL.

This fork keeps **`/DT/NODA/STOP`** (not CST), same μ/ρ/Ishell=1/`/PLOAD`/`/ADYREL`, and lowers the STOP floor to **5e-7** so the legitimate CFL can run. Still kills a true 1e-15 hang.

## This-session wall-clock (OpenRadioss, not Python post)

| | |
|--|--|
| starter | **4.24 s** |
| engine ELAPSED TIME | **1290.11 s** (00:21:30) |
| starter+engine | 1294.35 s |
| cycles | **27058** |
| OMP threads | **4** |
| termination | NORMAL at t≈27.35 ms (dt collapsing in contact; past both grade stations) |

Grade frames 10 (32.5 kPa) and 11 (35.8 kPa) are on disk. Engine did **not** reach T_END=0.05 s. Metric frames are valid.
