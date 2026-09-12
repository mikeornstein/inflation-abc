# B-refine fine — STOP Tmin=5e-7

Vanilla `/DT/NODA/STOP 0.9 1e-6` died at **t≈1.3 ms** (before λ≥2 / before 32.5 kPa). Mesh CFL spike, not a 1e-15 hang.

- Tried `/AMS` Tmin=5e-6 once (Kareem): reached the 20/22 ms grade, then dt collapsed toward hang at t≈27 ms (timeout). Did **not** rupture the film the way A-finest AMS did.
- Working nested-grade tape: this fork keeps **STOP** (not CST) at Tmin=**5e-7**, same μ/ρ/Ishell=1/`/PLOAD`/`/ADYREL`.
