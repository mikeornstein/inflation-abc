#!/usr/bin/env python3
"""Same-load A-refine grading (Mike): strain at fixed p, not first λ≥2.

Loads:
  ~32.5 kPa  (t≈20 ms, ANIM frame 10)
  ~35.8 kPa  (t≈22 ms, ANIM frame 11)

Nested family only: ship / fine / finer / finest (same rest letter, V0≈354 mL).
Wall-clock = OpenRadioss ELAPSED TIME from the engine .out (not Python post).
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
    }
    eng = run_dir / "Ainflate_0001.out"
    if not eng.exists():
        return out
    txt = eng.read_text(errors="replace")
    out["source"] = "Ainflate_0001.out"
    m = re.search(r"ELAPSED TIME\s*=\s*([0-9.]+)\s*s", txt)
    if m:
        out["engine_elapsed_s"] = float(m.group(1))
    m = re.search(r"TOTAL NUMBER OF CYCLES\s*:\s*(\d+)", txt)
    if m:
        out["cycles"] = int(m.group(1))
    m = re.search(r"NUMBER OF THREADS PER DOMAIN\s+(\d+)", txt)
    if m:
        out["threads"] = int(m.group(1))
    m = re.search(r"STARTER RUNTIME\s*=\s*([0-9.]+)\s*s", txt)
    if m:
        out["starter_s"] = float(m.group(1))
    m = re.search(r"STARTER\+ENGINE RUNTIME\s*=\s*([0-9.]+)\s*s", txt)
    if m:
        out["starter_plus_engine_s"] = float(m.group(1))
    out["source"] = "Ainflate_0001.out (prior tape; not re-run this session)"
    return out


def pick_frame(rows: list[dict], t_target: float) -> dict | None:
    if not rows:
        return None
    return min(rows, key=lambda r: abs(float(r["t"]) - t_target))


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


def locked_camera(root: Path) -> tuple[float, float, float]:
    """Same (cx, cy, span) in projected XY for rest + 35.8 kPa stills."""
    pts = []
    ship = json.loads((root / "meshes" / "A-ship.json").read_text())
    pos = np.asarray(ship["pos0"], dtype=float).reshape(-1, 3)
    pts.extend(pos)
    fine_run = root / "fine" / "run"
    # frame 11 file is typically Ainflate_A012.vtk
    cand = fine_run / "Ainflate_A012.vtk"
    if cand.exists():
        x, _, _ = parse_vtk(cand)
        pts.extend(np.asarray(x, dtype=float))
    xy = np.asarray([project(p) for p in pts], dtype=float)
    xmin, ymin = xy.min(0)
    xmax, ymax = xy.max(0)
    span = max(xmax - xmin, ymax - ymin, 1e-6) * 1.22
    cx, cy = 0.5 * (xmin + xmax), 0.5 * (ymin + ymax)
    return float(cx), float(cy), float(span)


def render_still(x, quads, X, camera, hud, *, rest=False, size=720, warn=False, warn_label=""):
    nq = len(quads)
    lams = np.ones(nq) if rest else quad_lams(X, x, quads)
    return render_frame(
        x,
        quads,
        lams,
        hud,
        size=size,
        warn=warn,
        camera=camera,
        draw_edges=nq <= 8000,
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


def grade_load(rows_by_dens: dict, load: dict) -> list[dict]:
    order = [d for d in NESTED if d in rows_by_dens]
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
    camera = locked_camera(root)
    (root / "camera.json").write_text(
        json.dumps({"cx": camera[0], "cy": camera[1], "span": camera[2], "az": AZ, "el": EL}, indent=2)
        + "\n"
    )

    summary = json.loads((root / "mesh-summary.json").read_text()) if (root / "mesh-summary.json").exists() else {}
    session = set(args.session_rerun)

    timings = {}
    loads_out = {ld["key"]: [] for ld in LOADS}
    rest_imgs = []
    rest_labs = []
    load_imgs = {ld["key"]: [] for ld in LOADS}
    load_labs = {ld["key"]: [] for ld in LOADS}

    for dens in NESTED:
        deck = root / dens
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
            # rest still
            if not args.no_stills:
                hud = [f"{dens}  N={n}  rest", f"V0 ≈ {(summary.get(dens) or {}).get('V0_mL', 354):.0f} mL  /ADYREL"]
                img = render_still(X, quads, X, camera, hud, rest=True, size=640)
                img.save(stills / f"{dens}_rest.png")
                rest_imgs.append(img.copy())
                rest_labs.append(f"{dens} {n}")

        for ld in LOADS:
            rec = {
                "density": dens,
                "N": n,
                "load": ld["key"],
                "p_target_Pa": ld["p_Pa"],
            }
            row = pick_frame(rows, ld["t"]) if rows else None
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
            vtk = vtk_for_row(run_dir, row) if pack is not None else None
            if vtk is not None and pack is not None:
                x, _cells, _t = field_from_vtk(vtk)
                field = lambda_field_stats(X, x, quads)
                rec["lam_aw_mean"] = field["lam_aw_mean"]
                rec["lam_p90"] = field["lam_p90"]
                rec["lambda_field"] = field
                if not args.no_stills:
                    hud = [
                        f"{dens}  N={n}  {ld['label']}",
                        f"t={row['t']*1e3:.3g} ms  p={row['p_Pa']:.0f} Pa",
                        f"λ_max={row['lam_max']:.3f}  λ_aw={field['lam_aw_mean']:.3f}  V={row['V_mL']:.1f} mL",
                    ]
                    img = render_still(
                        x,
                        quads,
                        X,
                        camera,
                        hud,
                        size=640,
                        warn=row["lam_max"] >= 2.0,
                        warn_label=f"{ld['label']}  λ_max={row['lam_max']:.3f}",
                    )
                    img.save(stills / f"{dens}_{ld['key']}.png")
                    load_imgs[ld["key"]].append(img.copy())
                    load_labs[ld["key"]].append(f"{dens} {n}")
            else:
                # fall back to warn-frame field if this is the warn load
                w = deck / "artifacts" / "lambda_field.json"
                if w.exists() and abs(float(row["t"]) - 0.020) < 0.0015:
                    field = json.loads(w.read_text())
                    rec["lam_aw_mean"] = field.get("lam_aw_mean")
                    rec["lam_p90"] = field.get("lam_p90")
            loads_out[ld["key"]].append(rec)

    if not args.no_stills and rest_imgs:
        concat_h(
            rest_imgs,
            rest_labs,
            "Undeformed rest — nested refine ladder (same V0 ≈ 354 mL, same camera)",
        ).save(stills / "rest_lineup.png")
    for ld in LOADS:
        if load_imgs[ld["key"]]:
            concat_h(
                load_imgs[ld["key"]],
                load_labs[ld["key"]],
                f"Same load {ld['label']} (t≈{ld['t_ms']} ms) — same camera",
            ).save(stills / f"{ld['key']}_lineup.png")

    pairs = {ld["key"]: grade_load({r["density"]: r for r in loads_out[ld["key"]] if "lam_max" in r}, ld) for ld in LOADS}

    payload = {
        "camera": {"cx": camera[0], "cy": camera[1], "span": camera[2], "az": AZ, "el": EL},
        "timings": timings,
        "loads": loads_out,
        "pairs": pairs,
        "note": (
            "Grade at the same PLOAD, not first λ≥2. "
            "engine_elapsed_s is OpenRadioss ELAPSED TIME; post/contact-gap is not solve time. "
            "Finer 24864 elapsed recovered from existing .out unless listed in session-rerun."
        ),
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
