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
import tempfile
from contextlib import contextmanager
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
        comps = MeshQuality.components(n, quads, tris)
        return {
            "N": n,
            "nQuads": len(quads),
            "nTris": len(tris),
            "nEdges": n_e,
            "freeEdges": free,
            "nonManifold": nonman,
            "euler": euler,
            "components": comps,
        }

    @staticmethod
    def components(n: int, quads: list, tris: list | None = None) -> int:
        tris = tris or []
        parent = list(range(n))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        used: set[int] = set()
        for q in quads:
            used.update(q)
            for i in range(4):
                union(q[i], q[(i + 1) % 4])
        for t in tris:
            used.update(t)
            for i in range(3):
                union(t[i], t[(i + 1) % 3])
        if not used:
            return 0
        return len({find(i) for i in used})

    @staticmethod
    def gate_closed_quad_shell(
        n: int,
        quads: list,
        tris: list | None = None,
        *,
        want_euler=None,
        check_size: bool = True,
    ) -> dict:
        g = MeshQuality.counts(n, quads, tris)
        if check_size:
            if n > MeshQuality.MAX_VERTS:
                raise ValueError(f"N={n} exceeds cap {MeshQuality.MAX_VERTS}")
            if g["nQuads"] > MeshQuality.MAX_QUADS:
                raise ValueError(f"quads={g['nQuads']} exceeds cap {MeshQuality.MAX_QUADS}")
        if g["freeEdges"] != 0:
            raise ValueError(f"open shell: freeEdges={g['freeEdges']}")
        if g["nonManifold"] != 0:
            raise ValueError(f"non-manifold edges={g['nonManifold']}")
        if g["components"] != 1:
            raise ValueError(f"multi-body: {g['components']} components")
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
    def read_obj(path: Path) -> tuple[list[float], list, list]:
        pos0: list[float] = []
        quads: list = []
        tris: list = []
        for line in path.read_text().splitlines():
            if line.startswith("v "):
                pos0.extend(float(x) for x in line.split()[1:4])
            elif line.startswith("f "):
                ids = [int(p.split("/")[0]) - 1 for p in line.split()[1:]]
                if len(ids) == 4:
                    quads.append(ids)
                elif len(ids) == 3:
                    tris.append(ids)
                else:
                    raise ValueError(f"OBJ face arity {len(ids)}")
        return pos0, quads, tris

    @staticmethod
    def dump_cad(path: Path, mesh: dict, *, meta: dict) -> None:
        extra = mesh.get("faceTris") or []
        split = BakeJSON.split_tris(mesh["quads"])
        payload = {
            "pos0": mesh["pos0"],
            "quads": mesh["quads"],
            "tris": split + extra,
            "faceTris": extra,
            "elemType": "quad" if not extra else "mixed",
            "meta": {
                "DEPTH": 0.05,
                "N": mesh["n"],
                "nQuads": len(mesh["quads"]),
                "nTris": len(split) + len(extra),
                "nOrphanCapTris": len(extra),
                "volume_m3": mesh["volume"],
                "gates": mesh["gates"],
                **meta,
            },
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, separators=(",", ":")))

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


