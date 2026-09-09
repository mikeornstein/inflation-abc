# Pressure ladder (ORN-49)

Interactive pressure scrub is a **WASM SIMD lerp** of a **load-time Chiron bake**. The neo-Hookean quad-membrane solver is unchanged.

## Reuse-and-delete

**Already there (kept):**
- Chiron quadmem JS solver in `index.html` (analytic NH, wrinkle clamp, kiss contact, warm start, `minimize`).
- Contiguous `Float64Array` pos/force + scratch reuse (the parked SoA / no-GC path).
- WebGL2 film draw + existing pressure slider.

**Not rebuilt:** no second physics stack, no WebGPU force kernel (would fork constitutive math vs the Chiron bar).

**Unavoidable new surface:**
- `wasm/ladder.wasm` — `f32x4` SoA pack + lerp (ticket requires WASM and/or WebGPU; this is the silky playback path).
- Load-time bake orchestration that snapshots existing `minimize` states.

Interactive per-frame `minimize(8)` / tip `warmClimbToP` is skipped once ≥2 rungs exist (`?live=1` restores it).

## Bake resolution

| | Default |
|---|---|
| ΔP | **2000 Pa** (`?dP=` to override, min 250) |
| Range | 0 … slider max (80000 Pa) → **41 rungs** |
| Iters / rung | 24, doubled every 4th rung (`?ladderIters=`) |
| Mesh | Design-PASS `meshes/{A,B,C}.json`, quadmem ON |
| Constitutive | same μ, λ≥2 warn, kiss contact as live solver |

Each rung is a warm-started Chiron equilibrium. Between rungs, vertex positions and λ_max are **linear in P** (not a solve). Exact slider values that land on a rung replay that snapshot (f32).

A warn still at ~54100 Pa for letter A is bracketed by 54000 and 56000 Pa rungs; interpolated λ is documented as playback, not a new residual-driven solve.

## Query flags

| Query | Meaning |
|-------|---------|
| *(default)* | Bake ladder then WASM SIMD scrub |
| `?live=1` | Old per-step CPU settle (multi-second stalls possible) |
| `?dP=1000` | Finer ladder |
| `?ladderIters=40` | Deeper settle per rung |
| `?still=1` / `?ramptowarn=1` | Capture path; ladder off |

## Rebuild WASM

```bash
wasm/build.sh   # rustc wasm32-unknown-unknown + simd128
node test/ladder-wasm.mjs
```

GitHub Pages serves the committed `wasm/ladder.wasm` (no runtime compile).
