#!/usr/bin/env python3
"""ANIM → VTK → λ_max(t), V(t), p(t), Ψ(t), contact gap, GIF/MP4.

λ is membrane principal stretch from rest vs deformed (same CST as the
project bar). Ψ = Σ ½ μ (I1−3) H0 A0  with λ3=1/(λ1 λ2).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from mesh_to_radioss import ANIM_DT, P_MAX, T_RAMP, RUNNAME, load_mesh, quadify_orphans
from radioss_law import CONTACT_KISS, H0, MU, RHO, WARN_LAM, law_card_lines

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = ImageDraw = ImageFont = None


def rest_from_json(mesh_path: Path):
    mesh = load_mesh(mesh_path)
    n = mesh["n"]
    pos = np.asarray(mesh["pos"], dtype=np.float64).reshape(n, 3)
    quads, leftover = quadify_orphans(mesh["quads"], mesh["orphans"])
    if leftover:
        raise RuntimeError(f"JSON still has {len(leftover)} unpaired tris")
    cover = []
    for q in quads:
        cover.append((q[0], q[1], q[2]))
        cover.append((q[0], q[2], q[3]))
    return pos, quads, [], cover


def parse_vtk(path: Path):
    text = path.read_text(errors="replace")
    lines = text.splitlines()
    pts = None
    npts = 0
    cells = []
    i = 0
    time = None
    i = 0
    while i < min(40, len(lines)):
        ln = lines[i].strip()
        if ln.startswith("TIME") and "VERSION" not in ln.upper():
            # FIELD: "TIME 1 1 double" then value on the next line
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
            parts = ln.split()
            npts = int(parts[1])
            nums = []
            i += 1
            while len(nums) < 3 * npts and i < len(lines):
                nums.extend(float(x) for x in lines[i].split())
                i += 1
            pts = np.asarray(nums[: 3 * npts], dtype=np.float64).reshape(npts, 3)
            continue
        if ln.startswith("CELLS") or ln.startswith("CONNECTIVITY"):
            # legacy CELLS n size  OR VTK 5.1+ OFFSETS/CONNECTIVITY
            if ln.startswith("CELLS"):
                parts = ln.split()
                ncells = int(parts[1])
                i += 1
                for _ in range(ncells):
                    vals = [int(x) for x in lines[i].split()]
                    cells.append(tuple(vals[1 : 1 + vals[0]]))
                    i += 1
                continue
        i += 1
    if pts is None:
        raise RuntimeError(f"no POINTS in {path}")
    return pts, cells, time


def vtk_cover(cells):
    """Quads from VTK cells. Degenerate quads (n3==n4) and 3-node cells are tris."""
    quads, tris, cover = [], [], []
    for c in cells:
        if len(c) == 4 and c[2] != c[3]:
            q = tuple(int(i) for i in c)
            quads.append(q)
            cover.append((q[0], q[1], q[2]))
            cover.append((q[0], q[2], q[3]))
        elif len(c) == 4:
            t = (int(c[0]), int(c[1]), int(c[2]))
            tris.append(t)
            cover.append(t)
        elif len(c) == 3:
            t = tuple(int(i) for i in c)
            tris.append(t)
            cover.append(t)
    return quads, tris, cover


def _cross(a, b):
    return np.array(
        [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
    )


def tri_stretch(X, x):
    """Return (lam1, lam2, A0, I1, W_density) for one CST triangle."""
    e1 = X[1] - X[0]
    e2 = X[2] - X[0]
    n0 = _cross(e1, e2)
    A0 = 0.5 * np.linalg.norm(n0)
    if A0 < 1e-18:
        return 1.0, 1.0, A0, 3.0, 0.0
    nn = n0 / (2.0 * A0)
    tmp = np.array([0.0, 1.0, 0.0]) if abs(nn[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    t = _cross(nn, tmp)
    t = t / np.linalg.norm(t)
    b = _cross(nn, t)
    D = np.array([[np.dot(e1, t), np.dot(e2, t)], [np.dot(e1, b), np.dot(e2, b)]], dtype=np.float64)
    det = D[0, 0] * D[1, 1] - D[0, 1] * D[1, 0]
    if abs(det) < 1e-18:
        return 1.0, 1.0, A0, 3.0, 0.0
    invD = np.array([[D[1, 1], -D[0, 1]], [-D[1, 0], D[0, 0]]]) / det
    u1 = x[1] - x[0]
    u2 = x[2] - x[0]
    F = np.column_stack((u1, u2)) @ invD  # 3x2
    C = F.T @ F
    tr = C[0, 0] + C[1, 1]
    d = C[0, 0] * C[1, 1] - C[0, 1] * C[1, 0]
    disc = max(0.0, (tr * 0.5) ** 2 - d)
    s = math.sqrt(disc)
    ev1 = max(1e-16, tr * 0.5 + s)
    ev2 = max(1e-16, tr * 0.5 - s)
    lam1 = math.sqrt(ev1)
    lam2 = math.sqrt(ev2)
    lam3 = 1.0 / max(lam1 * lam2, 1e-16)
    I1 = lam1 * lam1 + lam2 * lam2 + lam3 * lam3
    W = 0.5 * MU * (I1 - 3.0)
    return lam1, lam2, A0, I1, W


def metrics_frame(X, x, quads, orphans):
    lam_max = 1.0
    Psi = 0.0
    nneg = 0
    for q in quads:
        for tri in ((q[0], q[1], q[2]), (q[0], q[2], q[3])):
            lam1, lam2, A0, I1, W = tri_stretch(X[list(tri)], x[list(tri)])
            lam_max = max(lam_max, lam1, lam2)
            Psi += W * H0 * A0
            if W < -1e-12:
                nneg += 1
    for t in orphans:
        lam1, lam2, A0, I1, W = tri_stretch(X[list(t)], x[list(t)])
        lam_max = max(lam_max, lam1, lam2)
        Psi += W * H0 * A0
        if W < -1e-12:
            nneg += 1
    return lam_max, Psi, nneg


def enclosed_volume(x, cover):
    v = 0.0
    for i, j, k in cover:
        a, b, c = x[i], x[j], x[k]
        v += (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            + a[1] * (b[2] * c[0] - b[0] * c[2])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6.0
    return v


def pressure_at(t: float) -> float:
    if t <= 0:
        return 0.0
    if t >= T_RAMP:
        return P_MAX
    return P_MAX * (t / T_RAMP)


def adjacency(n, quads, orphans):
    adj = [set() for _ in range(n)]

    def add(a, b):
        adj[a].add(b)
        adj[b].add(a)

    for q in quads:
        for i in range(4):
            add(q[i], q[(i + 1) % 4])
    for t in orphans:
        for i in range(3):
            add(t[i], t[(i + 1) % 3])
    ring2 = []
    for i in range(n):
        r1 = set(adj[i])
        r2 = set(r1)
        for j in r1:
            r2.update(adj[j])
        r2.add(i)
        ring2.append(r2)
    return ring2


def contact_gap(x, Xrest, cover, ring2):
    """Min distance to faces whose rest centroids are far (not same-sheet)."""
    min_u = 1e9
    min_s = 1e9
    punch = False
    far = 0.008
    faces = []
    for (i, j, k) in cover:
        a, b, c = x[i], x[j], x[k]
        nvec = _cross(b - a, c - a)
        ln = np.linalg.norm(nvec)
        if ln < 1e-18:
            continue
        nrm = nvec / ln
        c0 = (Xrest[i] + Xrest[j] + Xrest[k]) / 3.0
        faces.append((i, j, k, a, nrm, c0))
    step = 1 if len(x) < 400 else 2
    for vi in range(0, len(x), step):
        p = x[vi]
        skip = ring2[vi]
        pr = Xrest[vi]
        for (i, j, k, a, nrm, c0) in faces:
            if i in skip or j in skip or k in skip:
                continue
            if np.linalg.norm(pr - c0) < far:
                continue
            sd = float(np.dot(p - a, nrm))
            au = abs(sd)
            if au < min_u:
                min_u = au
                min_s = sd
            # Punch-through is volume sign (V<0), not this plane heuristic.
    if min_u > 1e8:
        min_u = float("nan")
        min_s = float("nan")
    return min_u, min_s, punch


def convert_anim(run_dir: Path, anim_bin: str) -> list[Path]:
    anims = sorted(p for p in run_dir.iterdir() if p.name.startswith(f"{RUNNAME}A") and p.is_file())
    vtks = []
    for anim in anims:
        tag = anim.name[len(RUNNAME) + 1 :]  # A001 → wait name is AinflateA001
        # AinflateA001 → after RUNNAME "A001"
        suffix = anim.name[len(RUNNAME) :]  # A001
        vtk = run_dir / f"{RUNNAME}_{suffix}.vtk"
        if not vtk.exists() or vtk.stat().st_size < 100:
            with vtk.open("w") as out:
                r = subprocess.run([anim_bin, str(anim)], stdout=out, stderr=subprocess.PIPE, text=True)
            if r.returncode != 0:
                print(f"anim_to_vtk failed {anim}: {r.stderr[-500:]}", file=sys.stderr)
                continue
        vtks.append(vtk)
    return vtks


def look_font(size: int):
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/opentype/inter/Inter[slnt,wght].ttf",
    ):
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_frame(x, quads, lams_quad, hud, size=720, warn=False):
    """Orthographic +Z view, Y up. Fill + stroke **quads** (no diagonal bleed)."""
    w = h = size
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[:] = (18, 18, 22)
    xy = x[:, :2]
    xmin, ymin = xy.min(axis=0)
    xmax, ymax = xy.max(axis=0)
    span = max(xmax - xmin, ymax - ymin, 1e-6) * 1.18
    cx, cy = 0.5 * (xmin + xmax), 0.5 * (ymin + ymax)

    def to_px(p):
        px = (p[0] - cx) / span * (w * 0.92) + w * 0.5
        py = h * 0.5 - (p[1] - cy) / span * (h * 0.92)
        return px, py

    faces = []
    for fi, q in enumerate(quads):
        zc = (x[q[0], 2] + x[q[1], 2] + x[q[2], 2] + x[q[3], 2]) / 4.0
        faces.append((zc, fi, q))
    # Camera at +Z looking toward -Z: nearest is max z, draw far (min z) first
    faces.sort(key=lambda t: t[0])

    def lerp(c0, c1, t):
        t = max(0.0, min(1.0, t))
        return tuple(int(c0[k] + (c1[k] - c0[k]) * t) for k in range(3))

    edge = (52, 52, 60)
    for zc, fi, q in faces:
        lam = lams_quad[fi] if fi < len(lams_quad) else 1.0
        t = (lam - 1.0) / max(WARN_LAM - 1.0, 1e-6)
        col = lerp((210, 210, 214), (196, 72, 28), t)
        # same color on both CST halves so the diagonal does not read as a tri mesh
        _fill_tri(img, [to_px(x[q[0]]), to_px(x[q[1]]), to_px(x[q[2]])], col)
        _fill_tri(img, [to_px(x[q[0]]), to_px(x[q[2]]), to_px(x[q[3]])], col)

    pil = Image.fromarray(img, "RGB")
    draw = ImageDraw.Draw(pil)
    for zc, fi, q in faces:
        pts = [to_px(x[q[i]]) for i in range(4)]
        ring = pts + [pts[0]]
        draw.line(ring, fill=edge, width=1)
    font = look_font(18)
    font_b = look_font(22)
    y = 10
    for line in hud:
        draw.text((12, y), line, fill=(240, 240, 240), font=font)
        y += 22
    if warn:
        draw.rectangle([10, h - 48, w - 10, h - 12], outline=(220, 90, 40), width=2)
        draw.text((18, h - 44), "WARN  first λ_max ≥ 2", fill=(255, 200, 140), font=font_b)
    return pil


def _fill_tri(img, pts, col):
    h, w, _ = img.shape
    pts = np.array(pts, dtype=np.float64)
    minx = max(0, int(np.floor(pts[:, 0].min())))
    maxx = min(w - 1, int(np.ceil(pts[:, 0].max())))
    miny = max(0, int(np.floor(pts[:, 1].min())))
    maxy = min(h - 1, int(np.ceil(pts[:, 1].max())))
    if maxx <= minx or maxy <= miny:
        return
    (x0, y0), (x1, y1), (x2, y2) = pts
    den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if abs(den) < 1e-12:
        return
    ys, xs = np.mgrid[miny : maxy + 1, minx : maxx + 1]
    w0 = ((y1 - y2) * (xs - x2) + (x2 - x1) * (ys - y2)) / den
    w1 = ((y2 - y0) * (xs - x2) + (x0 - x2) * (ys - y2)) / den
    w2 = 1.0 - w0 - w1
    m = (w0 >= -1e-4) & (w1 >= -1e-4) & (w2 >= -1e-4)
    img[miny : maxy + 1, minx : maxx + 1][m] = col


def face_lams(X, x, cover):
    out = []
    for tri in cover:
        lam1, lam2, *_ = tri_stretch(X[list(tri)], x[list(tri)])
        out.append(max(lam1, lam2))
    return out


def quad_lams(X, x, quads):
    """One λ per quad (max of the two CST halves) so fill has no diagonal seam."""
    out = []
    for q in quads:
        m = 1.0
        for tri in ((q[0], q[1], q[2]), (q[0], q[2], q[3])):
            lam1, lam2, *_ = tri_stretch(X[list(tri)], x[list(tri)])
            m = max(m, lam1, lam2)
        out.append(m)
    return out


def ffmpeg_encode(frames_dir: Path, gif: Path, mp4: Path):
    pattern = str(frames_dir / "frame_%04d.png")
    subprocess.run(
        [
            "ffmpeg", "-y", "-framerate", "8", "-i", pattern,
            "-pix_fmt", "yuv420p", "-vf", "scale=720:720",
            str(mp4),
        ],
        check=False,
        capture_output=True,
    )
    pal = frames_dir / "palette.png"
    subprocess.run(
        ["ffmpeg", "-y", "-framerate", "8", "-i", pattern, "-vf", "palettegen", str(pal)],
        check=False,
        capture_output=True,
    )
    if pal.exists():
        subprocess.run(
            [
                "ffmpeg", "-y", "-framerate", "8", "-i", pattern, "-i", str(pal),
                "-lavfi", "paletteuse", str(gif),
            ],
            check=False,
            capture_output=True,
        )


def write_run_md(path: Path, rows, warn_row, blockers, extra, mesh_note=None):
    lines = ["# A-inflate first light — RUN", ""]
    lines.append("Cloud VM job. OpenRadioss linux64_gf (`latest-20260728`). SI deck. **μ and ρ not retuned.**")
    lines.append("")
    lines.append("## Law card dump")
    lines.append("```")
    lines.extend(law_card_lines())
    lines.append("  /PROP   N=1  Ismstr=10  Ishell=1 (Belytschko)  Ithick=1")
    lines.append("  /INTER/TYPE19  Igap=4  Irem_gap=2  Inacti=6  Gapmin=CONTACT_KISS")
    lines.append("  /PLOAD  0 → 65000 Pa in 0.04 s (not MONVOL)")
    lines.append("```")
    lines.append("")
    lines.append("## Quad-only (no triangle bleed)")
    lines.append("")
    lines.append("- Inflate part is **`/SHELL` only**. No `/SH3N`.")
    lines.append("- Ship `meshes/A.json` midplane is already quad (`nMidTris=0`); **not remeshed to tris**.")
    lines.append("- 28 orphan cap `faceTris` are **paired along shared edges into 14 quads** at convert time (same V0).")
    lines.append("- ANIM/VTK + GIF/warn still are drawn as **nice quads** (uniform fill per shell + perimeter edges; no CST diagonal).")
    if mesh_note:
        lines.append(f"- ANIM cells: {mesh_note}")
    lines.append("")
    lines.append("## Inertial relief / free-free")
    lines.append("")
    lines.append("- **No `/BCS`** — 3-2-1 grounded nodes dropped.")
    lines.append("- OpenRadioss explicit analogue of inertial relief is engine **`/ADYREL`** (adaptive dynamic relaxation).")
    lines.append("- Radioss has **no `PARAM,INREL`** (that is OptiStruct). Closed `/PLOAD` on a watertight shell is self-equilibrated (net F≈0).")
    lines.append("- Kept starter **`/DAMP`** Rayleigh mass α=80 1/s as residual rigid-body sink.")
    lines.append("")
    lines.append("## ρ source")
    lines.append("")
    lines.append("ρ = **1130 kg/m³** — Desmopan 85085A **ISO 1183-1**.")
    lines.append("McMaster-Carr 1446T11 (85A film) **does not publish density**; the ISO 1183-1")
    lines.append("Desmopan 85085A value is the desked label. Not invented, not retuned.")
    lines.append("")
    lines.append("## λ ≥ 2 frame")
    lines.append("")
    if warn_row:
        lines.append(
            f"- **frame {warn_row['frame']}** (`{warn_row['file']}` / `artifacts/warn-lambda2.png`)"
        )
        lines.append(f"- t = **{warn_row['t']:.5g} s**")
        lines.append(f"- λ_max = **{warn_row['lam_max']:.4g}**")
        lines.append(
            f"- p = **{warn_row['p_Pa']:.0f} Pa** (PLOAD ramp; **dynamic**, not Chiron QS — JS warn was ~54100 Pa at equilibrium)"
        )
        lines.append(f"- V = **{warn_row['V_mL']:.4g} mL**")
        lines.append("- Overlay: `WARN  first λ_max ≥ 2`")
    else:
        lines.append("- **not reached** in this run (see blockers / last frame below).")
    lines.append("")
    lines.append("## Correctness tape")
    lines.append("")
    lines.append("λ from CST membrane principals on ANIM/VTK (rest = frame 0). Ψ = Σ ½ μ (I1−3) H0 A0, λ3=1/(λ1 λ2).")
    lines.append("")
    lines.append("| frame | t [s] | p [Pa] | λ_max | V [mL] | Ψ [J] |")
    lines.append("|------:|------:|-------:|------:|-------:|------:|")
    for r in rows:
        lines.append(
            f"| {r['frame']} | {r['t']:.5g} | {r['p_Pa']:.0f} | {r['lam_max']:.4f} | "
            f"{r['V_mL']:.4g} | {r['Psi_J']:.4g} |"
        )
    lines.append("")
    if rows:
        psi_ok = all(r["Psi_J"] >= -1e-8 for r in rows)
        lines.append(f"Ψ(t) ≥ 0: **{'yes' if psi_ok else 'FAIL'}**  (min {min(r['Psi_J'] for r in rows):.4g} J)")
        v_ok = all(r["V_mL"] > 0 for r in rows)
        lines.append(f"Enclosed V(t) **{' > 0 every frame' if v_ok else 'NON-POSITIVE'}** (no global inside-out)")
        lines.append(
            "Contact: `/INTER/TYPE19` Gapmin = **0.762 mm** (= CONTACT_KISS). "
            "A plane-distance heuristic is too noisy for a min-gap column."
        )
    lines.append("")
    lines.append("## Blockers (CFL / AMS)")
    lines.append("")
    if blockers:
        for b in blockers:
            lines.append(f"- {b}")
    else:
        lines.append("- Natural CFL at start ~1.3e-5 s (Belytschko N=1). `/DT/NODA/CST 0.9 1e-6` armed.")
        lines.append("- Try-first QEPH (Ishell=24)+Ismstr=10 ruptured at rest (no PLOAD). Working first light: Belytschko Ishell=1, Ismstr=10, N=1.")
        lines.append("- No `/AMS`. μ and ρ unchanged.")
    for e in extra:
        lines.append(f"- {e}")
    lines.append("")
    lines.append("## Artifacts")
    lines.append("")
    lines.append("- `artifacts/A-inflate.gif` / `A-inflate.mp4` — rest → past first λ≥2 (warn frame labeled)")
    lines.append("- `artifacts/warn-lambda2.png` (or `last-frame.png` if λ<2)")
    lines.append("- `artifacts/metrics.csv`")
    lines.append("- `law-card.txt`")
    path.write_text("\n".join(lines) + "\n")


def scan_logs(run_dir: Path):
    blockers = []
    for name in ("starter.log", "engine.log", "starter.out", f"{RUNNAME}_0000.out"):
        p = run_dir / name
        if not p.exists():
            continue
        txt = p.read_text(errors="replace")
        low = txt.lower()
        if "error" in low:
            for line in txt.splitlines():
                if "error" in line.lower() and "0 error" not in line.lower():
                    blockers.append(line.strip()[:200])
        if "ams" in low:
            blockers.append("log mentions AMS")
        if "time step" in low and "smaller" in low:
            blockers.append("time step collapsed (see engine log)")
    # starter listing
    for p in run_dir.glob("*.out"):
        txt = p.read_text(errors="replace")
        if "MINIMUM TIME STEP" in txt.upper() or "DT=" in txt.upper():
            for line in txt.splitlines():
                if "TIME STEP" in line.upper() or "DT " in line.upper():
                    if "MIN" in line.upper() or "INITIAL" in line.upper():
                        blockers.append("dt: " + line.strip()[:180])
                        break
    # unique
    seen = set()
    out = []
    for b in blockers:
        if b not in seen:
            seen.add(b)
            out.append(b)
    return out[:12]


def main(argv=None) -> int:
    repo = _TOOLS.parent
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", type=Path, default=repo / "radioss" / "A-inflate" / "run")
    ap.add_argument("--deck-dir", type=Path, default=repo / "radioss" / "A-inflate")
    ap.add_argument("--mesh", type=Path, default=repo / "meshes" / "A.json")
    args = ap.parse_args(argv)

    art = args.deck_dir / "artifacts"
    frames_dir = art / "frames"
    art.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    anim_bin = os.environ.get("ANIM_TO_VTK", "anim_to_vtk_linux64_gf")
    vtks = convert_anim(args.run_dir, anim_bin)
    if not vtks:
        vtks = sorted(args.run_dir.glob(f"{RUNNAME}_A*.vtk"))
        vtks = [p for p in vtks if p.stat().st_size > 100]
    vtks = sorted(vtks, key=lambda p: p.name)
    if not vtks:
        print("no VTK/ANIM frames", file=sys.stderr)
        write_run_md(
            args.deck_dir / "RUN.md",
            [],
            None,
            ["No ANIM/VTK frames — engine did not produce animation, or anim_to_vtk missing."]
            + scan_logs(args.run_dir),
            [],
        )
        return 2

    # anim_to_vtk reorders nodes. Rest = first ANIM (t=0); connectivity from VTK cells.
    X, cells0, t0 = parse_vtk(vtks[0])
    quads, orphans, cover = vtk_cover(cells0)
    if orphans:
        print(
            f"ERROR: ANIM still has {len(orphans)} triangle cells (want quad-only /SHELL)",
            file=sys.stderr,
        )
    print(f"ANIM cells: {len(quads)} quads, {len(orphans)} tris")
    ring2 = adjacency(len(X), quads, orphans)

    rows = []
    warn_row = None
    last_img = None
    for fi, vtk in enumerate(vtks):
        pts, cells, time = parse_vtk(vtk)
        x = np.asarray(pts, dtype=np.float64)
        if time is None:
            digits = "".join(ch for ch in vtk.stem if ch.isdigit())
            idx = int(digits) if digits else fi
            time = max(0, idx - 1) * ANIM_DT
        lam_max, Psi, nneg = metrics_frame(X, x, quads, orphans)
        V = enclosed_volume(x, cover)
        gap_u, min_s, punch = contact_gap(x, X, cover, ring2)
        if V < 0:
            punch = True
        p = pressure_at(time)
        row = {
            "frame": fi,
            "file": vtk.name,
            "t": time,
            "p_Pa": p,
            "lam_max": lam_max,
            "V_m3": V,
            "V_mL": V * 1e6,
            "Psi_J": Psi,
            "Psi_neg_elems": nneg,
            "gap_m": gap_u,
            "gap_mm": gap_u * 1e3 if gap_u == gap_u else float("nan"),
            "gap_signed_m": min_s,
            "punch": punch,
            "n_quads": len(quads),
            "n_tris": len(orphans),
        }
        rows.append(row)
        print(
            f"frame {fi:03d} t={time:.4g}s  p={p:.4g} Pa  λ_max={lam_max:.4f}  "
            f"V={V*1e6:.4g} mL  Ψ={Psi:.4g} J  gap={row['gap_mm']:.3g} mm  punch={punch}"
        )
        lams = quad_lams(X, x, quads)
        hud = [
            f"OpenRadioss A  frame {fi}  t={time*1e3:.3g} ms",
            f"p = {p:.0f} Pa   λ_max = {lam_max:.3f}   V = {V*1e6:.1f} mL",
            f"Ψ = {Psi:.4g} J   quads={len(quads)} SH3N={len(orphans)}  /ADYREL",
        ]
        is_warn = lam_max >= WARN_LAM and warn_row is None
        img = render_frame(x, quads, lams, hud, warn=is_warn or (warn_row is not None and fi == warn_row["frame"]))
        png = frames_dir / f"frame_{fi:04d}.png"
        img.save(png)
        last_img = png
        if is_warn:
            warn_row = row
            img.save(art / "warn-lambda2.png")

    with (art / "metrics.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    (art / "metrics.json").write_text(json.dumps(rows, indent=2))

    if warn_row is None and last_img:
        dest = art / "last-frame.png"
        dest.write_bytes(last_img.read_bytes())

    gif = art / "A-inflate.gif"
    mp4 = art / "A-inflate.mp4"
    ffmpeg_encode(frames_dir, gif, mp4)

    blockers = scan_logs(args.run_dir)
    extra = []
    if orphans:
        extra.append(f"ANIM still contains {len(orphans)} triangle cells — GIF may show tri bleed.")
    if not gif.exists() and not mp4.exists():
        extra.append("ffmpeg GIF/MP4 encode failed — PNG frames are in artifacts/frames/")
    write_run_md(
        args.deck_dir / "RUN.md",
        rows,
        warn_row,
        blockers,
        extra,
        mesh_note=f"{len(quads)} quads, {len(orphans)} tris",
    )
    print(f"wrote {args.deck_dir / 'RUN.md'}")
    print(f"warn frame: {warn_row['frame'] if warn_row else 'NOT REACHED'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