class GmshCad:
    """STEP via OpenCASCADE → surface mesh → Blossom recombine; QuadriFlow if on PATH.

    STL: dirty/open/multi-body fail hygiene. Prefer QuadriFlow on the triangle soup;
    Gmsh classify+recombine is a fallback (often leftover tris / split surfaces).
    """

    @staticmethod
    @contextmanager
    def session():
        import gmsh

        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 1)
        try:
            yield gmsh
        finally:
            gmsh.finalize()

    @staticmethod
    def mesh_size_from_bbox(gmsh, *, across: int = 4) -> float:
        xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(-1, -1)
        thin = min(xmax - xmin, ymax - ymin, zmax - zmin)
        if thin <= 0:
            raise ValueError("degenerate bounding box")
        return thin / max(2, across)

    @staticmethod
    def extract(gmsh) -> tuple[list[float], list, list]:
        node_tags, coords, _ = gmsh.model.mesh.getNodes()
        node_tags = [int(t) for t in node_tags]
        coords = [float(x) for x in coords]
        tag_to_i = {t: i for i, t in enumerate(node_tags)}
        pos0 = list(coords)
        quads: list = []
        tris: list = []
        types, _tags, node_lists = gmsh.model.mesh.getElements(2)
        for etype, nodes in zip(types, node_lists):
            et = int(etype)
            nodes = [int(x) for x in nodes]
            if et == 3:
                for k in range(0, len(nodes), 4):
                    quads.append([tag_to_i[nodes[k + j]] for j in range(4)])
            elif et == 2:
                for k in range(0, len(nodes), 3):
                    tris.append([tag_to_i[nodes[k + j]] for j in range(3)])
        return pos0, quads, tris

    @staticmethod
    def maybe_quadriflow(pos0: list, quads: list, tris: list, *, faces: int) -> tuple[list[float], list, list, str]:
        if not QuadriFlow.which():
            return pos0, quads, tris, "gmsh-blossom (QuadriFlow CLI optional)"
        all_tris = list(tris) + BakeJSON.split_tris(quads)
        with tempfile.TemporaryDirectory() as td:
            inp = Path(td) / "in.obj"
            out = Path(td) / "out.obj"
            BakeJSON.write_obj(inp, pos0, all_tris)
            QuadriFlow.remesh_obj(inp, out, faces)
            pos1, q1, t1 = BakeJSON.read_obj(out)
        return pos0 if not q1 else pos1, q1 or quads, t1, "quadriflow"

    @staticmethod
    def compact(pos0: list, quads: list, tris: list) -> tuple[list[float], list, list]:
        used: set[int] = set()
        for q in quads:
            used.update(q)
        for t in tris:
            used.update(t)
        order = sorted(used)
        old_to_new = {old: i for i, old in enumerate(order)}
        new_pos: list[float] = []
        for old in order:
            new_pos.extend(pos0[3 * old : 3 * old + 3])
        quads = [[old_to_new[i] for i in q] for q in quads]
        tris = [[old_to_new[i] for i in t] for t in tris]
        return new_pos, quads, tris

    @staticmethod
    def pack(pos0: list, quads: list, tris: list, *, remesh: str) -> dict:
        pos0, quads, tris = GmshCad.compact(pos0, quads, tris)
        n = len(pos0) // 3
        vol = BakeJSON.volume(pos0, BakeJSON.split_tris(quads) + tris)
        if vol < 0:
            quads = [[q[0], q[3], q[2], q[1]] for q in quads]
            tris = [[t[0], t[2], t[1]] for t in tris]
            vol = -vol
        gates = MeshQuality.gate_closed_quad_shell(n, quads, tris)
        return {
            "pos0": pos0,
            "quads": quads,
            "faceTris": tris,
            "n": n,
            "across": None,
            "volume": vol,
            "gates": gates,
            "remesh": remesh,
        }

    @staticmethod
    def occ_torus(*, across: int = 4) -> dict:
        with GmshCad.session() as gmsh:
            gmsh.model.add("occ-torus")
            gmsh.model.occ.addTorus(0, 0, 0, TorusQuads.R, TorusQuads.r)
            gmsh.model.occ.synchronize()
            vols = gmsh.model.getEntities(3)
            if len(vols) != 1:
                raise ValueError(f"multi-body: {len(vols)} volumes")
            size = (2 * TorusQuads.r) / max(2, across)
            gmsh.option.setNumber("Mesh.MeshSizeMax", size)
            gmsh.option.setNumber("Mesh.Algorithm", 6)
            gmsh.model.mesh.generate(2)
            gmsh.model.mesh.recombine()
            pos0, quads, tris = GmshCad.extract(gmsh)
        pos0, quads, tris, remesh = GmshCad.maybe_quadriflow(
            pos0, quads, tris, faces=max(64, len(quads) or 128)
        )
        mesh = GmshCad.pack(pos0, quads, tris, remesh=remesh)
        mesh["across"] = across
        return mesh

    @staticmethod
    def from_step(path: Path, *, across: int = 4) -> dict:
        with GmshCad.session() as gmsh:
            gmsh.model.add("cad")
            gmsh.model.occ.importShapes(str(path))
            gmsh.model.occ.synchronize()
            vols = gmsh.model.getEntities(3)
            if len(vols) > 1:
                raise ValueError(f"multi-body: {len(vols)} volumes (single-body only)")
            if not gmsh.model.getEntities(2) and not vols:
                raise ValueError("STEP has no surfaces/volumes")
            size = GmshCad.mesh_size_from_bbox(gmsh, across=across)
            gmsh.option.setNumber("Mesh.MeshSizeMax", size)
            gmsh.option.setNumber("Mesh.Algorithm", 6)
            gmsh.model.mesh.generate(2)
            gmsh.model.mesh.recombine()
            pos0, quads, tris = GmshCad.extract(gmsh)
        pos0, quads, tris, remesh = GmshCad.maybe_quadriflow(
            pos0, quads, tris, faces=max(64, len(quads) or 128)
        )
        return GmshCad.pack(pos0, quads, tris, remesh=remesh)

    @staticmethod
    def from_stl(path: Path, *, across: int = 4) -> dict:
        with GmshCad.session() as gmsh:
            gmsh.merge(str(path))
            if gmsh.model.getEntities(3):
                raise ValueError("STL imported as volume — expected a surface shell")
            angle = 40.0 * math.pi / 180.0
            gmsh.model.mesh.classifySurfaces(angle, True, True, angle)
            gmsh.model.mesh.createGeometry()
            size = GmshCad.mesh_size_from_bbox(gmsh, across=across)
            gmsh.option.setNumber("Mesh.MeshSizeMax", size)
            gmsh.option.setNumber("Mesh.Algorithm", 6)
            gmsh.model.mesh.generate(2)
            gmsh.model.mesh.recombine()
            pos0, quads, tris = GmshCad.extract(gmsh)
        pos0, quads, tris, remesh = GmshCad.maybe_quadriflow(
            pos0, quads, tris, faces=max(64, len(quads) or 128)
        )
        return GmshCad.pack(pos0, quads, tris, remesh=remesh)


