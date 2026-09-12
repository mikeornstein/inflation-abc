# B-refine finer — STOP Tmin=5e-7 (not enough)

Vanilla 1e-6 and this 5e-7 tape both died at **t≈1.1 ms** (nodal dt dropped through 5e-7 before λ≥2). Same μ/ρ. Working tape is the `/AMS` fork if it reaches the grade; otherwise lower STOP further.
