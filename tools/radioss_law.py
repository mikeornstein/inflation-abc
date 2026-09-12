"""Locked Inflation ABC constitutive constants for OpenRadioss decks.

Do not invent or retune μ or ρ. These match index.html / the Zeus lock:

    MU = (800 * PSI) / 1.75
    H0 = 0.015 * 0.0254
    CONTACT_KISS = max(2*H0, 1e-4)
    WARN_LAM = 2.0
    ρ = 1130 kg/m³  (Desmopan 85085A ISO 1183-1;
                      McMaster 1446T11 density is not published)
"""

PSI = 6894.757
MU = (800.0 * PSI) / 1.75
H0 = 0.015 * 0.0254
RHO = 1130.0
NU = 0.495
WARN_LAM = 2.0
CONTACT_KISS = max(2.0 * H0, 1e-4)
ALPHA1 = 2.0
PRONY_M = 0
P_WARN_JS = 54100.0  # Chiron quadmem A first λ≥2 (docs, not a retune)

RHO_LABEL = (
    "Desmopan 85085A ISO 1183-1; McMaster 1446T11 density not published"
)
MU_LABEL = "grill eng. μ = (800 * 6894.757) / 1.75 ; not invented"


def law_card_lines():
    return [
        "LAW42 neo-Hookean (Ogden 1-term)",
        f"  μ1      = {MU:.16g} Pa   # {MU_LABEL}",
        f"  α1      = {ALPHA1:g}",
        "  μp,αp   = 0 for p=2..10",
        f"  ν       = {NU:g}  (≤ 0.495)",
        f"  M       = {PRONY_M}  (no Prony)",
        f"  Iform   = 1 (standard Ogden SED)",
        f"  H0      = {H0:.16g} m  (0.015*0.0254)",
        f"  ρ       = {RHO:g} kg/m^3  # {RHO_LABEL}",
        f"  Gapmin  = {CONTACT_KISS:.16g} m  # CONTACT_KISS = max(2*H0, 1e-4)",
        f"  WARN_LAM= {WARN_LAM:g}",
    ]
