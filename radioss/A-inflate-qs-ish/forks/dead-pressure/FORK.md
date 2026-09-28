# Fork — dead p = 54100 Pa (`qs-ish-dead-pressure`)

Not the vend golden. Evidence that matching the web-mbd toy step load on this
LAW42 film is not a usable first-λ≥2 freeze.

- Same μ₁ / ρ / H0 / Gapmin / mesh `d9c56487` / `/ADYREL` / no `/AMS`
- `/PLOAD` Fscale = **54100 Pa**, ramp **1 ms**, hold to 80 ms (`T_RAMP_QS_ISH=0` analogue)
- Hang guard `/DT/NODA/STOP 0.9 1e-6`

## Result

Engine **NORMAL TERMINATION** via NODA/STOP at **t = 2.45 ms** (1089 cycles).

| frame | t [s] | p [Pa] | λ_max | V [mL] | Ψ [J] |
|------:|------:|-------:|------:|-------:|------:|
| 0 | 0 | 0 | 1.000 | 354 | 0 |
| 1 | 0.00200 | 54100 | **5.213** | 3827 | 126.5 |
| 2 | 0.00248 | 54100 | **15.02** | 2.95e4 | 740 |

First ANIM after rest already has λ_max = 5.21 — the λ=2 crossing is **between frames**
on a CFL blow-up, not a QS warn freeze. `punch` flag is false (V>0) but the glyph
is exploded. **Do not vendor this as the QS golden. Do not retune μ.**

Working tape: `../../` (`qs-ish-pload-400ms`).
