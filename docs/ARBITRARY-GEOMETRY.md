# Arbitrary geometry (ORN-52)

**Ship path:** load-time **bake JSON**, not in-browser STEP remesh.

Pipeline: single-body manifold hygiene → **QuadriFlow** (batch CLI when present; Instant Meshes OK interactive) → quality gates (`free=0`, non-manifold=0) → bake JSON → browser load + **density knob** → Chiron quadmem + WASM ladder (same as letters).

**Demo:** owned closed torus `meshes/torus-demo.json` (not Bunny). Suzanne is not the default.

## Reuse vs new

**Kept:** `applyBakeMesh` + quadmem + ORN-49 WASM ladder + ORN-50 camera + ORN-51 quad wire + ORN-53 P0 Details/pressure.

**Killed:** O / plus / pill presets, SVG paste/upload, live occupancy-grid remesh for this ticket.

**New:** `tools/bake_quad.py` (`TorusQuads` / `MeshQuality` / `QuadriFlow` hook), torus density bakes, torus button + JSON upload, this doc.

## Density

Slider 1–5 swaps **prebaked** revolution-quad files (~2–4 quads across the tube at default):

| Level | File | Quads across tube | N (default bake) |
|------:|------|------------------:|------------------:|
| 1 | `torus-demo.d1.json` | 2 | 176 |
| 3 | `torus-demo.json` | 4 | 688 |
| 5 | `torus-demo.d5.json` | 8 | 2784 |

A/B/C stay on Design-PASS Gmsh bakes; the slider does not remesh letters.

## STEP / STL (CLI)

```bash
python3 tools/bake_quad.py --torus          # owned torus density ladder
# STL/STEP: hygiene + QuadriFlow when `quadriflow` is on PATH
# STEP via Gmsh OpenCASCADE → surface → remesh if needed
```

Browser **JSON upload** loads a bake with the same schema as `meshes/A.json` / `torus-demo.json`. In-browser QuadriFlow is stretch (not this ship).

## Limits

- **Single-body closed shell.** Multi-body STL/STEP is rejected (euler / component count).
- **Dirty STL** (holes, non-manifold, inverted soup): hygiene fails (`free≠0` or non-manifold). Repair before bake.
- **Open shells** fail the free-edge gate.
- **Size caps:** ≤ 8000 verts, ≤ 12000 quads (see `MeshQuality`).
- **Tris** only when needed to avoid bad quads. The torus demo is all-quad (`faceTris=[]`).
- Letters remain hollow 5 cm **film** blocks. The torus is a closed tube membrane (genus 1).

Rebuild:

```bash
python3 tools/bake_quad.py --torus
node test/torus-bake.mjs
node test/ladder-wasm.mjs
```
