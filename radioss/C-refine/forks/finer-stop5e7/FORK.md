# C-refine finer — STOP Tmin=5e-7

Vanilla `/DT/NODA/STOP 0.9 1e-6` on the **outward-oriented** tape died at **t≈2.07 ms** (A002 only), before λ≥2 / before 32.5 kPa. Mesh CFL spike, not a 1e-15 hang.

This fork keeps **STOP** (not CST) at Tmin=**5e-7**, same μ/ρ/Ishell=1/`/PLOAD`/`/ADYREL`. No `/AMS` (A-finest AMS ruptured this LAW42 film).

**Result:** NORMAL TERMINATION via STOP at t≈21.8 ms (A012). Engine ELAPSED **109.72 s**, 9765 cycles, OMP 4. Grade frame A011 (32.5 kPa) is valid. A012 is a CFL blow-up (λ_max≈127, V≈37 L) — same as ship/fine on the outward tape.
