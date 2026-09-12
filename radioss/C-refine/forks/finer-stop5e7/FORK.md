# C-refine finer — STOP Tmin=5e-7

Vanilla `/DT/NODA/STOP 0.9 1e-6` on the **outward-oriented** tape died at **t≈2.07 ms** (A002 only), before λ≥2 / before 32.5 kPa. Mesh CFL spike, not a 1e-15 hang.

Hang guard stays **STOP** (not CST). Same μ/ρ/Ishell=1/`/PLOAD`/`/ADYREL`. No `/AMS` on this fork (A-finest AMS ruptured this LAW42 film; B working nested tapes are STOP Tmin).

If 5e-7 is still not enough to reach A011/A012, lower once more to 1e-7 (`finer-stop1e7`).