def bake_torus_levels(mesh_dir: Path, levels: list[int], *, write_stl: bool) -> None:
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
    if write_stl and default:
        tri = BakeJSON.split_tris(default["quads"])
        BakeJSON.write_stl_ascii(mesh_dir / "torus-demo.stl", default["pos0"], tri)
        print(f"wrote {mesh_dir / 'torus-demo.stl'} (tri source for STL path; not a Pages asset)")


def bake_cad_to(path: Path, mesh: dict, *, ident: str, plan: str) -> None:
    BakeJSON.dump_cad(
        path,
        mesh,
        meta={
            "id": ident,
            "plan": plan,
            "remesh": mesh["remesh"],
            "acrossTube": mesh.get("across"),
            "note": "CAD bake JSON; upload in Details or load like letter/torus bakes",
        },
    )
    print(f"wrote {path} N={mesh['n']} quads={len(mesh['quads'])} tris={len(mesh.get('faceTris') or [])} {mesh['gates']}")


def self_test() -> None:
    mesh = TorusQuads.build(3)
    if mesh["gates"]["freeEdges"] != 0 or mesh["gates"]["euler"] != 0:
        raise SystemExit("owned torus failed gates")
    try:
        MeshQuality.gate_closed_quad_shell(mesh["n"], mesh["quads"][:-1], want_euler=0)
        raise SystemExit("open shell should fail")
    except ValueError as e:
        if "open shell" not in str(e):
            raise
    try:
        # two disjoint closed cubes (not open quads — those fail free-edge first)
        def cube(xoff: float, i0: int) -> tuple[list[float], list]:
            corners = [
                (0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0),
                (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1),
            ]
            pos: list[float] = []
            for x, y, z in corners:
                pos.extend((x + xoff, float(y), float(z)))
            q = [
                [0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4],
                [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7],
            ]
            return pos, [[i0 + i for i in face] for face in q]

        p0, q0 = cube(0.0, 0)
        p1, q1 = cube(3.0, 8)
        MeshQuality.gate_closed_quad_shell(16, q0 + q1)
        raise SystemExit("multi-body should fail")
    except ValueError as e:
        if "multi-body" not in str(e):
            raise
    print("ok  bake_quad self-test (gates)")
    try:
        import gmsh  # noqa: F401
    except ImportError:
        print("skip OCC torus (gmsh not installed)")
        return
    occ = GmshCad.occ_torus(across=4)
    print(
        "ok  OCC torus  N="
        + str(occ["n"])
        + " quads="
        + str(len(occ["quads"]))
        + " leftoverTris="
        + str(len(occ["faceTris"]))
        + " remesh="
        + occ["remesh"]
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="ORN-52 quad bake (torus demo / STEP+STL / QuadriFlow)")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--torus", action="store_true", help="bake owned torus density ladder")
    src.add_argument("--occ-torus", action="store_true", help="Gmsh OpenCASCADE torus → surface → remesh")
    src.add_argument("--step", type=Path, help="Gmsh OCC import STEP → surface → remesh")
    src.add_argument("--stl", type=Path, help="hygiene + remesh STL (QuadriFlow preferred)")
    src.add_argument("--self-test", action="store_true", help="quality-gate + optional OCC torus check")
    ap.add_argument("--levels", default="1,2,3,4,5")
    ap.add_argument("--write-stl", action="store_true", help="with --torus, also write torus-demo.stl")
    ap.add_argument("--out-dir", default="meshes")
    ap.add_argument("--out", type=Path, help="output JSON for --step/--stl/--occ-torus")
    ap.add_argument("--across", type=int, default=4, help="quads across thinnest bbox extent")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.torus:
        bake_torus_levels(Path(args.out_dir), [int(x) for x in args.levels.split(",") if x], write_stl=args.write_stl)
        return 0
    if not args.out:
        ap.error("--out is required for --step / --stl / --occ-torus")
    if args.occ_torus:
        mesh = GmshCad.occ_torus(across=args.across)
        bake_cad_to(args.out, mesh, ident="occ-torus", plan="Gmsh OpenCASCADE torus → surface → remesh")
        return 0
    if args.step:
        mesh = GmshCad.from_step(args.step, across=args.across)
        bake_cad_to(args.out, mesh, ident=args.step.stem, plan="Gmsh OpenCASCADE STEP → surface → remesh")
        return 0
    mesh = GmshCad.from_stl(args.stl, across=args.across)
    bake_cad_to(args.out, mesh, ident=args.stl.stem, plan="STL hygiene → remesh (QuadriFlow preferred)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
