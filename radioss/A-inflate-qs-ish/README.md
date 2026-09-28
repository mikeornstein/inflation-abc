# OpenRadioss — letter A inflate **QS-ish** golden

Labeled load family for web-mbd `compare:inflate:qs` (Chiron E.17 / Themis ABC QS apples).

**Not** `dynamic-pload-40ms`. **μ and ρ are not retuned.** OpenRadioss stays offline (AGPL).

## Why this tape exists

PR #8 / `radioss/A-inflate` is a **dynamic** `/PLOAD` 0 → 65 kPa in **40 ms** with `/ADYREL`. First λ_max ≥ 2 is **t ≈ 22 ms, p ≈ 35769 Pa, V ≈ 902 mL**. Inflation ABC quasi-static warn is **~54100 Pa**. Those are different load families. Closing the gap by changing μ or ρ is forbidden.

This directory is a **QS-ish** load-schedule fork of the same LAW42 card + ship A mesh:

| Lever | This tape | Dynamic PR #8 |
| --- | --- | --- |
| μ₁ | `(800 × 6894.757) / 1.75` Pa | same |
| α₁ | 2 | same |
| ρ | 1130 kg/m³ | same |
| H0 | 0.381 mm | same |
| Gapmin | CONTACT_KISS = 0.762 mm | same |
| mesh | N=1554, NUMELC=1554, NUMELTG=0, fingerprint `d9c56487` | same |
| `/PLOAD` | 0 → 65 kPa in **0.40 s**, hold to **0.50 s** | 0 → 65 kPa in **0.04 s** |
| `/ANIM/DT` | 0.005 s | 0.002 s |
| `/ADYREL` | yes (full run) | yes |
| `/AMS` | no (ship CFL OK until after λ≥2) | no |
| loadFamily | `qs-ish-pload-400ms` | `dynamic-pload-40ms` |

QS-ish means **slower explicit ramp + adaptive dynamic relaxation**, not a true implicit static solve, not MONVOL, and **not** the web-mbd toy step `qs-ish-dead-pressure` (pMax=54100, tRamp=0).

## Run

```bash
bash radioss/install_openradioss.sh
python3 tools/mesh_to_radioss.py --check --qs-ish \
  --out-dir radioss/A-inflate-qs-ish \
  --note "QS-ish A-inflate; slower PLOAD; μ/ρ locked"
bash radioss/A-inflate-qs-ish/run.sh
```

See `RUN.md` for the job that actually ran. Freeze-frame golden:

- `artifacts/inflate-a-radioss-qs-golden.json`
- copy at `inflate-a-radioss-qs-golden.json` (deck root, for Daedalus)

## How web-mbd should ingest

Today web-mbd PR #18 FAIL-closes `src/oracle/inflate-a-radioss-qs-golden.json` as `status: EMPTY` with lock:

- `loadFamily = qs-ish-dead-pressure`
- `pMax = 54100`, `tRamp = 0`
- `parseInflateQsGolden` **requires** that family string

This Radioss tape is **honestly** `qs-ish-pload-400ms` with `pMax = 65000`, `tRamp = 0.40`. Daedalus should:

1. Copy `inflate-a-radioss-qs-golden.json` into web-mbd `src/oracle/inflate-a-radioss-qs-golden.json`.
2. Extend `LOAD_FAMILY` / `lockedLawCardQsIsh()` / `parseInflateQsGolden` to accept **`qs-ish-pload-400ms`** (or treat constitutive locks μ/ρ/H0/α₁ as the law-card equality and keep pMax/tRamp on the load-family object).
3. Keep `pnpm compare:inflate` on `dynamic-pload-40ms`. Do **not** compare this golden to the dynamic toy path.
4. Point `compare:inflate:qs` at the filled golden. Bands stay λ ≤ 2% / V ≤ 5% / p ≤ 5% **same load family**.
5. Do not invent μ to force p=54100 on the 40 ms tape.

If the freeze-frame p is in the ABC ~54 kPa neighborhood, that is the QS apples number. If it is not, `RUN.md` states the blocker with evidence — still no μ retune.
