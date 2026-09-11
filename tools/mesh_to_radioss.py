#!/usr/bin/env python3
"""Convert Inflation ABC bake JSON (meshes/A.json) to an OpenRadioss deck.

Physics-first first light:
  /PROP/SHELL  N=1  Ismstr=10  (Belytschko; QEPH ruptured at rest)
  /MAT/LAW42   μ1=MU  α1=2  other μp/αp=0  ν=0.495  Prony M=0
  /INTER/TYPE19 self-contact, Gapmin = CONTACT_KISS (do not soften)
  /PLOAD ramp  (not MONVOL)
  all-quad /SHELL (orphan faceTris paired; no /SH3N in the inflate part)
  free-free: no /BCS; engine /ADYREL + starter /DAMP

SI units. Does not touch the web-mbd JS neo-Hookean path.
Does not remesh the midplane (ship A.json nMidTris=0).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.request
from pathlib import Path

_TOOLS = Path(__file__).resolve().parent
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

from radioss_law import (
    ALPHA1,
    CONTACT_KISS,
    H0,
    MU,
    MU_LABEL,
    NU,
    PRONY_M,
    RHO,
    RHO_LABEL,
    WARN_LAM,
    law_card_lines,
)

MESH_URL = "https://raw.githubusercontent.com/mikeornstein/inflation-abc/main/meshes/A.json"

# Load path (not a constitutive retune). JS warn ~54100 Pa; ramp past that
# so first λ≥2 is on the tape if the explicit film reaches it.
P_MAX = 65000.0
T_RAMP = 0.040
T_END = 0.050
ANIM_DT = 0.002
DAMP_ALPHA = 80.0  # 1/s  Rayleigh mass-proportional; ρ unchanged

RUNNAME = "Ainflate"
PART_QUAD = 1
PROP_ID = 1
MAT_ID = 1
SURF_ID = 1
FUNCT_P = 1
GRNOD_ALL = 1


def i10(v: int = 0) -> str:
    return f"{int(v):10d}"


def r20(v: float = 0.0) -> str:
    if v == 0.0:
        return f"{0.0:20.1f}"
    return f"{float(v):20.12G}"


def i10s(vals) -> str:
    lines = []
    row = []
    for v in vals:
        row.append(i10(v))
        if len(row) == 10:
            lines.append("".join(row))
            row = []
    if row:
        lines.append("".join(row))
    return "\n".join(lines) + ("\n" if lines else "")


def header_bar() -> str:
    return "#---1----|----2----|----3----|----4----|----5----|----6----|----7----|----8----|----9----|---10----|\n"


def load_mesh(path: Path) -> dict:
    with path.open() as f:
        data = json.load(f)
    pos = data["pos0"]
    n = len(pos) // 3
    meta = data.get("meta") or {}
    if n != int(meta.get("N", n)):
        raise SystemExit(f"pos0/N mismatch: {n} vs meta.N={meta.get('N')}")
    quads = data.get("quads") or []
    orphans = data.get("faceTris") or []
    if not quads:
        raise SystemExit("mesh has no quads")
    return {
        "n": n,
        "pos": pos,
        "quads": quads,
        "orphans": orphans,
        "meta": meta,
        "elemType": data.get("elemType"),
    }


def node_xyz(pos, i: int):
    return pos[3 * i], pos[3 * i + 1], pos[3 * i + 2]


def _merge_tri_pair(t1, t2, shared):
    """Two tris sharing `shared` (sorted pair) → one quad. Keep t1 winding."""
    t1 = [int(i) for i in t1]
    t2 = [int(i) for i in t2]
    sh = set(int(i) for i in shared)
    u1 = next(v for v in t1 if v not in sh)
    u2 = next(v for v in t2 if v not in sh)
    i = t1.index(u1)
    n1, n2 = t1[(i + 1) % 3], t1[(i + 2) % 3]
    return (u1, n1, u2, n2)


def quadify_orphans(quads, orphans):
    """Pair orphan faceTris that share an edge into quads.

    Does not remesh existing quads (midplane stays quad). Ship A.json
    nMidTris=0; the 28 faceTris are cap orphans and pair 1:1 into 14 quads.
    Returns (all_quads, leftover_tris). leftover must be empty for A inflate.
    """
    all_quads = [tuple(int(i) for i in q) for q in quads]
    if not orphans:
        return all_quads, []
    from collections import defaultdict

    edges = defaultdict(list)
    tris = [tuple(int(i) for i in t) for t in orphans]
    for ti, t in enumerate(tris):
        if len(t) != 3:
            raise SystemExit(f"orphan faceTri {ti} is not a triangle: {t}")
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
        extra.append(_merge_tri_pair(tris[a], tris[b], e))
    leftover = [tris[i] for i in range(len(tris)) if i not in used]
    return all_quads + extra, leftover


def enclosed_volume(pos, quads, orphans) -> float:
    def tri_vol(a, b, c):
        return (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            + a[1] * (b[2] * c[0] - b[0] * c[2])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6.0

    v = 0.0
    for q in quads:
        a, b, c, d = (node_xyz(pos, i) for i in q)
        v += tri_vol(a, b, c) + tri_vol(a, c, d)
    for t in orphans:
        a, b, c = (node_xyz(pos, i) for i in t)
        v += tri_vol(a, b, c)
    return v


def write_starter(mesh: dict, out: Path) -> dict:
    n = mesh["n"]
    pos = mesh["pos"]
    src_quads = mesh["quads"]
    src_orphans = mesh["orphans"]
    quads, leftover = quadify_orphans(src_quads, src_orphans)
    if leftover:
        raise SystemExit(
            f"quadify left {len(leftover)} unpaired tris — refuse /SH3N in inflate part"
        )
    vol0 = enclosed_volume(pos, src_quads, src_orphans)
    vol_q = enclosed_volume(pos, quads, [])
    if abs(vol_q - vol0) > 1e-12 * max(abs(vol0), 1e-12):
        raise SystemExit(f"quadify changed V0: {vol0} → {vol_q}")
    info = {
        "n": n,
        "nquads": len(quads),
        "nquads_src": len(src_quads),
        "norphans_src": len(src_orphans),
        "norphans": 0,
        "nsh3n": 0,
        "bcs": None,
        "ir": "/ADYREL + /DAMP (free-free; no /BCS)",
        "V0_m3": vol0,
        "MU": MU,
        "H0": H0,
        "RHO": RHO,
        "NU": NU,
        "Gapmin": CONTACT_KISS,
        "P_MAX": P_MAX,
        "T_END": T_END,
        "T_RAMP": T_RAMP,
    }

    lines = []
    w = lines.append
    w("#RADIOSS STARTER\n")
    w(header_bar())
    w("# Inflation ABC letter A — OpenRadioss first light\n")
    w("# SI: kg, m, s, Pa. Do not retune μ or ρ.\n")
    for ln in law_card_lines():
        w(f"# {ln}\n")
    w(
        f"# Mesh {n} nodes, {len(quads)} /SHELL quads "
        f"(source {len(src_quads)} quads + {len(src_orphans)} orphan faceTris paired; SH3N=0)\n"
    )
    w("# Midplane not remeshed (ship A.json nMidTris=0). Cap orphans quadified only.\n")
    w(f"# Rest enclosed volume V0 = {vol0:.8g} m^3 ({vol0*1e6:.4g} mL)\n")
    w("# Free-free: no /BCS. OpenRadioss explicit inertial-relief analogue = /ADYREL (engine)\n")
    w("#   + /DAMP Rayleigh mass (starter). Radioss has no PARAM,INREL (that is OptiStruct).\n")
    w("#   Closed /PLOAD is self-equilibrated (net F≈0); /ADYREL+/DAMP kill residual RB drift.\n")
    w(f"# PLOAD ramp 0 → {P_MAX:g} Pa in {T_RAMP}s, hold to {T_END}s (not MONVOL)\n")
    w(header_bar())
    w("/BEGIN\n")
    w(f"{RUNNAME}\n")
    w(f"{i10(2024)}\n")
    w(f"{'kg':>20}{'m':>20}{'s':>20}\n")
    w(f"{'kg':>20}{'m':>20}{'s':>20}\n")
    w("/TITLE\n")
    w("Inflation ABC A — LAW42 NH /PLOAD first light (same μ, ρ=1130)\n")

    w(header_bar())
    w("/DEF_SHELL\n")
    w("#    Ishell    Ismstr    Ithick     Iplas   Istrain   Ioffset               ISH3N    Idrill\n")
    # 2024: 6 ints, 10 blanks, Ish3n, Idrill. Istrain=1 for ANIM strain.
    w(i10(24) + i10(0) + i10(1) + i10(0) + i10(1) + i10(2) + "          " + i10(2) + i10(1) + "\n")

    w(header_bar())
    w(f"/MAT/LAW42/{MAT_ID}\n")
    w("Desmopan 85085A NH film; McMaster 1446T11 density not published\n")
    w("#              RHO_I\n")
    w(r20(RHO) + "\n")
    w("#                 Nu           sigma_cut           funIDbulk         Fscale_bulk         M     Iform\n")
    w(r20(NU) + r20(0.0) + r20(0.0) + r20(0.0) + i10(PRONY_M) + i10(1) + "\n")
    w("#               Mu_1                Mu_2                Mu_3                Mu_4                Mu_5\n")
    w(r20(MU) + r20(0.0) + r20(0.0) + r20(0.0) + r20(0.0) + "\n")
    w("#               Mu_6                Mu_7                Mu_8                Mu_9               Mu_10\n")
    w(r20(0.0) + r20(0.0) + r20(0.0) + r20(0.0) + r20(0.0) + "\n")
    w("#            alpha_1             alpha_2             alpha_3             alpha_4             alpha_5\n")
    w(r20(ALPHA1) + r20(0.0) + r20(0.0) + r20(0.0) + r20(0.0) + "\n")
    w("#            alpha_6             alpha_7             alpha_8             alpha_9            alpha_10\n")
    w(r20(0.0) + r20(0.0) + r20(0.0) + r20(0.0) + r20(0.0) + "\n")

    w(header_bar())
    w(f"/PROP/SHELL/{PROP_ID}\n")
    w("film membrane N=1 Ismstr=10 QEPH Ithick=1\n")
    w("#    Ishell    Ismstr     Ish3n    Idrill    Ipinch                  P_Thick_Fail\n")
    # QEPH(24)+Ismstr=10 ruptured at rest (no PLOAD). Belytschko Ismstr=10 N=1 is stable.
    w(i10(1) + i10(10) + i10(2) + i10(1) + i10(0) + "          " + r20(0.0) + "\n")
    w("#                 Hm                  Hf                  Hr                  Dm                  Dn\n")
    w(r20(0.0) + r20(0.0) + r20(0.0) + r20(0.05) + r20(0.0) + "\n")
    w("#         N                         Thick              Ashear              Ithick     Iplas      Ipos\n")
    w(i10(1) + "          " + r20(H0) + r20(0.0) + "          " + i10(1) + i10(0) + i10(0) + "\n")

    w(header_bar())
    w(f"/PART/{PART_QUAD}\n")
    w(f"letter A all-quad film ({len(quads)} shells; SH3N=0)\n")
    w(i10(PROP_ID) + i10(MAT_ID) + i10(0) + "\n")

    w(header_bar())
    w("/NODE\n")
    for i in range(n):
        x, y, z = node_xyz(pos, i)
        w(i10(i + 1) + r20(x) + r20(y) + r20(z) + "\n")

    w(header_bar())
    w(f"/SHELL/{PART_QUAD}\n")
    for e, q in enumerate(quads, start=1):
        n1, n2, n3, n4 = (int(q[0]) + 1, int(q[1]) + 1, int(q[2]) + 1, int(q[3]) + 1)
        if n4 == n3:
            raise SystemExit(f"degenerate quad (would bleed as tri) elem {e}: {q}")
        w(i10(e) + i10(n1) + i10(n2) + i10(n3) + i10(n4) + "\n")

    w(header_bar())
    w(f"/GRNOD/PART/{GRNOD_ALL}\n")
    w("all film nodes (free-free; no 3-2-1 pins)\n")
    w(i10(PART_QUAD) + "\n")

    w(header_bar())
    w("/DAMP/1\n")
    w("Rayleigh mass damping (rho unchanged); free-free RB sink with engine /ADYREL\n")
    w(r20(DAMP_ALPHA) + r20(0.0) + i10(GRNOD_ALL) + i10(0) + r20(0.0) + r20(1e30) + "\n")

    w(header_bar())
    w(f"/SURF/PART/{SURF_ID}\n")
    w("closed all-quad film; outward normals; +PLOAD inflates\n")
    w(i10(PART_QUAD) + "\n")

    w(header_bar())
    w("/INTER/TYPE19/1\n")
    w(f"self-contact kiss Gapmin={CONTACT_KISS:.8g} m (=CONTACT_KISS, not puffy)\n")
    # surf_s surf_m Istf Ithe Igap Iedge Ibag Idel Icurv
    # Ibag=0 (no MONVOL). Iedge=2 all segment edges. Igap=1000 → gap=Gapmin.
    w(i10(SURF_ID) + i10(0) + i10(5) + i10(0) + i10(4) + i10(2) + i10(0) + i10(1000) + i10(0) + "\n")
    w("#          Fscalegap               Gapmax      Edge_scale_gap\n")
    w(r20(1.0) + r20(0.0) + r20(1.0) + "\n")
    w("#             Stmin                Stmax           mesh_size                dtmin  Irem_gap   Irem_i2\n")
    w(r20(0.0) + r20(0.0) + r20(0.4) + r20(1.0e-6) + i10(2) + i10(2) + "\n")
    w("#              Stfac                 Fric               Gapmin               Tstart                Tstop\n")
    w(r20(1.0) + r20(0.1) + r20(CONTACT_KISS) + r20(0.0) + r20(1e30) + "\n")
    w("#      IBC                        Inacti                VISs                VISf              Bumult\n")
    # 2024: 7 blanks + XYZ flags + 10 blank + 10 blank + Inacti(10) + VISs + VISf + Bumult
    w("       " + "000" + "          " + "          " + i10(6) + r20(0.05) + r20(1.0) + r20(0.20) + "\n")
    w("#     Ifric    Ifiltr               Xfreq     Iform   sens_ID                                 fric_ID\n")
    w(i10(0) + i10(0) + r20(0.0) + i10(1) + i10(0) + "          " * 3 + i10(0) + "\n")

    w(header_bar())
    w(f"/FUNCT/{FUNCT_P}\n")
    w(f"PLOAD ramp 0-1 over {T_RAMP}s then hold; Fscale={P_MAX:g} Pa\n")
    w(r20(0.0) + r20(0.0) + "\n")
    w(r20(T_RAMP) + r20(1.0) + "\n")
    w(r20(T_END) + r20(1.0) + "\n")
    w(r20(T_END + 1.0) + r20(1.0) + "\n")

    w(header_bar())
    w("/PLOAD/1\n")
    w("internal pressure on film (positive = outward / inflate)\n")
    w(i10(SURF_ID) + i10(FUNCT_P) + i10(0) + i10(0) + i10(1) + i10(0) + r20(1.0) + r20(P_MAX) + "\n")

    w(header_bar())
    w("# Time history: variables before object IDs (Radioss /TH). λ,V,Ψ from ANIM/VTK.\n")
    w("/TH/PART/1\n")
    w("part energy\n")
    w("DEF\n")
    w(i10(PART_QUAD) + "\n")
    w("/TH/INTER/1\n")
    w("TYPE19 contact\n")
    w("DEF\n")
    w(i10(1) + "\n")

    w(header_bar())
    w("/END\n")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(lines))
    return info


def write_engine(out: Path) -> None:
    lines = []
    w = lines.append
    w("#RADIOSS ENGINE\n")
    w(header_bar())
    w(f"/RUN/{RUNNAME}/1\n")
    w(r20(T_END).strip() + "\n" if False else f"{T_END:g}\n")
    w("/TFILE\n")
    w("0.001\n")
    w("/ANIM/DT\n")
    w(f"0.0 {ANIM_DT:g}\n")
    w("/ANIM/VECT/DISP\n")
    w("/ANIM/VECT/CONT\n")
    w("/ANIM/ELEM/ENER\n")
    w("/ANIM/ELEM/HOURG\n")
    w("/ANIM/SHELL/THIC\n")
    w("/ANIM/SHELL/TENS/STRAIN/MEMB\n")
    w("/PRINT/-200\n")
    w("/DT\n")
    w("0.9 0.0\n")
    w("/DT/NODA/CST\n")
    w("0.9 1.0e-6\n")
    w("# Free-free / inertial relief analogue (no /BCS pins).\n")
    w("# /ADYREL = adaptive dynamic relaxation (OpenRadioss engine).\n")
    w("# Radioss has no PARAM,INREL — that keyword is OptiStruct only.\n")
    w("/ADYREL\n")
    w("/END\n")
    out.write_text("".join(lines))


def write_law_card(path: Path, info: dict) -> None:
    lines = law_card_lines() + [
        "",
        "Contact / load",
        "  /INTER/TYPE19 self-contact  Igap=4 (var gap + neighbor skip)  Irem_gap=2  Inacti=6  dtmin=1e-6",
        f"  Gapmin  = {CONTACT_KISS:.16g} m",
        f"  /PLOAD  0 → {P_MAX:g} Pa in {T_RAMP}s, hold to {T_END}s",
        f"  /PROP   N=1  Ismstr=10  Ishell=1 (Belytschko; QEPH ruptured at rest)  Ithick=1  Thick=H0",
        "  /BCS    none (3-2-1 pins dropped)",
        "  IR      /ADYREL (engine) + /DAMP Rayleigh α=80 1/s (starter) — explicit free-free",
        "          OpenRadioss has no PARAM,INREL (OptiStruct). Closed /PLOAD is self-equilibrated.",
        f"  V0      = {info['V0_m3']:.8g} m^3",
        f"  mesh    = N={info['n']}  /SHELL={info['nquads']}  /SH3N=0  "
        f"(source quads={info['nquads_src']} orphan faceTris={info['norphans_src']} paired)",
    ]
    path.write_text("\n".join(lines) + "\n")


def fetch_mesh(dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"fetching {MESH_URL}")
    with urllib.request.urlopen(MESH_URL, timeout=60) as r:
        dest.write_bytes(r.read())


def main(argv=None) -> int:
    here = Path(__file__).resolve().parent
    repo = here.parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mesh", type=Path, default=repo / "meshes" / "A.json")
    ap.add_argument("--out-dir", type=Path, default=repo / "radioss" / "A-inflate")
    ap.add_argument("--fetch", action="store_true", help="download A.json if missing")
    ap.add_argument("--check", action="store_true", help="validate counts and exit after write")
    args = ap.parse_args(argv)

    if args.fetch or not args.mesh.exists():
        fetch_mesh(args.mesh)
    mesh = load_mesh(args.mesh)
    n, nq, nt = mesh["n"], len(mesh["quads"]), len(mesh["orphans"])
    print(f"mesh {args.mesh}: N={n} source_quads={nq} orphan_tris={nt} type={mesh['elemType']}")
    if n != 1554 or nq != 1540 or nt != 28:
        print(
            f"WARNING: expected ship A N=1554 / 1540 quads / 28 orphan tris; got {n}/{nq}/{nt}",
            file=sys.stderr,
        )

    starter = args.out_dir / f"{RUNNAME}_0000.rad"
    engine = args.out_dir / f"{RUNNAME}_0001.rad"
    info = write_starter(mesh, starter)
    write_engine(engine)
    write_law_card(args.out_dir / "law-card.txt", info)
    print(f"wrote {starter}")
    print(f"wrote {engine}")
    print(f"μ1={MU:.8g} α1={ALPHA1} H0={H0:.8g} ν={NU} ρ={RHO} Gapmin={CONTACT_KISS:.8g}")
    print(f"deck /SHELL={info['nquads']} /SH3N=0  IR={info['ir']}")
    print(f"V0={info['V0_m3']*1e6:.4g} mL")
    if args.check:
        text = starter.read_text()
        eng = engine.read_text()
        assert text.count("\n") > n, "starter too small"
        assert f"/SHELL/{PART_QUAD}" in text
        assert not any(ln.startswith("/SH3N") for ln in text.splitlines()), "inflate part must be quad-only"
        assert not any(ln.startswith("/BCS") for ln in text.splitlines()), "no 3-2-1 pins"
        assert "/ADYREL" in eng, "engine must use /ADYREL free-free"
        assert not any(ln.startswith("/DYREL") for ln in eng.splitlines())
        assert "/MAT/LAW42/" in text
        assert "/INTER/TYPE19/" in text
        assert "/PLOAD/" in text
        assert "/MONVOL" not in text
        assert "/DAMP/" in text
        assert info["nquads"] == 1554, info["nquads"]
        assert info["nsh3n"] == 0
        assert abs(MU - (800.0 * 6894.757) / 1.75) < 1e-6
        assert RHO == 1130.0
        print("check ok")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
