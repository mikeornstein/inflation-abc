# OpenRadioss — letter A inflate **QS-ish** golden

Labeled load family for web-mbd `compare:inflate:qs` (Chiron E.17).

**Not** `dynamic-pload-40ms`. **μ and ρ are not retuned.** OpenRadioss stays offline (AGPL).

## Freeze frame (this tape)

| qty | `qs-ish-pload-400ms` | `dynamic-pload-40ms` (PR #8) | ABC QS class |
| --- | ---: | ---: | ---: |
| loadFamily | `qs-ish-pload-400ms` | `dynamic-pload-40ms` | `qs-ish-dead-pressure` (toy) |
| `/PLOAD` | 0→65 kPa in **0.40 s** | 0→65 kPa in **0.04 s** | dead p = 54100 Pa |
| t at first λ≥2 | **0.170 s** (frame 34) | 0.0220 s (frame 11) | — |
| λ_max | **2.327** | 2.140 | 2 |
| p | **27625 Pa** | 35769 Pa | ~54100 Pa |
| V | **752.6 mL** | 901.8 mL | — |
| Ψ | **8.043 J** (≥0) | 9.502 J | — |
| punch at warn | false (V>0) | false | — |
| mesh fingerprint | `d9c56487` | `d9c56487` | `d9c56487` |
| μ₁ / ρ / H0 / Gapmin | locked | **same lock** | same lock |

Golden JSON: `inflate-a-radioss-qs-golden.json` (also `artifacts/inflate-a-radioss-qs-golden.json`).

## ABC ~54 kPa is **not** a load-schedule result

Slowing `/PLOAD` 10× (the requested QS-ish lever) moved first-λ≥2 **down** (36 kPa → **28 kPa**), farther from ABC ~54 kPa (rel **48.9%**). Stretch has more time to develop at each p, so λ_max hits 2 earlier on the ramp. Getting 54 kPa at first λ_max≥2 on this LAW42 film would mean **less** stretch at a given p — a μ or kinematics change, which is forbidden.

A matching-family dead-pressure fork (`forks/dead-pressure`, pMax=54100, 1 ms step) **CFL-explodes**: rest → λ=5.21 / V=3.8 L in 2 ms, then λ=15. Not a valid first-λ≥2 freeze (ANIM skipped the crossing). `/AMS` is not armed (ship CFL is fine until after λ≥2; AMS ruptured this LAW42 film on the A-finest ladder).

**Do not invent μ.** This golden is the honest Radioss QS-ish apples number, not a 54 kPa claim.

## Shared card (unchanged)

| | |
|---|---:|
| μ₁ | `(800 × 6894.757) / 1.75` ≈ 3.151888914×10⁶ Pa |
| α₁ | 2 |
| ρ | 1130 kg/m³ Desmopan 85085A ISO 1183-1 |
| H0 | 0.381 mm |
| Gapmin | CONTACT_KISS = 0.762 mm |
| `/ADYREL` | yes (full run) |
| `/AMS` | no |
| NUMELC / NUMELTG | 1554 / 0 |

## Run

```bash
bash radioss/install_openradioss.sh
bash radioss/A-inflate-qs-ish/run.sh
```

See `RUN.md` for the cycle tape. Warn still: `artifacts/warn-lambda2.png`.

## How web-mbd should ingest (`compare:inflate:qs`)

Today PR #18 FAIL-closes `src/oracle/inflate-a-radioss-qs-golden.json` as `status: EMPTY` with lock `loadFamily = qs-ish-dead-pressure`, `pMax = 54100`, `tRamp = 0`.

1. Copy **this** file to web-mbd `src/oracle/inflate-a-radioss-qs-golden.json`.
2. Extend `LOAD_FAMILY` / `lockedLawCardQsIsh()` / `parseInflateQsGolden` to accept **`qs-ish-pload-400ms`** with `pMax=65000`, `tRamp=0.40` (or constitutive-only law equality: μ/ρ/H0/α₁, and keep pMax/tRamp on the load-family object).
3. Keep `pnpm compare:inflate` on `dynamic-pload-40ms`. Do **not** mix families in one table.
4. Point `compare:inflate:qs` at the filled golden. Bands stay λ ≤ 2% / V ≤ 5% / p ≤ 5% **same load family**.
5. The toy path `qs-ish-dead-pressure` at 54100 Pa will **FAIL the p band** vs this golden (48.9%). That is the correct FAIL until the toy uses this load family (or Chiron files a different bar). Closing it by changing μ is forbidden.
6. Dead-pressure Radioss at 54100 Pa is **not** a usable freeze (CFL explode). Do not vendor that fork as the QS golden.

Exact warn numbers for the compare:

```
warn.frame      = 34
warn.t          = 0.170001
warn.lambdaMax  = 2.327123518375924
warn.p          = 27625.1625
warn.volume_mL  = 752.6256176704242
warn.psi_J      = 8.042896684001748
mesh.fingerprint = d9c56487
```
