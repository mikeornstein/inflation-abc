# Kareem AMS fork — finest N=99456

Vanilla `/DT/NODA/STOP 0.9 1e-6` died at **t=0** (nodal dt = 9.74e-7 on node 99081). CFL before λ≥2.

- Same LAW42 μ₁, α₁=2, ρ=1130, H0, Gapmin, Ishell=1, `/ADYREL`, `/PLOAD` 0→65 kPa in 0.04 s
- No `/DT/NODA/CST`
- Hang guard **still** `/DT/NODA/STOP`
- `/AMS` + `/DT/AMS/0` Tmin=**5e-6** (1e-4 ruptured shells at 0.3 ms — too much mass scaling)

**Result:** ERROR TERMINATION — `-- RUPTURE OF SHELL ELEMENT` 99399 / 99375 at t=0. No standard `ELAPSED TIME     =` footer on the engine `.out`. Cycle table stops at cycle 0. Starter elapsed from `Ainflate_0000.out` = **4.41 s**. OMP threads = 4. Same μ/ρ.

AMS is incompatible with this film. Working tape is `../finest-stop5e7` (STOP Tmin=5e-7, not CST).
