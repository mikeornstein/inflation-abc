#!/usr/bin/env python3
"""Same-load refine grading (Mike): strain at fixed p, not first λ≥2.

Loads:
  ~32.5 kPa  (t≈20 ms, ANIM frame 10)
  ~35.8 kPa  (t≈22 ms, ANIM frame 11)

If a letter's ANIM stations differ, pick the frames whose p matches those
two loads (not a first-λ≥2 crossing). Nested family: ship / fine / finer
(/ finest when present). Wall-clock = OpenRadioss ELAPSED TIME from the
engine .out (not Python post).
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from radioss_post import (  # noqa: E402
    enclosed_volume,
    lambda_field_stats,
    look_font,
    metrics_frame,
    parse_vtk,
    quad_lams,
    render_frame,
    vtk_cover,
)

NESTED = ("ship", "fine", "finer", "finest")


def letter_of(root: Path, summary: dict | None = None) -> str:
    summary = summary or {}
    L = str(summary.get("letter") or "").upper()
    if L in ("A", "B", "C"):
        return L
    name = root.name
    if len(name) >= 1 and name[0] in "ABC" and name.endswith("-refine"):
        return name[0]
    return "A"


def nested_present(root: Path, summary: dict | None = None) -> tuple[str, ...]:
    summary = summary or {}
    out = []
    for dens in NESTED:
        if dens in summary or (root / dens).exists() or (
            dens == "finest" and resolve_deck(root, dens).exists()
        ):
            out.append(dens)
    return tuple(out)


def resolve_deck(root: Path, dens: str) -> Path:
    """Prefer a labeled CFL fork that has ANIM past rest."""
    names = [f"{dens}-stop1e7", f"{dens}-stop5e7", f"{dens}-ams"]
    if dens == "finest":
        names = ["finest-stop5e7", "finest-ams"] + names
    started = None
    for name in names:
        fork = root / "forks" / name
        n_anim = len(list((fork / "run").glob("AinflateA0*"))) if (fork / "run").exists() else 0
        n_vtk = len(list((fork / "run").glob("Ainflate_A0*.vtk"))) if (fork / "run").exists() else 0
        grade = (fork / "run" / "Ainflate_A011.vtk").exists() or list((fork / "run").glob("AinflateA011*"))
        if grade or ((n_anim > 2 or n_vtk > 2) and dens == "finest"):
            return fork
        if started is None and (fork / "run").exists() and (n_anim > 0 or n_vtk > 0):
            started = fork
    if started is not None:
        return started
    return root / dens
LOADS = (
    {"key": "p325", "p_Pa": 32500.0, "t": 0.020, "label": "32.5 kPa", "t_ms": 20},
    {"key": "p358", "p_Pa": 35750.0, "t": 0.022, "label": "35.8 kPa", "t_ms": 22},
)
AZ, EL = 0.55, 0.38
BEIGE = (196, 163, 122)
DV_MAX, DLAM_MAX, DAW_MAX = 0.05, 0.02, 0.02


def project(p) -> tuple[float, float]:
    x, y, z = float(p[0]), float(p[1]), float(p[2])
    ca, sa = math.cos(AZ), math.sin(AZ)
    ce, se = math.cos(EL), math.sin(EL)
    x1 = x * ca + z * sa
    z1 = -x * sa + z * ca
    y1 = y * ce - z1 * se
    return x1, y1


def rel(a, b) -> float:
    den = abs(b) if abs(b) > 1e-30 else 1e-30
    return abs(a - b) / den


def parse_timing(run_dir: Path) -> dict:
    """OpenRadioss wall-clock from engine/starter .out — not Python post."""
    out = {
        "engine_elapsed_s": None,
        "starter_s": None,
        "starter_plus_engine_s": None,
        "cycles": None,
        "threads": None,
        "source": None,
        "rerun_this_session": False,
        "termination": None,
    }
    eng = run_dir / "Ainflate_0001.out"
    st = run_dir / "Ainflate_0000.out"
    txt = eng.read_text(errors="replace") if eng.exists() else ""
    stxt = st.read_text(errors="replace") if st.exists() else ""
    if not txt and not stxt:
        return out
    out["source"] = "Ainflate_0001.out" if eng.exists() else "Ainflate_0000.out"
    if "ERROR TERMINATION" in txt:
        out["termination"] = "ERROR"
    elif "NORMAL TERMINATION" in txt:
        out["termination"] = "NORMAL"
    m = re.search(r"ELAPSED TIME\s*=\s*([0-9.]+)\s*s", txt)
    if not m:
        m = re.search(r"ELAPSED TIME\.*=\s*([0-9.]+)\s*s", txt)
    if m:
        out["engine_elapsed_s"] = float(m.group(1))
    m = re.search(r"TOTAL NUMBER OF CYCLES\s*:\s*(\d+)", txt)
    if m:
        out["cycles"] = int(m.group(1))
    else:
        cyc = re.findall(r"^\s+(\d+)\s+0\.\d", txt, re.M)
        if cyc:
            out["cycles"] = int(cyc[-1])
    m = re.search(r"NUMBER OF THREADS PER DOMAIN\s+(\d+)", txt)
    if m:
        out["threads"] = int(m.group(1))
    m = re.search(r"STARTER RUNTIME\s*=\s*([0-9.]+)\s*s", txt)
    if m:
        out["starter_s"] = float(m.group(1))
    if out["starter_s"] is None and stxt:
        m = re.search(r"ELAPSED TIME\.*=\s*([0-9.]+)\s*s", stxt)
        if m:
            out["starter_s"] = float(m.group(1))
    m = re.search(r"STARTER\+ENGINE RUNTIME\s*=\s*([0-9.]+)\s*s", txt)
    if m:
        out["starter_plus_engine_s"] = float(m.group(1))
    elif out["engine_elapsed_s"] is not None and out["starter_s"] is not None:
        out["starter_plus_engine_s"] = out["engine_elapsed_s"] + out["starter_s"]
    out["source"] = "Ainflate_0001.out (prior tape; not re-run this session)"
    return out


def pick_frame(rows: list[dict], load: dict) -> dict | None:
    """Closest PLOAD station to the target pressure; t is the tie-break.

    A uses t≈20/22 ms. If B/C ANIM frames differ, p-match wins.
    """
    if not rows:
        return None
    p_target = float(load.get("p_Pa", 0.0))
    t_target = float(load.get("t", 0.0))
    return min(
        rows,
        key=lambda r: (abs(float(r["p_Pa"]) - p_target), abs(float(r["t"]) - t_target)),
    )


def load_metrics(deck: Path) -> list[dict]:
    p = deck / "artifacts" / "metrics.json"
    if not p.exists():
        return []
    return json.loads(p.read_text())


def vtk_for_row(run_dir: Path, row: dict) -> Path | None:
    name = row.get("file")
    if not name:
        return None
    p = run_dir / name
    return p if p.exists() else None


def _aabb_camera(xy: np.ndarray, pad: float) -> tuple[float, float, float]:
    xmin, ymin = xy.min(0)
    xmax, ymax = xy.max(0)
    span = max(xmax - xmin, ymax - ymin, 1e-6) * pad
    cx, cy = 0.5 * (xmin + xmax), 0.5 * (ymin + ymax)
    return float(cx), float(cy), float(span)


def rest_camera(root: Path, letter: str = "A") -> tuple[float, float, float]:
    """Same camera across rest densities, fitted to the undeformed letter."""
    ship = json.loads((root / "meshes" / f"{letter}-ship.json").read_text())
    pos = np.asarray(ship["pos0"], dtype=float).reshape(-1, 3)
    xy = np.asarray([project(p) for p in pos], dtype=float)
    return _aabb_camera(xy, 1.22)


def load_camera(root: Path, nested: tuple[str, ...] | None = None) -> tuple[float, float, float]:
    """Same camera at both grade pressures, fitted to inflated AABB (not rest).

    Rest-fitted framing crops the balloon: inflation puffs in Z, which this
    3/4 view maps to +Y. Union of nested p325/p358 VTKs keeps every N in frame.
    """
    order = nested or nested_present(root)
    chunks = []
    for dens in order:
        deck = resolve_deck(root, dens)
        rows = load_metrics(deck)
        picked = []
        for ld in LOADS:
            row = pick_frame(rows, ld) if rows else None
            if row and row.get("file"):
                picked.append(row["file"])
        if not picked:
            picked = ["Ainflate_A011.vtk", "Ainflate_A012.vtk"]
        for name in dict.fromkeys(picked):
            vtk = deck / "run" / name
            if not vtk.exists():
                continue
            x, _cells, _t = parse_vtk(vtk)
            # Skip CFL-blow-up frames (λ≫2 or V tens of litres) so the grade
            # camera is not fitted to a ruptured balloon.
            row_m = next((r for r in rows if r.get("file") == name), None)
            if row_m is not None:
                if float(row_m.get("lam_max") or 0) > 8.0 or float(row_m.get("V_mL") or 0) > 8000:
                    continue
            chunks.append(np.asarray([project(p) for p in x], dtype=float))
    if not chunks:
        return rest_camera(root, letter_of(root))
    xy = np.vstack(chunks)
    return _aabb_camera(xy, 1.18)


def feature_edges(x: np.ndarray, quads, deg: float = 22.0):
    """Boundary + dihedral edges — readable on N=99456 without a full wireframe."""
    from collections import defaultdict

    adj: dict[tuple[int, int], list[int]] = defaultdict(list)
    nrms = np.zeros((len(quads), 3), dtype=float)
    for fi, q in enumerate(quads):
        p0, p1, p2 = x[int(q[0])], x[int(q[1])], x[int(q[2])]
        n = np.cross(p1 - p0, p2 - p0)
        ln = float(np.linalg.norm(n)) + 1e-30
        nrms[fi] = n / ln
        for k in range(4):
            a, b = int(q[k]), int(q[(k + 1) % 4])
            e = (a, b) if a < b else (b, a)
            adj[e].append(fi)
    cos_th = math.cos(math.radians(deg))
    out = []
    for (a, b), faces in adj.items():
        if len(faces) < 2:
            out.append((a, b))
        elif abs(float(np.dot(nrms[faces[0]], nrms[faces[1]]))) < cos_th:
            out.append((a, b))
    return out


def render_still(x, quads, X, camera, hud, *, rest=False, size=720, warn=False, warn_label=""):
    nq = len(quads)
    lams = np.ones(nq) if rest else quad_lams(X, x, quads)
    full_wire = nq <= 30000
    extra = None if full_wire else feature_edges(x, quads)
    return render_frame(
        x,
        quads,
        lams,
        hud,
        size=size,
        warn=warn,
        camera=camera,
        draw_edges=full_wire,
        extra_edges=extra,
        project=project,
        rest_fill=BEIGE if rest else None,
        warn_label=warn_label or "same load",
    )


def concat_h(images: list[Image.Image], labels: list[str], title: str) -> Image.Image:
    pad = 36
    w = sum(im.width for im in images) + 16 * (len(images) + 1)
    h = max(im.height for im in images) + pad + 28
    canvas = Image.new("RGB", (w, h), (10, 10, 12))
    draw = ImageDraw.Draw(canvas)
    font = look_font(16)
    font_t = look_font(18)
    draw.text((16, 8), title, fill=(230, 230, 230), font=font_t)
    x = 16
    y = pad
    for im, lab in zip(images, labels):
        canvas.paste(im, (x, y))
        draw.text((x + 8, y + im.height - 22), lab, fill=(240, 240, 240), font=font)
        x += im.width + 16
    return canvas


def field_from_vtk(vtk: Path):
    x, cells, time = parse_vtk(vtk)
    x = np.asarray(x, dtype=np.float64)
    return x, cells, time


def rest_and_cover(run_dir: Path):
    vtks = sorted(run_dir.glob("Ainflate_A*.vtk"))
    if not vtks:
        return None
    X, cells0, _ = parse_vtk(vtks[0])
    quads, orphans, cover = vtk_cover(cells0)
    return np.asarray(X, dtype=np.float64), quads, orphans, cover


def grade_load(rows_by_dens: dict, load: dict, nested: tuple[str, ...] | None = None) -> list[dict]:
    order = [d for d in (nested or NESTED) if d in rows_by_dens]
    pairs = []
    for i in range(len(order) - 1):
        a, b = rows_by_dens[order[i]], rows_by_dens[order[i + 1]]
        dv = rel(b["V_mL"], a["V_mL"])
        dl = rel(b["lam_max"], a["lam_max"])
        daw = rel(b["lam_aw_mean"], a["lam_aw_mean"])
        dpsi = rel(b["Psi_J"], a["Psi_J"])
        ok = dv <= DV_MAX and dl <= DLAM_MAX and daw <= DAW_MAX and b["Psi_J"] >= -1e-8
        pairs.append(
            {
                "pair": f"{order[i]}→{order[i+1]}",
                "Ns": f"{a['N']} → {b['N']}",
                "load": load["key"],
                "dv": dv,
                "dlam": dl,
                "daw": daw,
                "dpsi": dpsi,
                "dv_ok": dv <= DV_MAX,
                "dlam_ok": dl <= DLAM_MAX,
                "daw_ok": daw <= DAW_MAX,
                "pass": ok,
            }
        )
    return pairs


def main(argv=None) -> int:
    repo = _TOOLS.parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=repo / "radioss" / "A-refine")
    ap.add_argument("--no-stills", action="store_true")
    ap.add_argument("--session-rerun", action="append", default=[], help="densities timed this session")
    args = ap.parse_args(argv)
    root = args.root
    stills = root / "stills"
    stills.mkdir(parents=True, exist_ok=True)
    summary = json.loads((root / "mesh-summary.json").read_text()) if (root / "mesh-summary.json").exists() else {}
    letter = letter_of(root, summary)
    nested = nested_present(root, summary) or NESTED[:3]
    v0 = float((summary.get("ship") or {}).get("V0_mL") or 0.0)
    cam_rest = rest_camera(root, letter)
    cam_load = load_camera(root, nested)
    (root / "camera.json").write_text(
        json.dumps(
            {
                "letter": letter,
                "az": AZ,
                "el": EL,
                "rest": {"cx": cam_rest[0], "cy": cam_rest[1], "span": cam_rest[2]},
                "load": {"cx": cam_load[0], "cy": cam_load[1], "span": cam_load[2]},
                "note": (
                    f"Letter {letter}: rest camera fitted to undeformed ship. "
                    "Load camera is the same at 32.5 and 35.8 kPa, fitted to nested inflated AABB."
                ),
            },
            indent=2,
        )
        + "\n"
    )

    session = set(args.session_rerun)

    timings = {}
    loads_out = {ld["key"]: [] for ld in LOADS}
    rest_imgs = []
    rest_labs = []
    load_imgs = {ld["key"]: [] for ld in LOADS}
    load_labs = {ld["key"]: [] for ld in LOADS}
    station_notes = []

    for dens in nested:
        deck = resolve_deck(root, dens)
        if not deck.exists():
            continue
        meta = json.loads((deck / "deck-meta.json").read_text()) if (deck / "deck-meta.json").exists() else {}
        n = int((summary.get(dens) or {}).get("N") or meta.get("n") or 0)
        timing = parse_timing(deck / "run")
        if dens in session:
            timing["rerun_this_session"] = True
            timing["source"] = "Ainflate_0001.out (timed this session)"
        timings[dens] = {"density": dens, "N": n, **timing}
        (deck / "artifacts").mkdir(parents=True, exist_ok=True)
        (deck / "artifacts" / "timing.json").write_text(json.dumps(timings[dens], indent=2) + "\n")

        run_dir = deck / "run"
        pack = rest_and_cover(run_dir)
        rows = load_metrics(deck)
        if pack is None:
            print(f"skip stills {dens}: no VTK")
        else:
            X, quads, orphans, cover = pack
            if not args.no_stills:
                v0_d = float((summary.get(dens) or {}).get("V0_mL") or v0 or 0.0)
                hud = [f"{letter}-{dens}  N={n}  rest", f"V0 ≈ {v0_d:.0f} mL  /ADYREL"]
                img = render_still(X, quads, X, cam_rest, hud, rest=True, size=640)
                img.save(stills / f"{dens}_rest.png")
                rest_imgs.append(img.copy())
                rest_labs.append(f"{dens} {n}")

        for ld in LOADS:
            rec = {
                "density": dens,
                "N": n,
                "load": ld["key"],
                "p_target_Pa": ld["p_Pa"],
                "t_target": ld["t"],
            }
            row = pick_frame(rows, ld) if rows else None
            if row is None:
                rec["missing"] = True
                loads_out[ld["key"]].append(rec)
                continue
            rec.update(
                {
                    "frame": row["frame"],
                    "file": row.get("file"),
                    "t": row["t"],
                    "p_Pa": row["p_Pa"],
                    "lam_max": row["lam_max"],
                    "V_mL": row["V_mL"],
                    "Psi_J": row["Psi_J"],
                    "punch": row.get("punch"),
                }
            )
            dt = abs(float(row["t"]) - ld["t"])
            dp = abs(float(row["p_Pa"]) - ld["p_Pa"])
            rec["picked_by"] = "p"
            if dt > 0.0015 or dp > 200.0:
                rec["station_note"] = (
                    f"ANIM t={row['t']*1e3:.3g} ms p={row['p_Pa']:.0f} Pa "
                    f"(target t≈{ld['t_ms']} ms / {ld['p_Pa']:.0f} Pa)"
                )
                station_notes.append(f"{letter} {dens} {ld['key']}: {rec['station_note']}")
            vtk = vtk_for_row(run_dir, row) if pack is not None else None
            if vtk is not None and pack is not None:
                x, _cells, _t = field_from_vtk(vtk)
                field = lambda_field_stats(X, x, quads)
                rec["lam_aw_mean"] = field["lam_aw_mean"]
                rec["lam_p90"] = field["lam_p90"]
                rec["lambda_field"] = field
                if not args.no_stills:
                    hud = [
                        f"{letter}-{dens}  N={n}  {ld['label']}",
                        f"t={row['t']*1e3:.3g} ms  p={row['p_Pa']:.0f} Pa",
                        f"λ_max={row['lam_max']:.3f}  λ_aw={field['lam_aw_mean']:.3f}  V={row['V_mL']:.1f} mL",
                    ]
                    img = render_still(
                        x,
                        quads,
                        X,
                        cam_load,
                        hud,
                        size=640,
                        warn=row["lam_max"] >= 2.0,
                        warn_label=f"{ld['label']}  λ_max={row['lam_max']:.3f}",
                    )
                    img.save(stills / f"{dens}_{ld['key']}.png")
                    load_imgs[ld["key"]].append(img.copy())
                    load_labs[ld["key"]].append(f"{dens} {n}")
            else:
                w = deck / "artifacts" / "lambda_field.json"
                if w.exists() and abs(float(row["t"]) - 0.020) < 0.0015:
                    field = json.loads(w.read_text())
                    rec["lam_aw_mean"] = field.get("lam_aw_mean")
                    rec["lam_p90"] = field.get("lam_p90")
            loads_out[ld["key"]].append(rec)

    v0_s = f"{v0:.0f} mL" if v0 else "ship V0"
    if not args.no_stills and rest_imgs:
        concat_h(
            rest_imgs,
            rest_labs,
            f"Undeformed rest — letter {letter} nested ladder (same V0 ≈ {v0_s}, same camera)",
        ).save(stills / "rest_lineup.png")
    for ld in LOADS:
        if load_imgs[ld["key"]]:
            concat_h(
                load_imgs[ld["key"]],
                load_labs[ld["key"]],
                f"Letter {letter} same load {ld['label']} (t≈{ld['t_ms']} ms) — same camera",
            ).save(stills / f"{ld['key']}_lineup.png")

    pairs = {
        ld["key"]: grade_load(
            {r["density"]: r for r in loads_out[ld["key"]] if "lam_max" in r},
            ld,
            nested,
        )
        for ld in LOADS
    }

    session_forks = {}
    vanilla = root / "finest"
    if (vanilla / "run" / "Ainflate_0001.out").exists():
        vt = parse_timing(vanilla / "run")
        vt["rerun_this_session"] = "finest" in session
        vt["density"] = "finest-vanilla"
        vt["N"] = int((summary.get("finest") or {}).get("N") or 99456)
        vt["note"] = "STOP Tmin=1e-6 died at t=0 (nodal dt 9.74e-7). Mesh CFL, not a hang."
        session_forks["finest-vanilla"] = vt
        (vanilla / "artifacts").mkdir(parents=True, exist_ok=True)
        (vanilla / "artifacts" / "timing.json").write_text(json.dumps(vt, indent=2) + "\n")
    ams = root / "forks" / "finest-ams"
    if (ams / "run" / "Ainflate_0001.out").exists():
        at = parse_timing(ams / "run")
        at["rerun_this_session"] = True
        at["density"] = "finest-ams"
        at["N"] = int((summary.get("finest") or {}).get("N") or 99456)
        at["note"] = "Kareem /AMS Tmin=5e-6: ERROR TERMINATION, shells ruptured. Same μ/ρ. Hang guard still STOP."
        session_forks["finest-ams"] = at
        (ams / "artifacts").mkdir(parents=True, exist_ok=True)
        (ams / "artifacts" / "timing.json").write_text(json.dumps(at, indent=2) + "\n")
    forks_dir = root / "forks"
    if forks_dir.exists():
        for fork in sorted(forks_dir.iterdir()):
            if not fork.is_dir() or fork.name in session_forks:
                continue
            if not (fork / "run" / "Ainflate_0001.out").exists():
                continue
            ft = parse_timing(fork / "run")
            ft["rerun_this_session"] = True
            ft["density"] = fork.name
            parent = fork.name.split("-")[0]
            ft["N"] = int((summary.get(parent) or {}).get("N") or 0)
            note_p = fork / "FORK.md"
            ft["note"] = (
                note_p.read_text().splitlines()[0].lstrip("# ").strip()
                if note_p.exists()
                else fork.name
            )
            session_forks[fork.name] = ft
            (fork / "artifacts").mkdir(parents=True, exist_ok=True)
            (fork / "artifacts" / "timing.json").write_text(json.dumps(ft, indent=2) + "\n")
    for dens in nested:
        vanilla_d = root / dens
        used = resolve_deck(root, dens)
        key = f"{dens}-vanilla"
        if vanilla_d.resolve() != used.resolve() and (vanilla_d / "run" / "Ainflate_0001.out").exists():
            vt = parse_timing(vanilla_d / "run")
            vt["rerun_this_session"] = dens in session
            vt["density"] = key
            vt["N"] = int((summary.get(dens) or {}).get("N") or 0)
            vt["note"] = f"vanilla {dens} STOP 1e-6 (not the nested-grade row; see forks/)"
            session_forks[key] = vt

    note = (
        f"Letter {letter}. Grade at the same PLOAD, not first λ≥2. "
        "engine_elapsed_s is OpenRadioss ELAPSED TIME; post/contact-gap is not solve time. "
        "Peak λ_max at holes/creases is a sharp-hole singularity — do not chase with global refine. "
        "Volume / λ_aw is the useful signal."
    )
    if station_notes:
        note += " Frame stations: " + "; ".join(station_notes) + "."
    if letter == "A":
        note += (
            " Finer 24864 elapsed recovered from existing .out (not re-run this session). "
            "Finest working tape is forks/finest-stop5e7 (STOP Tmin=5e-7); vanilla 1e-6 CFL'd at t=0; /AMS ruptured."
        )
    payload = {
        "letter": letter,
        "nested": list(nested),
        "camera": {
            "az": AZ,
            "el": EL,
            "rest": {"cx": cam_rest[0], "cy": cam_rest[1], "span": cam_rest[2]},
            "load": {"cx": cam_load[0], "cy": cam_load[1], "span": cam_load[2]},
        },
        "timings": timings,
        "session_forks": session_forks,
        "loads": loads_out,
        "pairs": pairs,
        "station_notes": station_notes,
        "note": note,
        "gates": {"dV": DV_MAX, "dlam_max": DLAM_MAX, "dlam_aw": DAW_MAX},
    }
    (root / "same_load.json").write_text(json.dumps(payload, indent=2) + "\n")
    print("wrote", root / "same_load.json")
    for dens, t in timings.items():
        print(
            f"  {dens:7s} N={t['N']:5d}  engine={t['engine_elapsed_s']} s  "
            f"cycles={t['cycles']}  nt={t['threads']}  starter={t['starter_s']} s  "
            f"session_rerun={t['rerun_this_session']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
