# Inflation ABC

DynaPuff Bold → 5 cm hollow film shell → neo-Hookean inflate (letters **A · B · C**).

**Ship path (Quality clear for A):** Design-PASS Gmsh bake + **true quad membrane default**.

## Live
**GitHub Pages:** https://mikeornstein.github.io/inflation-abc/

(Enable Pages from `main` / root if the link 404s.)

## Local
```bash
python3 -m http.server 8080
# http://127.0.0.1:8080/
```

Default loads `meshes/A.json` (N=1554 orphan28) with quadmem ON. Opt out: `?quadmem=0`.

| Query | Meaning |
|-------|---------|
| `?letter=A\|B\|C` | Switch letter bake |
| `?quadmem=0` | Tri-split fallback/debug |
| `?wire=1` | Wire overlay |
| `?still=1&beauty=1&ramptowarn=1` | Capture still path |

## Locks
- μ = grill eng. (not invented)
- Warn at first λ_max ≥ 2
- Kiss contact · same μ
- A: Chiron 1–10 + Design kiss/continuous PASS (2026-09-07)
- B/C: meshes included; Design stills held

## Docs
- `docs/2026-09-07-quadmem-A-ship-clear.md`
- `docs/DEFAULT-QUADMEM.md`
- `meshes/A-LOCK.md`
- `SHIP.md`
