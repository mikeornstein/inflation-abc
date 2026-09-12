#!/usr/bin/env python3
"""All-quad letter film densities for the OpenRadioss refine study.

Does not overwrite meshes/{A,B,C}.json. Does not retune μ/ρ.

Letter A (default): coarse Gmsh remesh + ship/fine/(finer/finest).
Letters B,C (Mike 2026-09-12): ship / fine / finer only — no coarse row, no finest.

Ship  = locked bake meshes/{L}.json (pair orphan cap tris; midplane not remeshed).
        Leftover cap ears on an even-boundary patch are reconnected to /SHELL
        (same rest letter). If unpaired tris remain (B midplane), one conforming
        mixed 1-to-4 turns them into quads — no /SH3N, outline not Gmsh-remeshed.
Fine  = nested linear 1-to-4 of the closed all-quad ship shell.
Finer = nested linear 1-to-4 of fine. Study meshes may exceed web bake MAX_VERTS.

Locked physics (same as A-inflate): LAW42 μ1=MU α1=2, ρ=1130, H0,
Gapmin=CONTACT_KISS, /SHELL quads only, Ishell=1, free-free /ADYREL.
No /SH3N, no 3-2-1 /BCS.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from bake_quad import BakeJSON, GmshCad, MeshQuality
from mesh_to_radioss import _merge_tri_pair, enclosed_volume, load_mesh, quadify_orphans

DEPTH = 0.05  # ship z span (−0.025 … +0.025)
SHIP_N = 1554

# Prefer ~N_ship/2 (Chiron/Themis “successive ~2× denser N”), all-quad only.
COARSE_TRIALS = (
    {"every": 3, "lc": 0.016, "nz": 6},
    {"every": 2, "lc": 0.012, "nz": 4},
    {"every": 2, "lc": 0.014, "nz": 4},
)


def _signed_area_xy(pts) -> float:
    a = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return 0.5 * a


def _vol(pos: np.ndarray, quads) -> float:
    def tri(a, b, c):
        return (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            + a[1] * (b[2] * c[0] - b[0] * c[2])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6.0

    v = 0.0
    for q in quads:
        a, b, c, d = (pos[i] for i in q)
        v += tri(a, b, c) + tri(a, c, d)
    return v


def _flip_quads(quads):
    return [(q[0], q[3], q[2], q[1]) for q in quads]


def extract_front_midplane(pos: np.ndarray, quads):
    zmax = float(pos[:, 2].max())
    front_q = [q for q in quads if all(abs(pos[i, 2] - zmax) < 1e-8 for i in q)]
    if not front_q:
        raise SystemExit("no front-cap quads")
    ecount = defaultdict(int)
    for q in front_q:
        for k in range(4):
            a, b = q[k], q[(k + 1) % 4]
            ecount[tuple(sorted((a, b)))] += 1
    bnd = [e for e, c in ecount.items() if c == 1]
    bn = defaultdict(list)
    for a, b in bnd:
        bn[a].append(b)
        bn[b].append(a)
    used = set()
    loops = []
    for start in bn:
        if start in used:
            continue
        loop = [start]
        used.add(start)
        prev = None
        cur = start
        while True:
            nxts = [n for n in bn[cur] if n != prev]
            if not nxts:
                break
            nxt = nxts[0]
            if nxt == start:
                break
            loop.append(nxt)
            used.add(nxt)
            prev, cur = cur, nxt
        loops.append(loop)
    loops.sort(key=lambda L: abs(_signed_area_xy([pos[i, :2] for i in L])), reverse=True)
    return front_q, loops, zmax


def every_k(pts, k: int):
    if k <= 1:
        return list(pts)
    out = list(pts[::k])
    if len(out) >= 2 and np.linalg.norm(np.asarray(out[-1]) - np.asarray(out[0])) < 1e-12:
        out = out[:-1]
    if len(out) < 8:
        return list(pts)
    return out


def _pair_tris(tris):
    if not tris:
        return [], []
    edges = defaultdict(list)
    T = [tuple(int(i) for i in t) for t in tris]
    for ti, t in enumerate(T):
        for j in range(3):
            e = tuple(sorted((t[j], t[(j + 1) % 3])))
            edges[e].append(ti)
    used = set()
    extra = []
    for e, ids in edges.items():
        if len(ids) != 2:
            continue
        a, b = ids
        if a in used or b in used:
            continue
        used.add(a)
        used.add(b)
        extra.append(list(_merge_tri_pair(T[a], T[b], e)))
    leftover = [T[i] for i in range(len(T)) if i not in used]
    return extra, leftover


def compact_mesh(xyz: np.ndarray, quads, tris):
    pos0 = [float(v) for v in np.asarray(xyz, dtype=float).ravel()]
    return GmshCad.compact(pos0, quads, tris)


def gmsh_midplane(loop_pts_list, lc: float):
    import gmsh

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    gmsh.model.add("A-mid")
    occ = gmsh.model.occ

    def add_wire(pts):
        tags = [occ.addPoint(float(x), float(y), 0.0, lc) for x, y in pts]
        lines = [occ.addLine(tags[i], tags[(i + 1) % len(tags)]) for i in range(len(tags))]
        return occ.addCurveLoop(lines)

    oriented = []
    for pts in loop_pts_list:
        A = _signed_area_xy(pts)
        oriented.append((abs(A), A, list(pts)))
    oriented.sort(reverse=True)
    wires = []
    for i, (_aa, A, pp) in enumerate(oriented):
        if i == 0 and A < 0:
            pp = pp[::-1]
        if i > 0 and A > 0:
            pp = pp[::-1]
        wires.append(add_wire(pp))
    occ.addPlaneSurface(wires)
    occ.synchronize()
    gmsh.option.setNumber("Mesh.Algorithm", 8)  # DelQuad
    gmsh.option.setNumber("Mesh.RecombineAll", 1)
    gmsh.option.setNumber("Mesh.RecombinationAlgorithm", 1)
    gmsh.option.setNumber("Mesh.MeshSizeMax", lc)
    gmsh.model.mesh.generate(2)
    gmsh.model.mesh.recombine()
    node_tags, coords, _ = gmsh.model.mesh.getNodes()
    node_tags = [int(t) for t in node_tags]
    tag_to_i = {t: i for i, t in enumerate(node_tags)}
    types, _tags, node_lists = gmsh.model.mesh.getElements(2)
    quads, tris = [], []
    for etype, nodes in zip(types, node_lists):
        et = int(etype)
        nodes = [int(x) for x in nodes]
        if et == 3:
            for k in range(0, len(nodes), 4):
                quads.append([tag_to_i[nodes[k + j]] for j in range(4)])
        elif et == 2:
            for k in range(0, len(nodes), 3):
                tris.append([tag_to_i[nodes[k + j]] for j in range(3)])
    xyz = np.asarray(coords, dtype=float).reshape(-1, 3)
    gmsh.finalize()
    extra, leftover = _pair_tris(tris)
    if leftover:
        raise ValueError(f"gmsh midplane left {len(leftover)} unpaired tris — refuse /SH3N")
    pos0, quads, empty = compact_mesh(xyz, quads + extra, [])
    if empty:
        raise ValueError("compact leftover tris")
    n = len(pos0) // 3
    gates = MeshQuality.counts(n, quads, [])
    if gates["freeEdges"] == 0:
        raise ValueError("midplane should be open (letter outline), not a closed shell")
    return pos0, quads, gates


def midplane_boundary_loops(quads):
    ecount = defaultdict(int)
    for q in quads:
        for k in range(4):
            a, b = q[k], q[(k + 1) % 4]
            ecount[tuple(sorted((int(a), int(b))))] += 1
    bnd = [e for e, c in ecount.items() if c == 1]
    bn = defaultdict(list)
    for a, b in bnd:
        bn[a].append(b)
        bn[b].append(a)
    used = set()
    loops = []
    for start in bn:
        if start in used:
            continue
        loop = [start]
        used.add(start)
        prev = None
        cur = start
        while True:
            nxts = [x for x in bn[cur] if x != prev]
            if not nxts:
                break
            nxt = nxts[0]
            if nxt == start:
                break
            loop.append(nxt)
            used.add(nxt)
            prev, cur = cur, nxt
        loops.append(loop)
    return loops


def extrude_film(pos0, mid_quads, *, nz: int, depth: float = DEPTH):
    """Prism the 2-D all-quad midplane into a closed hollow film (caps + walls)."""
    nmid = len(pos0) // 3
    xy = np.asarray(pos0, dtype=float).reshape(nmid, 3)[:, :2]
    loops = midplane_boundary_loops(mid_quads)
    loops.sort(key=lambda L: abs(_signed_area_xy([xy[i] for i in L])), reverse=True)
    loops_m = []
    for iL, L in enumerate(loops):
        A = _signed_area_xy([xy[i] for i in L])
        Lm = list(L)
        if iL == 0 and A < 0:
            Lm = Lm[::-1]
        if iL > 0 and A > 0:
            Lm = Lm[::-1]
        loops_m.append(Lm)
    bnd_ordered = []
    seen = set()
    for L in loops_m:
        for i in L:
            if i not in seen:
                bnd_ordered.append(i)
                seen.add(i)
    z_front = 0.5 * depth
    z_back = -0.5 * depth
    new_pos = []
    for i in range(nmid):
        new_pos.append([float(xy[i, 0]), float(xy[i, 1]), z_front])
    for i in range(nmid):
        new_pos.append([float(xy[i, 0]), float(xy[i, 1]), z_back])
    wall_index = {}
    for i in range(nmid):
        wall_index[(i, nz)] = i
        wall_index[(i, 0)] = nmid + i
    nid = 2 * nmid
    for k in range(1, nz):
        z = z_back + k * depth / nz
        for i in bnd_ordered:
            wall_index[(i, k)] = nid
            new_pos.append([float(xy[i, 0]), float(xy[i, 1]), z])
            nid += 1
    new_pos = np.asarray(new_pos, dtype=float)
    new_quads = []
    for q in mid_quads:
        new_quads.append(tuple(int(i) for i in q))
    for q in mid_quads:
        a, b, c, d = (int(i) for i in q)
        new_quads.append((nmid + a, nmid + d, nmid + c, nmid + b))
    for L in loops_m:
        nL = len(L)
        for j in range(nL):
            i0, i1 = L[j], L[(j + 1) % nL]
            for k in range(nz):
                a = wall_index[(i0, k)]
                b = wall_index[(i1, k)]
                c = wall_index[(i1, k + 1)]
                d = wall_index[(i0, k + 1)]
                new_quads.append((a, b, c, d))
    V = _vol(new_pos, new_quads)
    if V < 0:
        new_quads = _flip_quads(new_quads)
        V = _vol(new_pos, new_quads)
    if V <= 0:
        raise SystemExit(f"extrude V not positive: {V}")
    n = len(new_pos)
    gates = MeshQuality.gate_closed_quad_shell(n, new_quads, want_euler=0)
    return new_pos, new_quads, V, gates


def subdivide_closed_quads(
    pos: np.ndarray, quads, *, check_size: bool = True, want_euler: int | None = 0
):
    """Linear 1-to-4 on a closed all-quad shell. Nested h-refinement; winding kept."""
    pos = np.asarray(pos, dtype=float)
    edge_node = {}
    new_pos = [pos[i].copy() for i in range(len(pos))]

    def midpoint(a, b):
        e = (a, b) if a < b else (b, a)
        if e not in edge_node:
            edge_node[e] = len(new_pos)
            new_pos.append(0.5 * (pos[a] + pos[b]))
        return edge_node[e]

    new_quads = []
    for q in quads:
        a, b, c, d = (int(i) for i in q)
        ab, bc, cd, da = midpoint(a, b), midpoint(b, c), midpoint(c, d), midpoint(d, a)
        f = len(new_pos)
        new_pos.append(0.25 * (pos[a] + pos[b] + pos[c] + pos[d]))
        new_quads.extend(
            [
                (a, ab, f, da),
                (b, bc, f, ab),
                (c, cd, f, bc),
                (d, da, f, cd),
            ]
        )
    new_pos = np.asarray(new_pos, dtype=float)
    n = len(new_pos)
    gates = MeshQuality.gate_closed_quad_shell(
        n, new_quads, want_euler=want_euler, check_size=check_size
    )
    V = _vol(new_pos, new_quads)
    if V < 0:
        new_quads = _flip_quads(new_quads)
        V = _vol(new_pos, new_quads)
    return new_pos, new_quads, V, gates


def subdivide_mixed_closed(
    pos: np.ndarray, quads, tris, *, check_size: bool = False, want_euler: int | None = None
):
    """Conforming linear subdivide of a closed quad+tri shell → all-quad.

    Quads 1-to-4 (face point + edge mids). Tris 1-to-3 quads (face point + edge
    mids). Every edge is split, so there are no hanging nodes. Same rest
    letter; outline is not Gmsh-remeshed. Used only when unpaired cap/mid
    tris remain after pairing + even-patch eat.
    """
    pos = np.asarray(pos, dtype=float)
    edge_node = {}
    new_pos = [pos[i].copy() for i in range(len(pos))]

    def midpoint(a, b):
        e = (a, b) if a < b else (b, a)
        if e not in edge_node:
            edge_node[e] = len(new_pos)
            new_pos.append(0.5 * (pos[a] + pos[b]))
        return edge_node[e]

    new_quads = []
    for q in quads:
        a, b, c, d = (int(i) for i in q)
        ab, bc, cd, da = midpoint(a, b), midpoint(b, c), midpoint(c, d), midpoint(d, a)
        f = len(new_pos)
        new_pos.append(0.25 * (pos[a] + pos[b] + pos[c] + pos[d]))
        new_quads.extend(
            [
                (a, ab, f, da),
                (b, bc, f, ab),
                (c, cd, f, bc),
                (d, da, f, cd),
            ]
        )
    for t in tris:
        a, b, c = (int(i) for i in t)
        ab, bc, ca = midpoint(a, b), midpoint(b, c), midpoint(c, a)
        f = len(new_pos)
        new_pos.append((pos[a] + pos[b] + pos[c]) / 3.0)
        new_quads.extend(
            [
                (a, ab, f, ca),
                (b, bc, f, ab),
                (c, ca, f, bc),
            ]
        )
    new_pos = np.asarray(new_pos, dtype=float)
    n = len(new_pos)
    gates = MeshQuality.gate_closed_quad_shell(
        n, new_quads, want_euler=want_euler, check_size=check_size
    )
    V = _vol(new_pos, new_quads)
    if V < 0:
        new_quads = _flip_quads(new_quads)
        V = _vol(new_pos, new_quads)
    return new_pos, new_quads, V, gates


def _boundary_edges(faces):
    ecount = defaultdict(int)
    for f in faces:
        n = len(f)
        for k in range(n):
            a, b = int(f[k]), int(f[(k + 1) % n])
            ecount[tuple(sorted((a, b)))] += 1
    return [e for e, c in ecount.items() if c == 1]


def _boundary_cycles(bnd):
    bn = defaultdict(list)
    for a, b in bnd:
        bn[a].append(b)
        bn[b].append(a)
    unused = set(bn)
    loops = []
    while unused:
        start = next(iter(unused))
        loop = [start]
        unused.discard(start)
        prev = None
        cur = start
        while True:
            nxts = [x for x in bn[cur] if x != prev]
            if not nxts:
                break
            nxt = nxts[0]
            if nxt == start:
                break
            if nxt not in unused:
                break
            loop.append(nxt)
            unused.discard(nxt)
            prev, cur = cur, nxt
            if len(loop) > len(bn) + 2:
                break
        loops.append(loop)
    return loops


def _tri_xy_area(pos, a, b, c) -> float:
    p, q, r = pos[a, :2], pos[b, :2], pos[c, :2]
    return 0.5 * ((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]))


def _quad_xy_ok(pos, q, sign: float) -> bool:
    a, b, c, d = q
    a1 = _tri_xy_area(pos, a, b, c)
    a2 = _tri_xy_area(pos, a, c, d)
    if a1 * a2 <= 0:
        return False
    if abs(a1 + a2) < 1e-16:
        return False
    if sign != 0.0 and (a1 + a2) * sign < 0:
        return False
    # reject bowties: the other diagonal split should agree
    b1 = _tri_xy_area(pos, a, b, d)
    b2 = _tri_xy_area(pos, b, c, d)
    if b1 * b2 <= 0:
        return False
    return True


def fill_even_cycle(cycle, pos, sign: float):
    """Fill an even-boundary planar cycle with quads.

    n=4 → one quad. n>4 → one interior Steiner (centroid) and n/2 quads
    from paired fan triangles. Boundary edges stay, so neighbors do not
    pick up hanging nodes. Returns (new_quads, new_xyz or None).
    """
    n = len(cycle)
    if n < 4 or n % 2:
        raise ValueError(f"cycle n={n} cannot be all-quad")
    if n == 4:
        q = tuple(int(i) for i in cycle)
        if not _quad_xy_ok(pos, q, sign):
            q = (q[0], q[3], q[2], q[1])
        if not _quad_xy_ok(pos, q, 0.0):
            raise ValueError("degenerate 4-cycle")
        return [q], None
    xyz = pos[list(cycle)].mean(axis=0)
    quads = []
    for i in range(0, n, 2):
        quads.append(
            (
                int(cycle[i]),
                int(cycle[(i + 1) % n]),
                int(cycle[(i + 2) % n]),
                -1,
            )
        )
    a0 = _tri_xy_area(pos, cycle[0], cycle[1], cycle[2])
    if sign != 0.0 and a0 * sign < 0:
        quads = [(q[0], q[3], q[2], q[1]) for q in quads]
    return quads, xyz


def eat_even_cap_patches(pos: np.ndarray, quads, leftover):
    """Reconnect leftover cap ears + adjacent cap quads when the hole is even.

    Does not remesh walls or the midplane outline. Returns (pos, quads, leftover, info).
    """
    pos = np.asarray(pos, dtype=float).copy()
    quads = [tuple(int(i) for i in q) for q in quads]
    leftover = [tuple(int(i) for i in t) for t in leftover]
    eaten = 0
    n_steiners = 0
    if not leftover:
        return pos, quads, leftover, {"eaten": 0, "steiners": 0}

    def cap_z(t):
        return float(np.mean(pos[list(t), 2]))

    def is_cap_at(ids, z0):
        zs = pos[list(ids), 2]
        return abs(float(zs.max() - zs.min())) < 1e-8 and abs(float(np.mean(zs)) - z0) < 1e-5

    qedges = defaultdict(list)
    for qi, q in enumerate(quads):
        for k in range(4):
            qedges[tuple(sorted((q[k], q[(k + 1) % 4])))].append(qi)
    vert2t = defaultdict(list)
    for ti, t in enumerate(leftover):
        for v in t:
            vert2t[v].append(ti)
    used = set()
    comps = []
    for ti in range(len(leftover)):
        if ti in used:
            continue
        stack = [ti]
        used.add(ti)
        for cur in stack:
            for v in leftover[cur]:
                for j in vert2t[v]:
                    if j not in used:
                        used.add(j)
                        stack.append(j)
        comps.append(stack)

    drop_quads = set()
    drop_tris = set()
    add_quads = []
    for comp in comps:
        if drop_tris & set(comp):
            continue
        tris = [leftover[i] for i in comp]
        z0 = cap_z(tris[0])
        if not all(is_cap_at(t, z0) for t in tris):
            continue
        cap_ids = set()
        for t in tris:
            for k in range(3):
                e = tuple(sorted((t[k], t[(k + 1) % 3])))
                for qi in qedges[e]:
                    if is_cap_at(quads[qi], z0):
                        cap_ids.add(qi)
        if cap_ids & drop_quads:
            continue
        faces = tris + [quads[i] for i in cap_ids]
        bnd = _boundary_edges(faces)
        if len(bnd) < 4 or len(bnd) % 2:
            continue
        loops = _boundary_cycles(bnd)
        if len(loops) != 1 or len(loops[0]) != len(bnd):
            continue
        cycle = loops[0]
        sign = 0.0
        patch_area = 0.0
        for t in tris:
            sign += _tri_xy_area(pos, t[0], t[1], t[2])
            patch_area += abs(_tri_xy_area(pos, t[0], t[1], t[2]))
        for qi in cap_ids:
            q = quads[qi]
            patch_area += abs(
                _tri_xy_area(pos, q[0], q[1], q[2]) + _tri_xy_area(pos, q[0], q[2], q[3])
            )
        try:
            new_q, xyz = fill_even_cycle(cycle, pos, sign)
        except ValueError:
            continue
        tmp_pos = pos
        if xyz is not None:
            tmp_pos = np.vstack([pos, np.asarray(xyz, dtype=float).reshape(1, 3)])
            fid = len(pos)
            trial = [tuple(fid if v == -1 else v for v in q) for q in new_q]
        else:
            trial = new_q
        fill_area = 0.0
        for q in trial:
            fill_area += abs(
                _tri_xy_area(tmp_pos, q[0], q[1], q[2])
                + _tri_xy_area(tmp_pos, q[0], q[2], q[3])
            )
        if patch_area > 0 and abs(fill_area - patch_area) / patch_area > 0.15:
            continue
        if xyz is not None:
            fid = len(pos)
            pos = np.vstack([pos, np.asarray(xyz, dtype=float).reshape(1, 3)])
            new_q = [tuple(fid if v == -1 else v for v in q) for q in new_q]
            n_steiners += 1
        drop_quads |= cap_ids
        drop_tris |= set(comp)
        add_quads.extend(new_q)
        eaten += len(tris)

    quads = [q for i, q in enumerate(quads) if i not in drop_quads] + add_quads
    leftover = [t for i, t in enumerate(leftover) if i not in drop_tris]
    return pos, quads, leftover, {"eaten": eaten, "steiners": n_steiners}


def close_to_all_quad(pos: np.ndarray, quads, leftover, *, want_euler: int | None):
    """Pair leftovers that can become /SHELL without Gmsh midplane remesh.

    Even-patch eat is skipped when it would change Euler characteristic
    (letter B through-holes look like even cap cycles; filling them caps genus).
    Remaining unpaired tris become quads via one conforming mixed 1-to-4.
    """
    pos = np.asarray(pos, dtype=float)
    quads = [tuple(int(i) for i in q) for q in quads]
    leftover = [tuple(int(i) for i in t) for t in leftover]
    euler0 = MeshQuality.counts(len(pos), quads, leftover)["euler"]
    pos_e, quads_e, leftover_e, eat_info = eat_even_cap_patches(pos, quads, leftover)
    euler1 = MeshQuality.counts(len(pos_e), quads_e, leftover_e)["euler"]
    if leftover and eat_info["eaten"] and euler1 != euler0:
        eat_info = {
            "eaten": 0,
            "steiners": 0,
            "skipped": f"even-patch would change euler {euler0}→{euler1}",
        }
        note = (
            f"paired orphans; even-patch skipped (would change euler "
            f"{euler0}→{euler1} — through-holes stay open)"
        )
    else:
        pos, quads, leftover = pos_e, quads_e, leftover_e
        note = (
            f"paired orphans; even-patch ate {eat_info['eaten']} leftover tris"
            f" (+{eat_info['steiners']} cap Steiners)"
        )
    if leftover:
        n_left = len(leftover)
        pos, quads, V, gates = subdivide_mixed_closed(
            pos, quads, leftover, check_size=False, want_euler=want_euler
        )
        note += f"; mixed 1-to-4 of remaining {n_left} unpaired tris (no /SH3N)"
        leftover = []
        return pos, quads, leftover, V, gates, note
    V = _vol(np.asarray(pos, dtype=float), quads)
    if V < 0:
        quads = _flip_quads(quads)
        V = -V
    gates = MeshQuality.gate_closed_quad_shell(
        len(pos), quads, want_euler=want_euler, check_size=False
    )
    return np.asarray(pos, dtype=float), quads, leftover, V, gates, note


def dump_bake(
    path: Path,
    pos: np.ndarray,
    quads,
    *,
    meta: dict,
    check_size: bool = True,
    skip_tris: bool = False,
    letter: str = "A",
    want_euler: int | None = 0,
):
    pos0 = [float(v) for v in np.asarray(pos, dtype=float).ravel()]
    quads = [[int(i) for i in q] for q in quads]
    n = len(pos0) // 3
    if skip_tris:
        vol = float(_vol(np.asarray(pos0, dtype=float).reshape(n, 3), quads))
        if vol < 0:
            quads = [[q[0], q[3], q[2], q[1]] for q in quads]
            vol = -vol
        split: list = []
    else:
        split = BakeJSON.split_tris(quads)
        vol = BakeJSON.volume(pos0, split)
        if vol < 0:
            quads = [[q[0], q[3], q[2], q[1]] for q in quads]
            split = BakeJSON.split_tris(quads)
            vol = -vol
    gates = MeshQuality.gate_closed_quad_shell(
        n, quads, want_euler=want_euler, check_size=check_size
    )
    payload = {
        "pos0": pos0,
        "quads": quads,
        "tris": split,
        "faceTris": [],
        "elemType": "quad",
        "meta": {
            "letter": letter,
            "DEPTH": DEPTH,
            "N": n,
            "nQuads": len(quads),
            "nTris": len(split),
            "nOrphanCapTris": 0,
            "nMidTris": 0,
            "volume_m3": vol,
            "gates": gates,
            **meta,
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, separators=(",", ":")))
    return payload["meta"]


def ship_closed(repo: Path, letter: str = "A"):
    mesh = load_mesh(repo / "meshes" / f"{letter}.json")
    pos = np.asarray(mesh["pos"], dtype=float).reshape(-1, 3)
    quads, leftover = quadify_orphans(mesh["quads"], mesh["orphans"])
    euler0 = MeshQuality.counts(len(pos), quads, leftover)["euler"]
    want_euler = 0 if letter == "A" else euler0
    if letter == "A":
        if leftover:
            raise SystemExit(f"ship still has {len(leftover)} unpaired tris")
        if mesh["n"] != SHIP_N:
            raise SystemExit(f"ship N={mesh['n']} want {SHIP_N}")
        V = enclosed_volume(mesh["pos"], quads, [])
        gates = MeshQuality.gate_closed_quad_shell(len(pos), quads, want_euler=0)
        return pos, quads, V, gates, mesh, "ship meshes/A.json (quadify orphan caps; midplane not remeshed)"
    pos, quads, leftover, V, gates, note = close_to_all_quad(
        pos, quads, leftover, want_euler=want_euler
    )
    if leftover:
        raise SystemExit(f"letter {letter} still has {len(leftover)} unpaired tris")
    return pos, quads, V, gates, mesh, note


def build_coarse(repo: Path, letter: str = "A"):
    pos, quads, _V, _gates, _mesh, _note = ship_closed(repo, letter)
    _front_q, loops, _zmax = extract_front_midplane(pos, quads)
    raw = [[tuple(pos[i, :2]) for i in L] for L in loops]
    last_err = None
    for trial in COARSE_TRIALS:
        dec = [every_k(p, trial["every"]) for p in raw]
        try:
            pos0, mid_q, g2 = gmsh_midplane(dec, trial["lc"])
            epos, equads, eV, egates = extrude_film(pos0, mid_q, nz=trial["nz"])
        except (ValueError, SystemExit) as e:
            last_err = e
            continue
        n = len(epos)
        if not (400 <= n < SHIP_N):
            last_err = ValueError(f"coarse N={n} not in [400, {SHIP_N})")
            continue
        meta = {
            "plan": f"Gmsh DelQuad remesh of ship {letter} outline + prism walls",
            "role": "coarse",
            "lc": trial["lc"],
            "nz": trial["nz"],
            "outlineEvery": trial["every"],
            "outlineCounts": [len(p) for p in dec],
            "nMid": len(pos0) // 3,
            "nMidQuads": len(mid_q),
            "midFreeEdges": g2["freeEdges"],
            "note": f"all-quad /SHELL study mesh; does not replace ship meshes/{letter}.json",
        }
        return epos, equads, eV, egates, meta
    raise SystemExit(f"no all-quad coarse trial worked: {last_err}")


def build_fine(repo: Path, letter: str = "A", want_euler: int | None = 0):
    pos, quads, V0, _gates, _mesh, _note = ship_closed(repo, letter)
    epos, equads, eV, egates = subdivide_closed_quads(
        pos, quads, check_size=(letter == "A"), want_euler=want_euler
    )
    meta = {
        "plan": "linear 1-to-4 of closed all-quad ship shell (nested 2× h; N×4 on a surface)",
        "role": "fine",
        "parentN": int(len(pos)),
        "parentV0_m3": V0,
        "note": f"all-quad /SHELL study mesh; does not replace ship meshes/{letter}.json",
    }
    return epos, equads, eV, egates, meta


def load_closed_bake(path: Path):
    data = json.loads(path.read_text())
    pos = np.asarray(data["pos0"], dtype=float).reshape(-1, 3)
    quads = [tuple(int(i) for i in q) for q in data["quads"]]
    V = float((data.get("meta") or {}).get("volume_m3") or _vol(pos, quads))
    return pos, quads, V, data.get("meta") or {}


def build_finer_from_fine(
    pos: np.ndarray, quads, V0: float, *, letter: str = "A", want_euler: int | None = 0
):
    """Nested 1-to-4 of the fine all-quad shell (N×4 vs fine; 16× ship quads)."""
    epos, equads, eV, egates = subdivide_closed_quads(
        pos, quads, check_size=False, want_euler=want_euler
    )
    meta = {
        "plan": "linear 1-to-4 of closed all-quad fine shell (nested 2× h of fine; N=4×fine)",
        "role": "finer",
        "parentN": int(len(pos)),
        "parentV0_m3": float(V0),
        "note": f"all-quad /SHELL study mesh; exceeds web bake MAX_VERTS; does not replace ship meshes/{letter}.json",
    }
    return epos, equads, eV, egates, meta


def build_finest_from_finer(
    pos: np.ndarray, quads, V0: float, *, letter: str = "A", want_euler: int | None = 0
):
    """Nested 1-to-4 of the finer all-quad shell (N=4×finer; same rest letter)."""
    epos, equads, eV, egates = subdivide_closed_quads(
        pos, quads, check_size=False, want_euler=want_euler
    )
    meta = {
        "plan": "linear 1-to-4 of closed all-quad finer shell (nested 2× h of finer; N=4×finer)",
        "role": "finest",
        "parentN": int(len(pos)),
        "parentV0_m3": float(V0),
        "note": "all-quad /SHELL study mesh; same rest letter as ship/fine/finer; not Gmsh coarse",
    }
    return epos, equads, eV, egates, meta


def generate(
    repo: Path,
    out_dir: Path,
    *,
    letter: str = "A",
    finer_only: bool = False,
    include_finer: bool = False,
    finest_only: bool = False,
    include_finest: bool = False,
    include_coarse: bool | None = None,
) -> dict:
    letter = letter.upper()
    if letter not in ("A", "B", "C"):
        raise SystemExit(f"letter must be A, B, or C, got {letter}")
    want_euler: int | None = 0 if letter == "A" else None  # B/C: ship_closed sets bake euler
    if include_coarse is None:
        include_coarse = letter == "A"
    if letter in ("B", "C"):
        include_finest = False
        finest_only = False
        if not finer_only:
            include_finer = True
    mesh_dir = out_dir / "meshes"
    mesh_dir.mkdir(parents=True, exist_ok=True)
    summary_path = out_dir / "mesh-summary.json"
    summary = json.loads(summary_path.read_text()) if summary_path.exists() else {}
    summary["letter"] = letter
    dump_kw = {"letter": letter, "want_euler": want_euler}

    if not finer_only and not finest_only:
        if include_coarse:
            cpos, cquads, cV, _cg, cmeta = build_coarse(repo, letter)
            cmeta_out = dump_bake(
                mesh_dir / f"{letter}-coarse.json", cpos, cquads, meta=cmeta, **dump_kw
            )
            summary["coarse"] = {**cmeta_out, "V0_mL": cV * 1e6}

        pos, quads, sV, sg, smesh, snote = ship_closed(repo, letter)
        if want_euler is None:
            want_euler = int(sg["euler"])
            dump_kw["want_euler"] = want_euler
        smeta = {
            "plan": (
                f"ship meshes/{letter}.json (quadify orphan caps; midplane not remeshed)"
                if letter == "A"
                else f"ship meshes/{letter}.json — {snote}"
            ),
            "role": "ship",
            "source": f"meshes/{letter}.json",
            "nQuads_src": len(smesh["quads"]),
            "nOrphanCapTris": len(smesh["orphans"]),
            "close": snote,
            "note": f"locked Design-PASS bake; do not overwrite meshes/{letter}.json",
        }
        smeta_out = dump_bake(
            mesh_dir / f"{letter}-ship.json", pos, quads, meta=smeta, **dump_kw
        )

        fpos, fquads, fV, _fg, fmeta = build_fine(repo, letter, want_euler=want_euler)
        skip_fine_tris = len(fpos) > MeshQuality.MAX_VERTS
        fmeta_out = dump_bake(
            mesh_dir / f"{letter}-fine.json",
            fpos,
            fquads,
            meta=fmeta,
            check_size=False,
            skip_tris=skip_fine_tris,
            **dump_kw,
        )

        summary.update({
            "ship": {**smeta_out, "V0_mL": sV * 1e6},
            "fine": {**fmeta_out, "V0_mL": fV * 1e6},
        })

    if (include_finer or finer_only) and not finest_only:
        fine_path = mesh_dir / f"{letter}-fine.json"
        if not fine_path.exists():
            raise SystemExit(f"{letter}-fine.json missing — run without --finer-only first")
        fpos, fquads, fV, _fmeta = load_closed_bake(fine_path)
        xpos, xquads, xV, _xg, xmeta = build_finer_from_fine(
            fpos, fquads, fV, letter=letter, want_euler=want_euler
        )
        xmeta_out = dump_bake(
            mesh_dir / f"{letter}-finer.json",
            xpos,
            xquads,
            meta=xmeta,
            check_size=False,
            skip_tris=True,
            **dump_kw,
        )
        summary["finer"] = {**xmeta_out, "V0_mL": xV * 1e6}

    if include_finest or finest_only:
        finer_path = mesh_dir / f"{letter}-finer.json"
        if not finer_path.exists():
            raise SystemExit(f"{letter}-finer.json missing — run --finer-only first")
        xpos, xquads, xV, _xmeta = load_closed_bake(finer_path)
        zpos, zquads, zV, _zg, zmeta = build_finest_from_finer(
            xpos, xquads, xV, letter=letter, want_euler=want_euler
        )
        zmeta_out = dump_bake(
            mesh_dir / f"{letter}-finest.json",
            zpos,
            zquads,
            meta=zmeta,
            check_size=False,
            skip_tris=True,
            **dump_kw,
        )
        summary["finest"] = {**zmeta_out, "V0_mL": zV * 1e6}

    summary["law"] = (
        "LAW42 μ1=MU α1=2 ρ=1130 H0 Gapmin=CONTACT_KISS Ishell=1 /ADYREL — not retuned"
    )
    summary["metrics"] = (
        "Mike 2026-09-12 same-load: at ~32.5 kPa and ~35.8 kPa report N, λ_max, λ_aw, V, Ψ; "
        "ΔV≤5% Δλ_max≤2% Δλ_aw≤2% on successive nested N; peak λ_max at holes/creases is a "
        "sharp-hole singularity — do not chase with global refine. Volume/λ_aw is the signal. "
        "Ψ≥0; contact report-only; dynamic until QS-ish; converged dynamic ≠ ABC apples"
    )
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    for key in ("coarse", "ship", "fine", "finer", "finest"):
        if key in summary and isinstance(summary[key], dict) and "N" in summary[key]:
            print("{k:6s} N={N} quads={nQuads} V0={V0_mL:.4g} mL".format(k=key, **summary[key]))
    if include_coarse:
        ns = [summary[k]["N"] for k in ("coarse", "ship", "fine") if k in summary]
        if len(ns) == 3 and not (ns[0] < ns[1] < ns[2]):
            raise SystemExit("densities are not coarse < ship < fine")
    else:
        ns = [summary[k]["N"] for k in ("ship", "fine") if k in summary]
        if len(ns) == 2 and not (ns[0] < ns[1]):
            raise SystemExit("densities are not ship < fine")
    if "finer" in summary and "fine" in summary:
        if not (summary["fine"]["N"] < summary["finer"]["N"]):
            raise SystemExit("finer is not denser than fine")
    if "finest" in summary and "finer" in summary:
        if not (summary["finer"]["N"] < summary["finest"]["N"]):
            raise SystemExit("finest is not denser than finer")
    return summary


def main(argv=None) -> int:
    repo = _TOOLS.parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--letter", choices=("A", "B", "C"), default="A")
    ap.add_argument("--out-dir", type=Path, default=None)
    ap.add_argument(
        "--finer-only",
        action="store_true",
        help="1-to-4 of existing {L}-fine.json only; do not remesh ship/fine",
    )
    ap.add_argument(
        "--with-finer",
        action="store_true",
        help="also write nested finer (N=4×fine) after the ship/fine ladder",
    )
    ap.add_argument(
        "--finest-only",
        action="store_true",
        help="1-to-4 of existing {L}-finer.json only; letter A only (B/C do not run finest)",
    )
    args = ap.parse_args(argv)
    out_dir = args.out_dir or (repo / "radioss" / f"{args.letter}-refine")
    generate(
        repo,
        out_dir,
        letter=args.letter,
        finer_only=args.finer_only,
        include_finer=args.with_finer or args.finer_only,
        finest_only=args.finest_only,
        include_finest=args.finest_only,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
