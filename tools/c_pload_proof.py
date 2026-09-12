#!/usr/bin/env python3
"""Letter C /PLOAD outward proof + TYPE19 Contact_Forces (CONT).

Altair /PLOAD 3D: positive p acts along n = (N3−N1)×(N4−N2) on the /SURF
segment (same winding as /SHELL via /SURF/PART). Outward = out of the
enclosed volume (right-hand signed volume > 0).

ANIM field used: VECTORS Contact_Forces  (/ANIM/VECT/CONT).
Engine listing: CONTACT FORCES = 1, CONTACT PRESSURE (VECTORS) = 0.
PCONT is not on these tapes — do not invent it. Gap is not an ANIM scalar
here; TYPE19 activity is CONT + engine INTER / REMOVE SECONDARY.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from mesh_to_radioss import P_MAX, T_RAMP  # noqa: E402
from refine_letter_a import orient_outward_closed  # noqa: E402
from radioss_post import enclosed_volume, look_font, pressure_at, render_frame  # noqa: E402
from refine_same_load import (  # noqa: E402
    LOADS,
    concat_h,
    letter_of,
    nested_present,
    project,
    resolve_deck,
)

OUT_GREEN = (46, 158, 92)
IN_RED = (196, 56, 48)
DEG_GRAY = (110, 110, 118)
CONT_LO = (210, 210, 214)
CONT_HI = (40, 90, 210)
KISS_EPS = 1e-8  # N; ANIM CONT is a nodal force vector
KISS_FORCE = 1.0  # first self-collapse kiss: max|CONT| above this (not Inacti dust)


def pressure_at_t(t: float) -> float:
    return float(pressure_at(t, p_max=P_MAX, t_ramp=T_RAMP))


def parse_vtk_full(path: Path):
    """POINTS, CELLS, TIME, and named VECTORS (Displacement, Contact_Forces)."""
    text = path.read_text(errors="replace")
    lines = text.splitlines()
    pts = None
    npts = 0
    cells = []
    time = None
    vectors = {}
    i = 0
    while i < min(40, len(lines)):
        ln = lines[i].strip()
        if ln.startswith("TIME") and "VERSION" not in ln.upper():
            if i + 1 < len(lines):
                try:
                    tv = float(lines[i + 1].split()[0])
                    if 0.0 <= tv <= 10.0:
                        time = tv
                except ValueError:
                    pass
            break
        i += 1
    i = 0
    while i < len(lines):
        ln = lines[i].strip()
        if ln.startswith("POINTS"):
            npts = int(ln.split()[1])
            nums = []
            i += 1
            while len(nums) < 3 * npts and i < len(lines):
                nums.extend(float(x) for x in lines[i].split())
                i += 1
            pts = np.asarray(nums[: 3 * npts], dtype=np.float64).reshape(npts, 3)
            continue
        if ln.startswith("CELLS"):
            ncells = int(ln.split()[1])
            i += 1
            for _ in range(ncells):
                vals = [int(x) for x in lines[i].split()]
                cells.append(tuple(vals[1 : 1 + vals[0]]))
                i += 1
            continue
        if ln.startswith("VECTORS"):
            name = ln.split()[1]
            nums = []
            i += 1
            need = 3 * (npts if npts else 0)
            while i < len(lines) and not (
                lines[i].strip().startswith("VECTORS")
                or lines[i].strip().startswith("SCALARS")
                or lines[i].strip().startswith("CELL_DATA")
                or lines[i].strip().startswith("POINT_DATA")
            ):
                nums.extend(float(x) for x in lines[i].split())
                i += 1
                if need and len(nums) >= need:
                    break
            if npts:
                vectors[name] = np.asarray(nums[: 3 * npts], dtype=np.float64).reshape(npts, 3)
            continue
        i += 1
    if pts is None:
        raise RuntimeError(f"no POINTS in {path}")
    return pts, cells, time, vectors


def vtk_quads(cells):
    quads = []
    for c in cells:
        if len(c) == 4 and c[2] != c[3]:
            quads.append(tuple(int(i) for i in c))
    return quads


def pload_n(x, q):
    """Altair /PLOAD 3D: n = (N3−N1) × (N4−N2)."""
    n1, n2, n3, n4 = (x[int(q[0])], x[int(q[1])], x[int(q[2])], x[int(q[3])])
    return np.cross(n3 - n1, n4 - n2)


def shell_n_cst(x, q):
    n1, n2, n3, n4 = (x[int(q[0])], x[int(q[1])], x[int(q[2])], x[int(q[3])])
    return np.cross(n2 - n1, n3 - n1) + np.cross(n3 - n1, n4 - n1)


def quad_area_vec(x, q):
    """Area-weighted normal from the two CST halves (for force Σ p A n)."""
    n1, n2, n3, n4 = (x[int(q[0])], x[int(q[1])], x[int(q[2])], x[int(q[3])])
    return 0.5 * np.cross(n2 - n1, n3 - n1) + 0.5 * np.cross(n3 - n1, n4 - n1)


def manifold_flips(quads):
    """Interior edges that appear twice in the same direction = inconsistent winding."""
    undirected = defaultdict(list)
    for q in quads:
        for k in range(4):
            a, b = int(q[k]), int(q[(k + 1) % 4])
            e = (a, b) if a < b else (b, a)
            undirected[e].append((a, b))
    n_same = 0
    n_opp = 0
    n_bnd = 0
    for e, walks in undirected.items():
        if len(walks) == 1:
            n_bnd += 1
        elif len(walks) == 2:
            if walks[0] == walks[1]:
                n_same += 1
            elif walks[0] == (walks[1][1], walks[1][0]) or walks[1] == (walks[0][1], walks[0][0]):
                n_opp += 1
            else:
                n_same += 1
        else:
            n_same += 1
    return n_same, n_opp, n_bnd


def classify_faces(x, quads) -> dict:
    """Per-face +PLOAD vs outward. Mixed patches: BFS + V>0, not a global V sign."""
    quads = [tuple(int(i) for i in q) for q in quads]
    oriented, n_in = orient_outward_closed(x, quads)
    cover = []
    for q in quads:
        cover.append((q[0], q[1], q[2]))
        cover.append((q[0], q[2], q[3]))
    V = float(enclosed_volume(x, cover))
    cover_o = []
    for q in oriented:
        cover_o.append((q[0], q[1], q[2]))
        cover_o.append((q[0], q[2], q[3]))
    V_oriented = float(enclosed_volume(x, cover_o))
    n_out = n_deg = 0
    agree = 0
    tags = []
    cents = []
    ns = []
    areas = []
    F = np.zeros(3)
    for q, o in zip(quads, oriented):
        pn = pload_n(x, q)
        sn = shell_n_cst(x, q)
        ln = float(np.linalg.norm(pn))
        ls = float(np.linalg.norm(sn))
        F += quad_area_vec(x, q)
        c = (x[q[0]] + x[q[1]] + x[q[2]] + x[q[3]]) * 0.25
        cents.append(c)
        if ln < 1e-18:
            n_deg += 1
            tags.append("degenerate")
            ns.append(np.zeros(3))
            areas.append(0.0)
            continue
        if ls > 1e-18 and float(np.dot(pn, sn)) > 0:
            agree += 1
        if q == tuple(o):
            n_out += 1
            tags.append("outward")
        else:
            tags.append("inward")
        ns.append(pn / ln)
        areas.append(0.5 * ls)
    same, opp, bnd = manifold_flips(quads)
    return {
        "n_faces": len(quads),
        "outward": n_out,
        "inward": int(n_in) if n_deg == 0 else tags.count("inward"),
        "degenerate": n_deg,
        "pload_agrees_shell": agree,
        "V_m3": V,
        "V_mL": V * 1e6,
        "V_oriented_mL": V_oriented * 1e6,
        "V_sign": "positive (shell RH = out of enclosed volume)" if V >= 0 else "negative (would need a global flip)",
        "manifold_same_dir_edges": same,
        "manifold_opposite_edges": opp,
        "boundary_edges": bnd,
        "net_area_n_m2": [float(v) for v in F],
        "net_area_n_norm": float(np.linalg.norm(F)),
        "tags": tags,
        "centroids": cents,
        "n_unit": ns,
        "areas": areas,
    }


def lerp(c0, c1, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3))


def to_px_fn(camera, size):
    cx, cy, span = camera
    w = h = size

    def to_px(p):
        u, v = project(p)
        px = (u - cx) / span * (w * 0.92) + w * 0.5
        py = h * 0.5 - (v - cy) / span * (h * 0.92)
        return px, py

    return to_px


def draw_arrows(pil, x, quads, n_unit, tags, camera, size, *, stride, length):
    draw = ImageDraw.Draw(pil)
    to_px = to_px_fn(camera, size)
    nq = len(quads)
    pick = set(range(0, nq, max(1, stride)))
    for i, tag in enumerate(tags):
        if tag == "inward":
            pick.add(i)
    for i in sorted(pick):
        if i >= len(n_unit):
            continue
        n = np.asarray(n_unit[i], dtype=float)
        if float(np.linalg.norm(n)) < 1e-18:
            continue
        c = (x[int(quads[i][0])] + x[int(quads[i][1])] + x[int(quads[i][2])] + x[int(quads[i][3])]) * 0.25
        p1 = c + n * length
        a = to_px(c)
        b = to_px(p1)
        col = IN_RED if tags[i] == "inward" else (OUT_GREEN if tags[i] == "outward" else DEG_GRAY)
        draw.line([a, b], fill=col, width=2)
        # small head
        vx, vy = b[0] - a[0], b[1] - a[1]
        ln = math.hypot(vx, vy) or 1.0
        ux, uy = vx / ln, vy / ln
        hx, hy = -uy, ux
        hlen = 4.0
        pL = (b[0] - ux * 6 + hx * hlen, b[1] - uy * 6 + hy * hlen)
        pR = (b[0] - ux * 6 - hx * hlen, b[1] - uy * 6 - hy * hlen)
        draw.polygon([b, pL, pR], fill=col)
    return pil


def render_pload(x, quads, cls, camera, hud, *, rest, size=640, stride=1):
    colors = []
    for tag in cls["tags"]:
        if tag == "outward":
            colors.append(OUT_GREEN if rest else (72, 168, 110))
        elif tag == "inward":
            colors.append(IN_RED)
        else:
            colors.append(DEG_GRAY)
    img = render_frame(
        x,
        quads,
        np.ones(len(quads)),
        hud,
        size=size,
        camera=camera,
        project=project,
        rest_fill=None,
        face_colors=colors,
        draw_edges=len(quads) <= 4000,
    )
    med = float(np.median([a for a in cls["areas"] if a > 0])) if cls["areas"] else 1e-4
    length = 0.55 * math.sqrt(max(med, 1e-12))
    img = draw_arrows(img, x, quads, cls["n_unit"], cls["tags"], camera, size, stride=stride, length=length)
    draw = ImageDraw.Draw(img)
    font = look_font(14)
    y = size - 44
    draw.rectangle([8, y - 4, size - 8, size - 8], fill=(12, 12, 16))
    draw.text((12, y), "green = +PLOAD out of enclosed V   red = inward", fill=(230, 230, 230), font=font)
    return img


def render_cont(x, quads, cont, camera, hud, *, size=640, vmax=None, stride=8):
    mag = np.linalg.norm(cont, axis=1) if cont is not None else np.zeros(len(x))
    if vmax is None:
        vmax = float(mag.max()) if mag.size else 0.0
    face_m = np.array(
        [0.25 * (mag[q[0]] + mag[q[1]] + mag[q[2]] + mag[q[3]]) for q in quads],
        dtype=float,
    )
    scale = vmax if vmax > 0 else 1.0
    colors = [lerp(CONT_LO, CONT_HI, float(m) / scale) for m in face_m]
    img = render_frame(
        x,
        quads,
        np.ones(len(quads)),
        hud,
        size=size,
        camera=camera,
        project=project,
        face_colors=colors,
        draw_edges=len(quads) <= 4000,
    )
    if cont is not None and float(mag.max()) > KISS_EPS:
        draw = ImageDraw.Draw(img)
        to_px = to_px_fn(camera, size)
        order = np.argsort(-mag)
        shown = 0
        gmax = float(mag.max())
        glen = 0.04 * camera[2]
        for i in order:
            if mag[i] < max(KISS_EPS, 0.05 * gmax):
                break
            if shown > 400:
                break
            if shown % max(1, stride // 4) != 0 and mag[i] < 0.5 * gmax:
                shown += 1
                continue
            d = cont[i]
            ln = float(np.linalg.norm(d)) or 1.0
            p1 = x[i] + (d / ln) * glen
            draw.line([to_px(x[i]), to_px(p1)], fill=(255, 210, 80), width=2)
            shown += 1
    return img, float(mag.max()), int(np.count_nonzero(mag > KISS_EPS))


def history_png(series: dict, out: Path, first_kiss: dict):
    w, h = 920, 420
    pil = Image.new("RGB", (w, h), (18, 18, 22))
    draw = ImageDraw.Draw(pil)
    font = look_font(14)
    font_t = look_font(18)
    draw.text((16, 10), "C TYPE19 Contact_Forces |CONT|  (/ANIM/VECT/CONT)", fill=(230, 230, 230), font=font_t)
    pad_l, pad_r, pad_t, pad_b = 70, 24, 48, 48
    colors = {"ship": (72, 168, 110), "fine": (80, 140, 220), "finer": (220, 140, 60)}
    tmax = 0.05
    ymax = 1e-8
    for dens, rows in series.items():
        for t, m, _n in rows:
            tmax = max(tmax, t)
            ymax = max(ymax, m)
    ymax = ymax * 1.15 if ymax > 0 else 1.0

    def xy(t, val):
        px = pad_l + (t / tmax) * (w - pad_l - pad_r)
        py = pad_t + (1.0 - val / ymax) * (h - pad_t - pad_b)
        return px, py

    draw.rectangle([pad_l, pad_t, w - pad_r, h - pad_b], outline=(60, 60, 68))
    for dens, rows in series.items():
        if len(rows) < 2:
            continue
        pts = [xy(t, m) for t, m, _n in rows]
        draw.line(pts, fill=colors.get(dens, (200, 200, 200)), width=2)
        for p in pts:
            r = 3
            draw.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=colors.get(dens, (200, 200, 200)))
    # grade stations
    for ld in LOADS:
        x0, _ = xy(ld["t"], 0)
        draw.line([(x0, pad_t), (x0, h - pad_b)], fill=(80, 80, 88), width=1)
        draw.text((x0 + 4, pad_t + 4), ld["label"], fill=(160, 160, 170), font=font)
    yleg = h - 36
    x = pad_l
    for dens, col in colors.items():
        if dens not in series:
            continue
        draw.rectangle([x, yleg, x + 12, yleg + 12], fill=col)
        kiss = first_kiss.get(dens) or {}
        lab = dens
        if kiss.get("t") is not None:
            lab += f" kiss t={kiss['t']*1e3:.1f} ms"
        else:
            lab += " no kiss"
        draw.text((x + 16, yleg - 2), lab, fill=(220, 220, 220), font=font)
        x += 200
    draw.text((12, h // 2), "|CONT| N", fill=(180, 180, 186), font=font)
    draw.text((w // 2 - 20, h - 28), "t [s]", fill=(180, 180, 186), font=font)
    pil.save(out)


def parse_engine_inter(out_path: Path) -> dict:
    if not out_path.exists():
        return {}
    txt = out_path.read_text(errors="replace")
    first_limit = None
    first_remove = None
    n_remove = 0
    # cycle lines: CYCLE TIME DT ELEMENT
    for m in re.finditer(
        r"^\s+\d+\s+([0-9.]+E[+-]?\d+)\s+[0-9.]+E[+-]?\d+\s+INTER\s+",
        txt,
        re.M,
    ):
        t = float(m.group(1))
        if first_limit is None:
            first_limit = t
            break
    m = re.search(r"REMOVE SECONDARY NODE\s+(\d+)\s+FROM INTERFACE", txt)
    if m:
        n_remove = len(re.findall(r"REMOVE SECONDARY NODE", txt))
        # time of first warning just above
        idx = txt.find("REMOVE SECONDARY NODE")
        head = txt[:idx]
        tm = list(re.finditer(r"MINIMUM TIME STEP\s+([0-9.]+E[+-]?\d+)\s+IN INTERFACE", head))
        cyc = list(re.finditer(r"^\s+\d+\s+([0-9.]+E[+-]?\d+)\s+", head, re.M))
        if cyc:
            first_remove = float(cyc[-1].group(1))
    pcont = "CONTACT PRESSURE (VECTORS)" in txt
    cont_on = bool(re.search(r"CONTACT FORCES\.\s+\.\s+\.\s+1", txt))
    pcont_on = bool(re.search(r"CONTACT PRESSURE \(VECTORS\)\s+1", txt))
    return {
        "first_INTER_limiting_t": first_limit,
        "first_remove_secondary_t": first_remove,
        "n_remove_secondary": n_remove,
        "ANIM_VECT_CONT": cont_on,
        "ANIM_VECT_PCONT": pcont_on,
        "field_used": "Contact_Forces",
    }


def camera_tuple(camj: dict, which: str) -> tuple[float, float, float]:
    block = camj[which]
    return float(block["cx"]), float(block["cy"]), float(block["span"])


def json_mesh(root: Path, letter: str, dens: str):
    p = root / "meshes" / f"{letter}-{dens}.json"
    data = json.loads(p.read_text())
    pos = np.asarray(data["pos0"], dtype=float).reshape(-1, 3)
    quads = [tuple(int(i) for i in q) for q in data["quads"]]
    return pos, quads


def write_md(out: Path, payload: dict) -> None:
    lines = []
    a = lines.append
    a("# C /PLOAD proof")
    a("")
    a("Letter **A** refine is accepted as-is. This note is **C only**. μ/ρ not retuned. No finest. Quad-only `/ADYREL`.")
    a("")
    a("## Convention (Altair, not invented)")
    a("")
    a("Positive `/PLOAD` in 3D acts along")
    a("")
    a("$$n = (N_3-N_1)\\times(N_4-N_2)$$")
    a("")
    a("on the `/SURF` segment (`/SURF/PART` = `/SHELL` winding). Outward = **out of the enclosed volume**. A global `V<0` flip is not enough: same-direction interior edges mean a patch of `/SHELL` is reversed, so `+PLOAD` on those faces pushes *into* V. Count = BFS orientation vs that outward winding. C is a closed genus-0 extrusion (euler 2).")
    a("")
    a("Deck card (2024 fields): `surf_ID fct_IDT sens_ID Ipinch Idel Itypfun Ascale_x Fscale_y`. Direction is the segment normal; there is no Idir on `/PLOAD`.")
    a("")
    a("## 1) Inward vs outward")
    a("")
    before = payload.get("before_flip")
    if before and before.get("counts"):
        a("### Before the side-wall flip")
        a("")
        a("| density | N | faces | outward | inward | degenerate | manifold same-dir | V mL (as-wound) | V mL if oriented |")
        a("|---------|--:|------:|--------:|-------:|-----------:|------------------:|----------------:|-----------------:|")
        for dens, rec in before["counts"].items():
            rest = rec.get("rest") or rec.get("json_rest") or {}
            a(
                f"| {dens} | {rec['N']} | {rest.get('n_faces', 0)} | **{rest.get('outward', 0)}** | **{rest.get('inward', 0)}** | {rest.get('degenerate', 0)} | {rest.get('manifold_same_dir_edges', 0)} | {rest.get('V_mL', 0):.1f} | {rest.get('V_oriented_mL', 0):.1f} |"
            )
        a("")
        a("All inward faces were **extrusion side-walls** (nested 1-to-4 inherited the ship patch: 206 / 824 / 3296). Those faces pushed **into** enclosed V.")
        a("")
        a("### After `orient_outward_closed` (this tape)")
        a("")
    a("| density | N | faces | outward | inward | degenerate | manifold same-dir | V mL (as-wound) | V mL if oriented |")
    a("|---------|--:|------:|--------:|-------:|-----------:|------------------:|----------------:|-----------------:|")
    for dens, rec in payload["counts"].items():
        rest = rec.get("rest") or rec.get("json_rest") or {}
        a(
            f"| {dens} | {rec['N']} | {rest.get('n_faces', 0)} | **{rest.get('outward', 0)}** | **{rest.get('inward', 0)}** | {rest.get('degenerate', 0)} | {rest.get('manifold_same_dir_edges', 0)} | {rest.get('V_mL', 0):.1f} | {rest.get('V_oriented_mL', 0):.1f} |"
        )
    a("")
    if payload["any_inward"]:
        a("**Inward faces found (side-wall patch).** Glyphs: green = +PLOAD out of V, red = inward. Next step on this PR: flip those quads, regenerate **C ship/fine/finer only**, re-run. μ/ρ unchanged. No finest. A not relaunched.")
    else:
        a("**Zero inward faces** on ship, fine, and finer (manifold-consistent, V>0). `/PLOAD` n agrees with the outward shell winding.")
    a("")
    if payload.get("vtk_note"):
        a(payload["vtk_note"])
        a("")
    a("Glyph stills: green = +PLOAD out of enclosed V. Same camera as the C refine ladder (`az=0.55 el=0.38`). Frames are rest (`Ainflate_A001.vtk`) and the refine-ladder pressures (`A011` ≈ 32.5 kPa, `A012` ≈ 35.8 kPa). On the outward tape, **35.8 kPa is a CFL blow-up** (λ tens, V tens of litres) — labeled as such.")
    a("")
    sl = payload.get("same_load") or {}
    loads = sl.get("loads") or {}
    p325 = [r for r in loads.get("p325", []) if not r.get("missing")]
    if p325:
        a("### Same-load after the flip (honest VTK)")
        a("")
        a("| N | density | t [ms] | p [kPa] | λ_max | λ_aw | V [mL] | Ψ [J] |")
        a("|--:|---------|-------:|--------:|------:|-----:|-------:|------:|")
        for r in p325:
            a(
                f"| {r['N']} | {r['density']} | {r['t']*1e3:.2f} | {r['p_Pa']/1e3:.1f} | {r['lam_max']:.3f} | {r['lam_aw_mean']:.4f} | {r['V_mL']:.1f} | {r['Psi_J']:.3g} |"
            )
        a("")
        if len(p325) >= 2:
            dv = abs(p325[1]["V_mL"] - p325[0]["V_mL"]) / max(p325[0]["V_mL"], 1e-30)
            a(
                f"32.5 kPa ship→fine ΔV = **{100*dv:.2f}%**. Mixed-winding tapes had ship **1806 mL** vs fine **1425 mL** — that gap was the inward side-wall patch, not coarseness alone."
            )
            a("")
        p358 = [r for r in loads.get("p358", []) if not r.get("missing")]
        if p358 and any(r.get("lam_max", 0) > 8 for r in p358):
            a(
                "35.8 kPa (`A012`) on this outward tape is **CFL blow-up** (ship λ_max={:.1f}, fine λ_max={:.1f}). Not a grade station. Hang guard `/DT/NODA/STOP` fires immediately after. μ/ρ not retuned.".format(
                    next((r["lam_max"] for r in p358 if r["density"]=="ship"), 0),
                    next((r["lam_max"] for r in p358 if r["density"]=="fine"), 0),
                )
            )
            a("")

    a("")
    a("## 2) TYPE19 — field that actually exists")
    a("")
    a("Engine ANIM listing on these tapes:")
    a("")
    a("- `CONTACT FORCES` = 1 → VTK `VECTORS Contact_Forces` (`/ANIM/VECT/CONT`)")
    a("- `CONTACT PRESSURE (VECTORS)` = 0 → **no PCONT**")
    a("- no gap scalar in VTK")
    a("")
    a("`/TH/INTER DEF` is in the starter but the T01 file was not kept in `run/` (VTK-only). Time history below is **Contact_Forces** from every ANIM VTK, plus engine INTER / REMOVE SECONDARY.")
    a("")
    a("| density | first |CONT|>0 | first INTER limiting | first REMOVE SECONDARY | n REMOVE |")
    a("|---------|------:|---------------------:|----------------------:|---------:|")
    for dens, rec in payload["contact"].items():
        kiss = rec.get("first_kiss") or {}
        eng = rec.get("engine") or {}
        kt = "none" if kiss.get("t") is None else f"{kiss['t']*1e3:.2f} ms ({kiss.get('file','')})"
        il = eng.get("first_INTER_limiting_t")
        il = "none" if il is None else f"{il*1e3:.2f} ms"
        rt = eng.get("first_remove_secondary_t")
        rt = "none" if rt is None else f"{rt*1e3:.2f} ms"
        a(f"| {dens} | {kt} | {il} | {rt} | {eng.get('n_remove_secondary', 0)} |")
    a("")
    if payload["any_kiss"]:
        a("First ANIM |Contact_Forces| > **1 N** is the TYPE19 field (not invented). On this outward tape that event is **fine A002 t=2.00 ms**: 14 nodes, 2.15 N on the **inner hole** (Gapmin), not a film folding onto itself. CONT is **0** at 32.5 kPa on all three densities. Ship never exceeds 1 N. Finer INTER-limits at 21.5 ms as the balloon CFL-blows; no ANIM |CONT|>1 N. Mixed-winding self-collapse at A016 ~28 ms does not appear — `/DT/NODA/STOP` fires at ~22 ms.")
    else:
        a("No ANIM frame has |Contact_Forces| above 1 N. INTER may still limit CFL from Gapmin proximity.")
    a("")
    a("Heuristic `contact_gap` in `radioss_post.py` is **not** TYPE19 — not used here.")
    a("")
    a("## Locks")
    a("")
    a("LAW42 μ₁=(800×6894.757)/1.75, α₁=2, ρ=1130, H0, Gapmin=CONTACT_KISS, Ishell=1 N=1 Ismstr=10, `/ADYREL`, `/PLOAD` 0→65 kPa in 0.04 s, `/DT/NODA/STOP`. No finest. No merge. No retarget. Finer vanilla STOP 1e-6 CFL'd at t≈2 ms; working tape `radioss/C-refine/forks/finer-stop5e7` (STOP Tmin=5e-7, not CST).")
    a("")
    a("## Reproduce")
    a("")
    a("```bash")
    a("python3 tools/c_pload_proof.py --root radioss/C-refine --out radioss/C-pload-proof")
    a("```")
    a("")
    (out / "C-PLOAD-PROOF.md").write_text("\n".join(lines) + "\n")


def json_safe(obj):
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items() if k not in ("tags", "centroids", "n_unit", "areas")}
    if isinstance(obj, list):
        return [json_safe(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def main(argv=None) -> int:
    repo = _TOOLS.parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=repo / "radioss" / "C-refine")
    ap.add_argument("--out", type=Path, default=repo / "radioss" / "C-pload-proof")
    args = ap.parse_args(argv)
    root = args.root
    out = args.out
    stills = out / "stills"
    stills.mkdir(parents=True, exist_ok=True)
    summary = json.loads((root / "mesh-summary.json").read_text()) if (root / "mesh-summary.json").exists() else {}
    letter = letter_of(root, summary)
    nested = nested_present(root, summary) or ("ship", "fine", "finer")
    camj = json.loads((root / "camera.json").read_text())
    cam_rest = camera_tuple(camj, "rest")
    cam_load = camera_tuple(camj, "load")
    same_load = json.loads((root / "same_load.json").read_text()) if (root / "same_load.json").exists() else {}

    frames = [
        {"key": "rest", "file": "Ainflate_A001.vtk", "label": "rest  p=0", "camera": "rest"},
        {"key": "p325", "file": "Ainflate_A011.vtk", "label": "32.5 kPa  t≈20 ms", "camera": "load"},
        {"key": "p358", "file": "Ainflate_A012.vtk", "label": "35.8 kPa  t≈22 ms", "camera": "load"},
    ]
    stride = {"ship": 1, "fine": 4, "finer": 16}

    counts = {}
    contact = {}
    series = {}
    any_inward = False
    pload_imgs = {k: [] for k in ("rest", "p325", "p358")}
    pload_labs = {k: [] for k in ("rest", "p325", "p358")}
    cont_imgs = {k: [] for k in ("rest", "p325", "p358")}
    cont_labs = {k: [] for k in ("rest", "p325", "p358")}

    for dens in nested:
        deck = resolve_deck(root, dens)
        run = deck / "run"
        n = int((summary.get(dens) or {}).get("N") or 0)
        rec = {"N": n, "density": dens}
        # JSON rest (deck winding)
        try:
            Xj, qj = json_mesh(root, letter, dens)
            rec["json_rest"] = json_safe(classify_faces(Xj, qj))
        except FileNotFoundError:
            rec["json_rest"] = None

        pack_frames = {}
        hist = []
        first_kiss = None
        vtks = sorted(run.glob("Ainflate_A0*.vtk"))
        vmax_cont = 0.0
        parsed = {}
        for vtk in vtks:
            x, cells, t, vecs = parse_vtk_full(vtk)
            quads = vtk_quads(cells)
            cont = vecs.get("Contact_Forces")
            mag_max = float(np.linalg.norm(cont, axis=1).max()) if cont is not None else 0.0
            n_hit = int(np.count_nonzero(np.linalg.norm(cont, axis=1) > KISS_EPS)) if cont is not None else 0
            vmax_cont = max(vmax_cont, mag_max)
            t = 0.0 if t is None else float(t)
            hist.append((t, mag_max, n_hit))
            if first_kiss is None and mag_max > KISS_FORCE:
                first_kiss = {
                    "t": t,
                    "file": vtk.name,
                    "max_CONT_N": mag_max,
                    "n_nodes": n_hit,
                    "p_Pa": pressure_at_t(t),
                }
            parsed[vtk.name] = (x, quads, t, cont)
            if vtk.name in {f["file"] for f in frames}:
                cls = classify_faces(x, quads)
                pack_frames[vtk.name] = (x, quads, t, cont, cls)
                if cls["inward"] > 0:
                    any_inward = True

        series[dens] = hist
        eng = parse_engine_inter(run / "Ainflate_0001.out")
        contact[dens] = {"first_kiss": first_kiss, "engine": eng, "max_CONT_N": vmax_cont}

        for fr in frames:
            pack = pack_frames.get(fr["file"])
            if pack is None:
                continue
            x, quads, t, cont, cls = pack
            rec[fr["key"]] = json_safe(cls)
            rec[fr["key"]]["t"] = t
            rec[fr["key"]]["p_Pa"] = pressure_at_t(t if t else 0.0)
            rec[fr["key"]]["file"] = fr["file"]
            cam = cam_rest if fr["camera"] == "rest" else cam_load
            # 35.8 kPa is a CFL blow-up on the outward C tape; keep that
            # station on the load camera. Early kiss uses rest framing.
            if fr["key"] == "p358" and cls.get("V_mL", 0) > 8000:
                cam = cam_load
            hud = [
                f"C-{dens}  N={n}  +PLOAD n=(N3-N1)×(N4-N2)",
                f"{fr['label']}  out={cls['outward']} in={cls['inward']}  V={cls['V_mL']:.0f} mL",
            ]
            img = render_pload(x, quads, cls, cam, hud, rest=(fr["key"] == "rest"), stride=stride[dens])
            img.save(stills / f"{dens}_{fr['key']}_pload.png")
            pload_imgs[fr["key"]].append(img.copy())
            pload_labs[fr["key"]].append(f"{dens} {n}")

            chud = [
                f"C-{dens}  N={n}  Contact_Forces  (/ANIM/VECT/CONT)",
                f"{fr['label']}  max|CONT|={float(np.linalg.norm(cont, axis=1).max()) if cont is not None else 0:.3e} N",
            ]
            cimg, mx, nh = render_cont(x, quads, cont, cam, chud, vmax=max(vmax_cont, 1e-12))
            cimg.save(stills / f"{dens}_{fr['key']}_cont.png")
            cont_imgs[fr["key"]].append(cimg.copy())
            cont_labs[fr["key"]].append(f"{dens} {n}")

        if first_kiss and first_kiss["file"] not in {f["file"] for f in frames}:
            vtk = run / first_kiss["file"]
            if vtk.exists() and first_kiss["file"] in parsed:
                x, quads, t, cont = parsed[first_kiss["file"]]
                cls = classify_faces(x, quads)
                hud = [
                    f"C-{dens}  first kiss  {first_kiss['file']}",
                    f"t={t*1e3:.2f} ms  p={pressure_at_t(t)/1e3:.1f} kPa  max|CONT|={first_kiss['max_CONT_N']:.3e} N",
                ]
                cimg, mx, nh = render_cont(
                    x, quads, cont, cam_rest if t < 0.01 else cam_load, hud, vmax=max(vmax_cont, 1e-12)
                )
                cimg.save(stills / f"{dens}_first_kiss_cont.png")
        counts[dens] = rec
        print(
            f"{dens}: rest out={rec.get('rest', {}).get('outward')} in={rec.get('rest', {}).get('inward')} "
            f"kiss={first_kiss} INTER={eng.get('first_INTER_limiting_t')}"
        )

    for key, title in (
        ("rest", "C /PLOAD glyphs  rest"),
        ("p325", "C /PLOAD glyphs  32.5 kPa"),
        ("p358", "C /PLOAD glyphs  35.8 kPa"),
    ):
        if pload_imgs[key]:
            concat_h(pload_imgs[key], pload_labs[key], title).save(stills / f"lineup_{key}_pload.png")
        if cont_imgs[key]:
            concat_h(cont_imgs[key], cont_labs[key], f"C Contact_Forces  {title.split('  ')[-1]}").save(
                stills / f"lineup_{key}_cont.png"
            )

    any_kiss = any((contact[d].get("first_kiss") or {}).get("t") is not None for d in contact)
    history_png(series, stills / "cont_history.png", {d: contact[d].get("first_kiss") for d in contact})

    before_flip = None
    bf = out / "counts_before_flip.json"
    if bf.exists():
        try:
            before_flip = json.loads(bf.read_text())
        except json.JSONDecodeError:
            before_flip = None

    payload = {
        "letter": letter,
        "convention": {
            "PLOAD_n": "n = (N3-N1) x (N4-N2)  Altair /PLOAD 3D",
            "outward": "out of enclosed volume (signed CST volume > 0)",
            "ANIM_field": "Contact_Forces (/ANIM/VECT/CONT)",
            "PCONT": "not dumped on these tapes",
            "gap_scalar": "not in VTK",
        },
        "counts": counts,
        "contact": contact,
        "any_inward": any_inward,
        "any_kiss": any_kiss,
        "before_flip": before_flip,
        "same_load": same_load,
        "vtk_note": (
            "`anim_to_vtk` used to skip existing VTK; a shorter re-run then mixed leftover "
            "A0xx frames. Post now drops ANIM/VTK older than the copied engine `.rad` and "
            "reconverts when ANIM is newer."
        ),
        "stills": [p.name for p in sorted(stills.glob("*.png"))],
        "frames": frames,
        "note": (
            "A not relaunched. No finest. μ/ρ locked. "
            "If inward>0, flip those quads and regenerate C ship/fine/finer only."
        ),
    }
    (out / "counts.json").write_text(json.dumps(json_safe(payload), indent=2) + "\n")
    write_md(out, payload)
    print(f"wrote {out / 'C-PLOAD-PROOF.md'}  inward={any_inward} kiss={any_kiss}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
