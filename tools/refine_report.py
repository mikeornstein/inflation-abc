#!/usr/bin/env python3
"""Chiron/Themis locked mesh-convergence report for radioss/{A,B,C}-refine.

At first λ_max≥2 on each N (quad + /ADYREL deck only):
  report p, λ_max, V, Ψ
  same μ/ρ; load law fixed; label dynamic until QS-ish
  successive ~2× denser N: Δp≤5%, ΔV≤5%, Δλ_max≤2%, and λ_max in [2.0, 2.35]
  Ψ≥0; contact viol/gap report-only
  CFL before λ≥2 → /AMS or slower PLOAD fork (Kareem), not NODA/CST
  converged dynamic ≠ ABC apples claim
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

LAM_LO, LAM_HI = 2.0, 2.35
DP_MAX = 0.05
DV_MAX = 0.05
DLAM_MAX = 0.02
MU = (800.0 * 6894.757) / 1.75
RHO = 1130.0

DENSITIES = ("coarse", "ship", "fine", "finer", "finest")
NESTED = ("ship", "fine", "finer", "finest")

from refine_same_load import letter_of, nested_present, resolve_deck  # noqa: E402  (after constants; no cycle)


def rel(a, b) -> float:
    den = abs(b) if abs(b) > 1e-30 else 1e-30
    return abs(a - b) / den


def load_warn(deck: Path) -> dict | None:
    p = deck / "artifacts" / "warn.json"
    if not p.exists():
        return None
    return json.loads(p.read_text())


def pair_verdict(coarser: dict, finer: dict, name_c: str, name_f: str) -> dict:
    pc, pf = coarser["p_Pa"], finer["p_Pa"]
    vc, vf = coarser["V_mL"], finer["V_mL"]
    lc, lf = coarser["lam_max"], finer["lam_max"]
    dp, dv, dl = rel(pf, pc), rel(vf, vc), rel(lf, lc)
    lam_ok = (LAM_LO <= lc <= LAM_HI) and (LAM_LO <= lf <= LAM_HI)
    psi_ok = coarser["Psi_J"] >= -1e-8 and finer["Psi_J"] >= -1e-8
    gates = {
        "dp": dp,
        "dv": dv,
        "dlam": dl,
        "dp_ok": dp <= DP_MAX,
        "dv_ok": dv <= DV_MAX,
        "dlam_ok": dl <= DLAM_MAX,
        "lam_band_ok": lam_ok,
        "psi_ok": psi_ok,
    }
    gates["pass"] = all(
        gates[k] for k in ("dp_ok", "dv_ok", "dlam_ok", "lam_band_ok", "psi_ok")
    )
    gates["pair"] = f"{name_c}→{name_f}"
    return gates


def fork_lines(rows: list[dict]) -> list[str]:
    cfl = [r for r in rows if r.get("cfl_before_lambda2")]
    ams = [r for r in rows if r.get("ams")]
    late = [r for r in rows if r.get("cfl_after_lambda2")]
    pending = [r for r in rows if not r.get("reached_lambda2") and not r.get("cfl_before_lambda2")]
    if cfl:
        names = ", ".join(r["density"] for r in cfl)
        return [
            f"CFL `/DT/NODA/STOP` before λ≥2 on: **{names}**. "
            "Kareem fork: `/AMS` or slower PLOAD (not NODA/CST). Ishell=1; μ/ρ locked.",
        ]
    if pending:
        names = ", ".join(r["density"] for r in pending)
        return [
            f"No Kareem fork armed. Pending λ≥2 tape: **{names}**. "
            "Hang guard remains STOP (not NODA/CST).",
        ]
    if late:
        names = ", ".join(r["density"] for r in late)
        return [
            f"CFL `/DT/NODA/STOP` **after** first λ≥2 on: **{names}** "
            "(metric frame is valid; no Kareem fork — lock only forks if CFL dies before λ≥2). "
            "Hang guard remains STOP (not NODA/CST). Ishell=1; μ/ρ locked.",
        ]
    if ams:
        names = ", ".join(r["density"] for r in ams)
        return [
            f"`/AMS` armed on: **{names}** (Kareem CFL fork). Hang guard remains STOP (not NODA/CST).",
        ]
    return [
        "No Kareem fork on this tape: every density reached λ≥2 **before** `/DT/NODA/STOP`. "
        "`/AMS` / slower PLOAD not armed. Hang guard remains STOP (not NODA/CST).",
    ]


def fmt_timing(t: dict) -> str:
    if not t or t.get("engine_elapsed_s") is None:
        return "—"
    el = t["engine_elapsed_s"]
    st = t.get("starter_s")
    cyc = t.get("cycles")
    nt = t.get("threads")
    tag = "this session" if t.get("rerun_this_session") else "from .out (not re-run)"
    st_s = f"{st:.2f}s" if st is not None else "—"
    return f"{el:.2f}s engine / {st_s} starter / {cyc} cyc / {nt} thr ({tag})"


def write_refine_md(
    out: Path,
    rows: list[dict],
    pairs: list[dict],
    verdict: str,
    same_load: dict | None = None,
    *,
    letter: str = "A",
    nested: tuple[str, ...] = NESTED,
) -> None:
    lines = [
        f"# {letter}-refine — mesh convergence (Chiron/Themis lock)",
        "",
        f"Quad-only `/SHELL` + free-free `/ADYREL` OpenRadioss {letter} inflate. "
        "**Not** the old tri/`SH3N` + 3-2-1 `/BCS` deck. "
        "μ and ρ are locked; load law is **fixed** across the ladder. "
        "This deck is the **Quality PASS desk** (p@λ≥2 still **dynamic** — "
        "NOT-YET apples vs ABC/Chiron QS).",
        "",
        "## Locked law (never retuned)",
        "",
        f"- μ₁ = `(800 * 6894.757) / 1.75` = {MU:.8g} Pa · α₁=2",
        f"- ρ = **{RHO:g} kg/m³** (Desmopan 85085A ISO 1183-1)",
        "- H0 = 0.015×0.0254 m · Gapmin = CONTACT_KISS = 2·H0",
        "- `/PROP` Ishell=**1** (Belytschko) N=1 Ismstr=10 · no `/SH3N` · no `/BCS`",
        "- `/PLOAD` 0→65 kPa in 0.04 s (same ramp on every density unless a labeled fork)",
        "- Hang guard is **`/DT/NODA/STOP`** (not CST). If CFL dies before λ≥2, `/AMS` once; "
        "if AMS ruptures the film, drop AMS and lower STOP Tmin only enough to run.",
        "",
        "## Metrics lock (2026-09-11 / same-load 2026-09-12)",
        "",
        "Treat as `briefs/2026-09-11-openradioss-mesh-convergence-metrics.md`.",
        "",
        "At **first λ_max ≥ 2** on each mesh N (historical crossing, not the grade):",
        "",
        "- Report **p, λ_max, V, Ψ**",
        "- Mike (2026-09-12): **grade at the same load**, not first λ≥2. "
        "Same p → same strain/deformation. Peak stretch at the hole/creases is the climbing quantity.",
        "- Same-load stations: **~32.5 kPa** (t≈20 ms) and **~35.8 kPa** (t≈22 ms). "
        "If ANIM frames differ, pick the frames whose **p** matches those loads.",
        "- Successive nested N: **ΔV ≤ 5%**, **Δλ_max ≤ 2%**, **Δλ_aw ≤ 2%**",
        "- λ_max stays in **[2.0, 2.35]** at that frame",
        "- Ψ ≥ 0 required; contact viol / gap is **report-only**",
        "- If CFL dies before λ≥2: **/AMS or slower PLOAD** fork (Kareem) — not NODA/CST; Ishell=1; no μ/ρ retune",
        "- Peak λ_max climbing at holes/creases is a **sharp-hole singularity** in the geometry input "
        "(real creases have a small radius). Do **not** chase λ_max with more global refine. "
        "Volume / λ_aw settling is the useful signal. Do not declare mesh-failed just because λ_max climbs.",
        "- **Converged dynamic ≠ ABC apples claim** vs Chiron QS (~54 kPa)",
        "",
        "## Ladder",
        "",
        "| density | N | /SHELL | plan |",
        "|---------|--:|-------:|------|",
    ]
    for r in rows:
        lines.append(
            f"| {r['density']} | {r['N']} | {r.get('n_quads', r['N'])} | {r.get('plan', '')} |"
        )
    if same_load and same_load.get("timings"):
        lines += [
            "",
            "## Wall-clock (OpenRadioss ELAPSED TIME — not Python post)",
            "",
            "Solve time is starter + engine from `Ainflate_0001.out`. "
            "Contact-gap / GIF post is **not** in this column. OMP threads = 4 unless noted.",
            "",
            "| density | N | engine ELAPSED | starter | cycles | threads | timed |",
            "|---------|--:|---------------:|--------:|-------:|--------:|-------|",
        ]
        for dens in nested:
            t = (same_load.get("timings") or {}).get(dens)
            if not t:
                continue
            el = t.get("engine_elapsed_s")
            st = t.get("starter_s")
            lines.append(
                f"| {dens} | {t.get('N', '')} | "
                f"{'—' if el is None else f'{el:.2f} s'} | "
                f"{'—' if st is None else f'{st:.2f} s'} | "
                f"{t.get('cycles') if t.get('cycles') is not None else '—'} | {t.get('threads') or '—'} | "
                f"{'this session' if t.get('rerun_this_session') else 'from existing .out'} |"
            )
        forks = same_load.get("session_forks") or {}
        if forks:
            lines += [
                "",
                "Session forks (same μ/ρ; not nested-grade rows):",
                "",
                "| fork | engine ELAPSED | starter | cycles | threads | note |",
                "|------|---------------:|--------:|-------:|--------:|------|",
            ]
            for name, t in forks.items():
                el = t.get("engine_elapsed_s")
                st = t.get("starter_s")
                lines.append(
                    f"| {name} | "
                    f"{'—' if el is None else f'{el:.2f} s'} | "
                    f"{'—' if st is None else f'{st:.2f} s'} | "
                    f"{t.get('cycles') if t.get('cycles') is not None else '—'} | {t.get('threads') or '—'} | "
                    f"{t.get('note', t.get('termination', ''))} |"
                )
    if same_load and same_load.get("loads"):
        lines += [
            "",
            "## Same load (the grade) — nested family only",
            "",
            "Mike: same p → same strain/deformation. Stations are PLOAD **32.5 kPa** "
            "(t≈20 ms) and **35.8 kPa** (t≈22 ms); if ANIM frames differ, the table uses the "
            "closest **p**. Coarse Gmsh remesh is excluded. "
            "Peak λ_max at holes/creases is a sharp-hole singularity — volume / λ_aw is the signal.",
            "",
        ]
        notes = (same_load.get("station_notes") or []) if same_load else []
        if notes:
            lines += ["Frame-station notes: " + "; ".join(notes), ""]
        for ld_key, ld_label in (("p325", "32.5 kPa (t≈20 ms)"), ("p358", "35.8 kPa (t≈22 ms)")):
            recs = (same_load["loads"] or {}).get(ld_key) or []
            lines += [
                f"### {ld_label}",
                "",
                "| N | density | t [ms] | p [Pa] | λ_max | λ_aw | V [mL] | Ψ [J] |",
                "|--:|---------|-------:|-------:|------:|-----:|-------:|------:|",
            ]
            for r in recs:
                if r.get("missing") or r.get("lam_max") is None:
                    lines.append(f"| {r.get('N','')} | {r['density']} | — | — | — | — | — | — |")
                    continue
                aw = r.get("lam_aw_mean")
                aw_s = "—" if aw is None else f"{aw:.4f}"
                lines.append(
                    f"| {r['N']} | {r['density']} | {r['t']*1e3:.3g} | {r['p_Pa']:.0f} | "
                    f"{r['lam_max']:.4f} | {aw_s} | {r['V_mL']:.4g} | {r['Psi_J']:.4g} |"
                )
            prs = (same_load.get("pairs") or {}).get(ld_key) or []
            if prs:
                lines += [
                    "",
                    f"| pair | N_c → N_f | ΔV | Δλ_max | Δλ_aw | pass |",
                    f"|------|-----------|---:|-------:|------:|:----:|",
                ]
                for p in prs:
                    lines.append(
                        f"| {p['pair']} | {p['Ns']} | {p['dv']*100:.2f}% | {p['dlam']*100:.2f}% | "
                        f"{p['daw']*100:.2f}% | **{'PASS' if p['pass'] else 'FAIL'}** |"
                    )
            lines.append("")
    lines += [
        "",
        "## First λ_max ≥ 2 (historical crossing — not the grade)",
        "",
        "| N | density | t [ms] | p [Pa] | λ_max | V [mL] | Ψ [J] | λ∈[2.0,2.35] | Ψ≥0 | contact |",
        "|--:|---------|-------:|-------:|------:|-------:|------:|:------------:|:---:|---------|",
    ]
    for r in rows:
        if not r.get("reached_lambda2"):
            why = "CFL before λ≥2" if r.get("cfl_before_lambda2") else "not reached"
            lines.append(
                f"| {r['N']} | {r['density']} | — | — | — | — | — | — | — | {why} |"
            )
            continue
        band = LAM_LO <= r["lam_max"] <= LAM_HI
        psi_ok = r["Psi_J"] >= -1e-8
        gap = r.get("gap_mm")
        punch = r.get("punch")
        if r.get("metrics_only"):
            contact = "metrics-only (gap skipped; report-only)"
        else:
            try:
                gap_s = f"gap={float(gap):.3g} mm"
            except (TypeError, ValueError):
                gap_s = "gap=n/a"
            contact = f"{gap_s}; punch={punch} (report-only)"
        lines.append(
            f"| {r['N']} | {r['density']} | {r['t']*1e3:.3g} | {r['p_Pa']:.0f} | "
            f"{r['lam_max']:.4f} | {r['V_mL']:.4g} | {r['Psi_J']:.4g} | "
            f"{'yes' if band else 'NO'} | {'yes' if psi_ok else 'NO'} | {contact} |"
        )
    lines += [
        "",
        "All values are **dynamic** (explicit `/PLOAD` + `/ADYREL`), not Chiron QS.",
        "",
        "λ field at that frame (area-weighted; report-only, not a gate):",
        "",
        "| N | density | λ_aw_mean | λ_p90 |",
        "|--:|---------|----------:|------:|",
    ]
    for r in rows:
        if not r.get("reached_lambda2"):
            lines.append(f"| {r['N']} | {r['density']} | — | — |")
            continue
        lines.append(
            f"| {r['N']} | {r['density']} | {r.get('lam_aw_mean', float('nan')):.4f} | "
            f"{r.get('lam_p90', float('nan')):.4f} |"
        )
    lines += [
        "",
        "## Successive pairs (relative change vs coarser N)",
        "",
        "| pair | N_c → N_f | Δp | ΔV | Δλ_max | λ band | Ψ≥0 | pass |",
        "|------|-----------|---:|---:|-------:|:------:|:---:|:----:|",
    ]
    for p in pairs:
        if p.get("skipped"):
            lines.append(
                f"| {p['pair']} | {p.get('Ns', '')} | — | — | — | — | — | skipped ({p['skipped']}) |"
            )
            continue
        lines.append(
            f"| {p['pair']} | {p['Ns']} | {p['dp']*100:.2f}% | {p['dv']*100:.2f}% | "
            f"{p['dlam']*100:.2f}% | {'yes' if p['lam_band_ok'] else 'NO'} | "
            f"{'yes' if p['psi_ok'] else 'NO'} | **{'PASS' if p['pass'] else 'FAIL'}** |"
        )
    lines += [
        "",
        "## Verdict",
        "",
        f"**{verdict}**",
        "",
        "Converged dynamic on this explicit tape is **not** an ABC apples-to-apples "
        "claim against the JS Chiron QS warn (~54 kPa).",
        "",
        "## Forks",
        "",
        *fork_lines(rows),
        "",
    ]
    if letter == "A":
        lines += [
            "Vanilla finest `/DT/NODA/STOP 0.9 1e-6` died at **t=0** (nodal dt = 9.74e-7). "
            "That is mesh CFL, not a 1e-15 hang. Kareem `/AMS` (Tmin 1e-4 and 5e-6) **ruptured** "
            "the LAW42 + Belytschko film; slower PLOAD cannot fix rest CFL. Working tape: "
            "`forks/finest-stop5e7` keeps STOP (not CST) at Tmin=**5e-7**, same μ/ρ/Ishell=1/`/PLOAD`/`/ADYREL`.",
            "",
            "## Reproduce",
            "",
            "```bash",
            "bash radioss/install_openradioss.sh",
            "python3 tools/refine_letter_a.py",
            "bash radioss/A-refine/run.sh",
            "python3 tools/refine_letter_a.py --finest-only",
            "python3 tools/mesh_to_radioss.py --allow-n --check \\",
            "  --mesh radioss/A-refine/meshes/A-finest.json \\",
            "  --out-dir radioss/A-refine/forks/finest-stop5e7 --noda-stop 5e-7",
            "bash radioss/A-refine/run.sh --finest-only",
            "python3 tools/refine_same_load.py --session-rerun finest",
            "python3 tools/refine_report.py",
            "```",
            "",
        ]
    else:
        lines += [
            "B/C ladder is ship / fine / finer only (no coarse Gmsh row, no finest / N≈99k). "
            "Hang guard remains STOP. `/AMS` only if CFL dies before λ≥2; drop AMS if it ruptures.",
            "",
            "## Reproduce",
            "",
            "```bash",
            "bash radioss/install_openradioss.sh",
            f"python3 tools/refine_letter_a.py --letter {letter}",
            f"bash radioss/{letter}-refine/run.sh",
            f"python3 tools/refine_same_load.py --root radioss/{letter}-refine "
            "--session-rerun ship --session-rerun fine --session-rerun finer",
            f"python3 tools/refine_report.py --root radioss/{letter}-refine",
            "```",
            "",
        ]
    out.write_text("\n".join(lines) + "\n")


def main(argv=None) -> int:
    repo = Path(__file__).resolve().parent.parent
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=repo / "radioss" / "A-refine")
    args = ap.parse_args(argv)
    root = args.root
    summary = json.loads((root / "mesh-summary.json").read_text()) if (root / "mesh-summary.json").exists() else {}
    letter = letter_of(root, summary)
    nested = nested_present(root, summary) or NESTED[:3]

    rows = []
    for dens in DENSITIES:
        deck = resolve_deck(root, dens)
        if dens not in summary and not deck.exists():
            continue
        if dens == "finest" and letter in ("B", "C"):
            continue
        if dens == "coarse" and letter in ("B", "C"):
            continue
        w = load_warn(deck)
        meta = json.loads((deck / "deck-meta.json").read_text()) if (deck / "deck-meta.json").exists() else {}
        plan = (summary.get(dens) or {}).get("plan") or dens
        rec = {
            "density": dens,
            "N": int((summary.get(dens) or {}).get("N") or meta.get("n") or 0),
            "n_quads": int(meta.get("nquads") or (summary.get(dens) or {}).get("nQuads") or 0),
            "plan": plan,
            "reached_lambda2": bool(w and w.get("reached_lambda2")),
            "cfl_before_lambda2": bool(w and w.get("cfl_before_lambda2")),
        }
        if w:
            rec.update(
                {
                    "t": w.get("t"),
                    "p_Pa": w.get("p_Pa"),
                    "lam_max": w.get("lam_max"),
                    "V_mL": w.get("V_mL"),
                    "Psi_J": w.get("Psi_J"),
                    "gap_mm": w.get("gap_mm"),
                    "punch": w.get("punch"),
                    "ams": w.get("ams"),
                    "metrics_only": w.get("metrics_only"),
                    "cfl_after_lambda2": w.get("cfl_after_lambda2"),
                    "lam_p90": (w.get("lambda_field") or {}).get("lam_p90"),
                    "lam_aw_mean": (w.get("lambda_field") or {}).get("lam_aw_mean"),
                }
            )
        rows.append(rec)

    pairs = []
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        if not a.get("reached_lambda2") or not b.get("reached_lambda2"):
            why = []
            if not a.get("reached_lambda2"):
                why.append(a["density"] + (" CFL" if a.get("cfl_before_lambda2") else " no λ≥2"))
            if not b.get("reached_lambda2"):
                why.append(b["density"] + (" CFL" if b.get("cfl_before_lambda2") else " no λ≥2"))
            pairs.append(
                {
                    "pair": f"{a['density']}→{b['density']}",
                    "Ns": f"{a['N']} → {b['N']}",
                    "skipped": ", ".join(why),
                }
            )
            continue
        g = pair_verdict(a, b, a["density"], b["density"])
        g["Ns"] = f"{a['N']} → {b['N']}"
        pairs.append(g)

    judged = [p for p in pairs if not p.get("skipped")]
    last = judged[-1] if judged else None

    same_load = None
    slp = root / "same_load.json"
    if slp.exists():
        same_load = json.loads(slp.read_text())

    # Mike's grade: last nested pair at both same-load stations.
    sl_pairs = []
    last_pair_name = None
    if same_load:
        nst = same_load.get("nested") or list(nested)
        if len(nst) >= 2:
            last_pair_name = f"{nst[-2]}→{nst[-1]}"
        for k in ("p325", "p358"):
            sl_pairs.extend((same_load.get("pairs") or {}).get(k) or [])
    last_nested = []
    if sl_pairs and last_pair_name:
        last_nested = [p for p in sl_pairs if p.get("pair") == last_pair_name]
    blowup_loads = set()
    if same_load:
        for k, rows_ld in (same_load.get("loads") or {}).items():
            if any(float(r.get("lam_max") or 0) > 8.0 for r in rows_ld if not r.get("missing") and r.get("lam_max") is not None):
                blowup_loads.add(k)
    live_nested = [p for p in last_nested if p.get("load") not in blowup_loads]
    if last_nested and all(p.get("pass") for p in last_nested) and len(last_nested) == 2:
        pair = last_nested[0]["pair"]
        verdict = (
            f"converged (same-load) — {pair} ΔV/Δλ_max/Δλ_aw within 5%/2%/2% "
            "at both 32.5 kPa and 35.8 kPa. Dynamic only — not an ABC apples claim."
        )
    elif live_nested:
        bits = "; ".join(
            f"{p['load']} {p['pair']} ΔV={p['dv']*100:.2f}% Δλ_max={p['dlam']*100:.2f}% Δλ_aw={p['daw']*100:.2f}%"
            for p in last_nested
        )
        vol_aw_ok = all(p.get("dv_ok") and p.get("daw_ok") for p in live_nested)
        dlam_fail = any(not p.get("dlam_ok") for p in live_nested)
        if vol_aw_ok and dlam_fail:
            blow = (
                " 35.8 kPa is a CFL blow-up on the outward tape (not a grade station)."
                if blowup_loads
                else ""
            )
            verdict = (
                f"letter {letter}: volume / λ_aw settled on last nested pair; "
                "λ_max climbing at holes/creases is a sharp-hole singularity "
                "(Mike 2026-09-12 — perfectly sharp hole in the geometry input; "
                "real creases have a small radius). Do not chase λ_max with more "
                "global refine. Not mesh-failed. " + bits + blow
            )
        else:
            verdict = (
                "not-yet — same load, volume / λ_aw still moving. " + bits
            )
    elif last and last.get("pass"):
        # finer of the passing finest pair; ship is the design N if ship→fine passes
        finer_name = last["pair"].split("→")[1]
        finer_n = next(r["N"] for r in rows if r["density"] == finer_name)
        # If the pair agrees, the coarser N is the converged design density.
        coarser_name = last["pair"].split("→")[0]
        coarser_n = next(r["N"] for r in rows if r["density"] == coarser_name)
        verdict = (
            f"converged N = {coarser_n} ({coarser_name})  "
            f"[finest passing pair {last['pair']}; finer N={finer_n} agrees within lock]. "
            f"Dynamic only — not an ABC apples claim."
        )
    elif any(r.get("cfl_before_lambda2") for r in rows):
        dens = ", ".join(r["density"] for r in rows if r.get("cfl_before_lambda2"))
        verdict = (
            f"not-yet — CFL before λ≥2 on: {dens}. "
            "Kareem fork required (/AMS or slower PLOAD; not NODA/CST)."
        )
    else:
        extra = ""
        if last and not last.get("pass"):
            extra = (
                f" {last['pair']} Δp={last['dp']*100:.2f}%, ΔV={last['dv']*100:.2f}%, "
                f"Δλ_max={last['dlam']*100:.2f}% "
                f"(locks 5%/5%/2%)."
            )
            if last.get("dp_ok") and last.get("dv_ok") and not last.get("dlam_ok"):
                extra += " λ_max still moving (needs a finer N or a QS-ish tape)."
        verdict = (
            "not-yet — successive ~2× N did not meet Δp≤5%, ΔV≤5%, Δλ_max≤2% "
            "with λ_max in [2.0, 2.35] and Ψ≥0."
            + extra
        )

    write_refine_md(
        root / "REFINE.md",
        rows,
        pairs,
        verdict,
        same_load=same_load,
        letter=letter,
        nested=nested,
    )
    (root / "convergence.json").write_text(
        json.dumps(
            {"rows": rows, "pairs": pairs, "verdict": verdict, "same_load": same_load},
            indent=2,
        )
        + "\n"
    )
    print(verdict)
    print(f"wrote {root / 'REFINE.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
