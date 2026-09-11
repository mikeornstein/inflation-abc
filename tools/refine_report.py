#!/usr/bin/env python3
"""Chiron/Themis locked mesh-convergence report for radioss/A-refine.

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

DENSITIES = ("coarse", "ship", "fine", "finer")


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


def write_refine_md(out: Path, rows: list[dict], pairs: list[dict], verdict: str) -> None:
    lines = [
        "# A-refine — mesh convergence (Chiron/Themis lock)",
        "",
        "Quad-only `/SHELL` + free-free `/ADYREL` OpenRadioss A inflate. "
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
        "",
        "## Metrics lock (2026-09-11)",
        "",
        "Treat as `briefs/2026-09-11-openradioss-mesh-convergence-metrics.md`.",
        "",
        "At **first λ_max ≥ 2** on each mesh N:",
        "",
        "- Report **p, λ_max, V, Ψ**",
        "- Label **dynamic** until a QS-ish tape exists",
        "- Successive ~2× denser N: relative change **p ≤ 5%**, **V ≤ 5%**, **λ_max ≤ 2%**",
        "- λ_max stays in **[2.0, 2.35]** at that frame",
        "- Ψ ≥ 0 required; contact viol / gap is **report-only**",
        "- If CFL dies before λ≥2: **/AMS or slower PLOAD** fork (Kareem) — not NODA/CST; Ishell=1; no μ/ρ retune",
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
    lines += [
        "",
        "## First λ_max ≥ 2 (dynamic)",
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
        "## Reproduce",
        "",
        "```bash",
        "bash radioss/install_openradioss.sh",
        "python3 tools/refine_letter_a.py",
        "bash radioss/A-refine/run.sh",
        "python3 tools/refine_letter_a.py --finer-only",
        "bash radioss/A-refine/run.sh --finer-only",
        "python3 tools/refine_report.py",
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

    rows = []
    for dens in DENSITIES:
        deck = root / dens
        if dens == "finer" and not deck.exists() and dens not in summary:
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
    if last and last.get("pass"):
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

    write_refine_md(root / "REFINE.md", rows, pairs, verdict)
    (root / "convergence.json").write_text(
        json.dumps({"rows": rows, "pairs": pairs, "verdict": verdict}, indent=2) + "\n"
    )
    print(verdict)
    print(f"wrote {root / 'REFINE.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
