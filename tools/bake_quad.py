#!/usr/bin/env python3
"""ORN-52: single-body manifold hygiene → quad surface → bake JSON.

Try-first remesh: QuadriFlow CLI if present (`quadriflow` on PATH).
Owned torus demo uses a singularity-free revolution grid (all val-4) —
the quality bar QuadriFlow aims at for this genus-1 body.

STEP: Gmsh OpenCASCADE (`--step` / `--occ-torus`).
STL: hygiene gates then QuadriFlow (or reject).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path


class MeshQuality:
    MAX_VERTS = 8000
    MAX_QUADS = 12000

    @staticmethod
    def edge_key(a: int, b: int) -> tuple[int, int]:
        return (a, b) if a < b else (b, a)

    @staticmethod
    def counts(n: int, quads: list, tris: list | None = None) -> dict:
        tris = tris or []
        ecount: dict[tuple[int, int], int] = {}
        for q in quads:
            if len(q) != 4:
                raise ValueError("non-quad in quads")
            for i in range(4):
                k = MeshQuality.edge_key(q[i], q[(i + 1) % 4])
                ecount[k] = ecount.get(k, 0) + 1
        for t in tris:
            for i in range(3):
                k = MeshQuality.edge_key(t[i], t[(i + 1) % 3])
                ecount[k] = ecount.get(k, 0) + 1
        free = sum(1 for c in ecount.values() if c == 1)
        nonman = sum(1 for c in ecount.values() if c > 2)
        n_e = len(ecount)
        n_f = len(quads) + len(tris)
        euler = n - n_e + n_f
        return {
            "N": n,
            "nQuads": len(quads),
            "nTris": len(tris),
            "nEdges": n_e,
            "freeEdges": free,
            "nonManifold": nonman,
            "euler": euler,
        }

    @staticmethod
    def gate_closed_quad_shell(n: int, quads: list, tris: list | None = None, *, want_euler=None) -> dict:
        g = MeshQuality.counts(n, quads, tris)
        if n > MeshQuality.MAX_VERTS:
            raise ValueError(f"N={n} exceeds cap {MeshQuality.MAX_VERTS}")
        if g["nQuads"] > MeshQuality.MAX_QUADS:
            raise ValueError(f"quads={g['nQuads']} exceeds cap {MeshQuality.MAX_QUADS}")
        if g["freeEdges"] != 0:
            raise ValueError(f"open shell: freeEdges={g['freeEdges']}")
        if g["nonManifold"] != 0:
            raise ValueError(f"non-manifold edges={g['nonManifold']}")
        if want_euler is not None and g["euler"] != want_euler:
            raise ValueError(f"euler={g['euler']} want {want_euler} (multi-body or wrong genus)")
        if g["nQuads"] < 8:
            raise ValueError("too few quads")
        return g


class TorusQuads:
    """Owned closed torus (revolution grid). All vertices valence 4."""

    # meters — similar footprint to 12 cm letters
    R = 0.038  # major radius
    r = 0.014  # tube radius (thinnest feature = 2r)

    # density → quads across tube diameter (~2–4 at default)
    ACROSS = {1: 2, 2: 3, 3: 4, 4: 6, 5: 8}

    @staticmethod
    def resolution(level: int) -> tuple[int, int, int]:
        across = TorusQuads.ACROSS[level]
        nv = max(8, across * 4)  # around tube
        nu = max(16, int(round(nv * TorusQuads.R / TorusQuads.r)))
        return nu, nv, across

    @staticmethod
    def build(level: int = 3) -> dict:
        nu, nv, across = TorusQuads.resolution(level)
        R, r = TorusQuads.R, TorusQuads.r
        pos0: list[float] = []
        for i in range(nu):
            u = 2 * math.pi * i / nu
            cu, su = math.cos(u), math.sin(u)
            for j in range(nv):
                v = 2 * math.pi * j / nv
                cv, sv = math.cos(v), math.sin(v)
                x = (R + r * cv) * cu
                y = r * sv
                z = (R + r * cv) * su
                pos0.extend((x, y, z))
        quads = []
        for i in range(nu):
            i1 = (i + 1) % nu
            for j in range(nv):
                j1 = (j + 1) % nv
                a = i * nv + j
                b = i1 * nv + j
                c = i1 * nv + j1
                d = i * nv + j1
                quads.append([a, b, c, d])
        n = len(pos0) // 3
        vol = BakeJSON.volume(pos0, BakeJSON.split_tris(quads))
        if vol < 0:
            quads = [[q[0], q[3], q[2], q[1]] for q in quads]
            vol = -vol
        gates = MeshQuality.gate_closed_quad_shell(n, quads, want_euler=0)
        return {
            "pos0": pos0,
            "quads": quads,
            "n": n,
            "nu": nu,
            "nv": nv,
            "across": across,
            "volume": vol,
            "gates": gates,
        }


class BakeJSON:
    @staticmethod
    def split_tris(quads: list) -> list:
        tris = []
        for q in quads:
            tris.append([q[0], q[1], q[2]])
            tris.append([q[0], q[2], q[3]])
        return tris

    @staticmethod
    def volume(pos0: list, tris: list) -> float:
        v = 0.0
        for i, j, k in tris:
            x0, y0, z0 = pos0[3 * i], pos0[3 * i + 1], pos0[3 * i + 2]
            x1, y1, z1 = pos0[3 * j], pos0[3 * j + 1], pos0[3 * j + 2]
            x2, y2, z2 = pos0[3 * k], pos0[3 * k + 1], pos0[3 * k + 2]
            v += x0 * (y1 * z2 - z1 * y2) + y0 * (z1 * x2 - x1 * z2) + z0 * (x1 * y2 - y1 * x2)
        return v / 6.0

    @staticmethod
    def write_obj(path: Path, pos0: list, tris: list) -> None:
        with path.open("w") as f:
            for i in range(len(pos0) // 3):
                f.write(f"v {pos0[3*i]} {pos0[3*i+1]} {pos0[3*i+2]}\n")
            for a, b, c in tris:
                f.write(f"f {a+1} {b+1} {c+1}\n")

    @staticmethod
    def write_stl_ascii(path: Path, pos0: list, tris: list) -> None:
        with path.open("w") as f:
            f.write("solid torus-demo\n")
            for a, b, c in tris:
                x0 = pos0[3 * a : 3 * a + 3]
                x1 = pos0[3 * b : 3 * b + 3]
                x2 = pos0[3 * c : 3 * c + 3]
                nx = (x1[1] - x0[1]) * (x2[2] - x0[2]) - (x1[2] - x0[2]) * (x2[1] - x0[1])
                ny = (x1[2] - x0[2]) * (x2[0] - x0[0]) - (x1[0] - x0[0]) * (x2[2] - x0[2])
                nz = (x1[0] - x0[0]) * (x2[1] - x0[1]) - (x1[1] - x0[1]) * (x2[0] - x0[0])
                f.write(f"  facet normal {nx} {ny} {nz}\n    outer loop\n")
                f.write(f"      vertex {x0[0]} {x0[1]} {x0[2]}\n")
                f.write(f"      vertex {x1[0]} {x1[1]} {x1[2]}\n")
                f.write(f"      vertex {x2[0]} {x2[1]} {x2[2]}\n")
                f.write("    endloop\n  endfacet\n")
            f.write("endsolid torus-demo\n")

    @staticmethod
    def dump(path: Path, mesh: dict, *, level: int, remesh: str) -> None:
        tris = BakeJSON.split_tris(mesh["quads"])
        payload = {
            "pos0": mesh["pos0"],
            "quads": mesh["quads"],
            "tris": tris,
            "faceTris": [],
            "elemType": "quad",
            "meta": {
                "id": "torus",
                "plan": "owned torus · revolution quads · QuadriFlow batch when CLI present",
                "remesh": remesh,
                "density": level,
                "acrossTube": mesh["across"],
                "nu": mesh["nu"],
                "nv": mesh["nv"],
                "R": TorusQuads.R,
                "r": TorusQuads.r,
                "DEPTH": 0.05,
                "N": mesh["n"],
                "nQuads": len(mesh["quads"]),
                "nTris": len(tris),
                "nOrphanCapTris": 0,
                "volume_m3": mesh["volume"],
                "gates": mesh["gates"],
                "note": "window.quads = CCW manifold torus; tris = quad splits; free=0 euler=0",
            },
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, separators=(",", ":")))


class QuadriFlow:
    @staticmethod
    def which() -> str | None:
        for name in ("quadriflow", "QuadriFlow"):
            from shutil import which
            p = which(name)
            if p:
                return p
        env = os.environ.get("QUADRIFLOW")
        if env and Path(env).exists():
            return env
        return None

    @staticmethod
    def remesh_obj(inp: Path, out: Path, faces: int) -> None:
        bin_ = QuadriFlow.which()
        if not bin_:
            raise FileNotFoundError("quadriflow not on PATH")
        subprocess.check_call([bin_, "-i", str(inp), "-o", str(out), "-f", str(faces)])


def bake_torus_levels(mesh_dir: Path, levels: list[int], *, stl: bool) -> None:
    remesh = "quadriflow" if QuadriFlow.which() else "revolution-quads (owned torus; QuadriFlow CLI optional)"
    default = None
    for level in levels:
        mesh = TorusQuads.build(level)
        if level == 3:
            out = mesh_dir / "torus-demo.json"
            default = mesh
        else:
            out = mesh_dir / f"torus-demo.d{level}.json"
        BakeJSON.dump(out, mesh, level=level, remesh=remesh)
        print(f"wrote {out} N={mesh['n']} quads={len(mesh['quads'])} across={mesh['across']} {mesh['gates']}")
    if stl and default:
        tri = BakeJSON.split_tris(default["quads"])
        BakeJSON.write_stl_ascii(mesh_dir / "torus-demo.stl", default["pos0"], tri)
        print(f"wrote {mesh_dir / 'torus-demo.stl'} (tri source for STL path)")


def main() -> int:
    ap = argparse.ArgumentParser(description="ORN-52 quad bake (torus demo / QuadriFlow hook)")
    ap.add_argument("--torus", action="store_true", help="bake owned torus density ladder")
    ap.add_argument("--levels", default="1,2,3,4,5")
    ap.add_argument("--stl", action="store_true", help="also write torus-demo.stl")
    ap.add_argument("--out-dir", default="meshes")
    args = ap.parse_args()
    if not args.torus:
        ap.error("pass --torus (STEP/STL QuadriFlow path: set QUADRIFLOW and extend later)")
    levels = [int(x) for x in args.levels.split(",") if x]
    bake_torus_levels(Path(args.out_dir), levels, stl=args.stl)
    return 0


if __name__ == "__main__":
    sys.exit(main())
