# Daedalus — wire Radioss QS-ish golden into web-mbd `compare:inflate:qs`

Source of truth: `radioss/A-inflate-qs-ish/inflate-a-radioss-qs-golden.json` on this PR
(`cursor/openradioss-a-qs-ish-b1bc`, inflation-abc).

OpenRadioss AGPL stays offline. Copy **JSON only**.

## Copy

```
inflation-abc: radioss/A-inflate-qs-ish/inflate-a-radioss-qs-golden.json
        →
web-mbd:      src/oracle/inflate-a-radioss-qs-golden.json
```

Set `status` remains `"filled"`. `provenance.source` is `"openradioss"`.

## Parser / law-card lock (required)

`parseInflateQsGolden` currently requires `loadFamily === "qs-ish-dead-pressure"`
and `lockedLawCardQsIsh()` pins `pMax=54100`, `tRamp=0`. This tape is:

| field | value |
| --- | --- |
| loadFamily | `qs-ish-pload-400ms` |
| pMax | 65000 |
| tRamp | 0.40 |
| rayleighAlpha | 80 |
| mu1 / rho / h0 / alpha1 / gapMin | **same lock as dynamic** |

Either add a `LOAD_FAMILY_QS_ISH_PLOAD_400MS` and a matching `lockedLawCardQsIshPload400ms()`,
or compare constitutive fields only and treat pMax/tRamp as load-family identity.

`pnpm compare:inflate` (dynamic) must stay green and untouched.

## Warn numbers

Use the JSON `warn` object bit-for-bit (do not re-round). Ψ ≥ 0. Mesh fingerprint `d9c56487`.

## What will FAIL (honest)

Toy `qs-ish-dead-pressure` at 54100 Pa vs this golden: **p rel ≈ 49%** (band 5%).
That is not a Radioss bug to “fix” with μ. See README blocker. Dead 54100 Pa on
this engine CFL-explodes (`forks/dead-pressure`).
