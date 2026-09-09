# Mesh A lock (Zeus 2026-09-06)

**Ship A = remesh N=1554 orphan28** (`meshes/A.json`).

Do **not** overwrite with coarse N=1032. Coarse parked at `meshes/A-coarse-N1032-pre-remesh.json`.
Remesh backup: `meshes/A-orphan-remesh-N1554.json`.

`bake_gmsh_letter.py A` **refuses** overwrite of this ship file unless `--force`.
Experiments: `--out meshes/A-scratch.json`.

Chiron 1–10 correctness on this mesh. Δ vs tri is regression only.
