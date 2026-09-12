# Vanilla finest — CFL at rest

`/DT/NODA/STOP 0.9 1e-6` on nested N=99456.

- Engine ELAPSED TIME = **0.73 s**
- Starter = **4.32 s**
- Cycles = **1**
- Threads = **4**
- `ERROR : NODAL TIME STEP LESS OR EQUAL DTMIN N=99081` (dt = 9.74e-7)
- NORMAL TERMINATION (STOP guard fired)

Mesh CFL, not a hang. Hang guard stayed STOP (not CST). `/AMS` fork ruptured; working tape is `forks/finest-stop5e7` with STOP Tmin=5e-7.
