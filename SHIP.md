# Shippable state checklist (A)

- [x] Default membrane = true quadmem (`USE_QUAD_MEMBRANE` unless `?quadmem=0`)
- [x] Boot loads Design-PASS bake `meshes/A.json` (N=1554 orphan28) without requiring `?bake=`
- [x] Letter switch prefers bake JSON for A/B/C
- [x] Bake overwrite protected (`meshes/A-LOCK.md` / bake `--force`)
- [x] Quality: Chiron 1–10 + shipOk + Design post-pforce warn PASS
- [x] Lean publish tree (no `.venv`, no archive-dense, no bak)
- [ ] Public Pages URL
- [ ] CloudAgent on repo
