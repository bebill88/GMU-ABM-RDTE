"""
Policy gate functions capture governance regimes without hard-coding ideology.
- funding_gate: probability a prototype secures funds this step
- oversight_gate: probability it clears oversight/milestones this step

Regimes:
- linear  : centralized, rigid milestones, slower feedback loops
- adaptive: decentralized, rolling evaluations, accelerated funding agility
- shock   : temporary disruption to budgets/oversight to test resilience
"""
from __future__ import annotations

from typing import Literal

Regime = Literal["linear", "adaptive", "shock"]


def funding_gate(model, researcher) -> bool:
    """
    Funding availability proxy:
    - linear   : conservative baseline (queue + narrow color of money)
    - adaptive : more flexible (e.g., OTA‑like agility or reprogramming ease)
    - shock    : temporary compression of RDTE, partial recovery after window
    """
    if model.regime == "linear":
        p = 0.3 * model.funding_rdte
    elif model.regime == "adaptive":
        p = 0.5 * (model.funding_rdte + model.funding_om)
    else:  # shock
        if model.is_in_shock():
            p = 0.15 * model.funding_rdte
        else:
            p = 0.45 * (model.funding_rdte + 0.5 * model.funding_om)

    return model.random.random() < p


def oversight_gate(model, researcher) -> bool:
    """
    Oversight pass probability:
    Lower rigidity => easier to pass, but we still factor in prototype quality.
    """
    if model.regime == "linear":
        rigidity = 0.8  # high drag
    elif model.regime == "adaptive":
        rigidity = 0.3  # rolling evaluations
    else:  # shock
        rigidity = 0.6 if model.is_in_shock() else 0.4

    # Convert rigidity + quality to pass probability (0.05 floor to avoid stall)
    pass_prob = max(0.05, (1.0 - rigidity) * 0.7 + 0.3 * researcher.quality)
    return model.random.random() < pass_prob


# ------------------ Extended typing ------------------
# (typing alias removed)



# ------------------ Stage-pipeline gates ------------------
def funding_gate_stage(model, researcher, stage: str) -> bool:
    """
    Stage-aware funding availability with coarse "color" behavior.
    - Early stages (feasibility, prototype_demo) rely mainly on RDT&E.
    - Later stages (functional/vulnerability/operational test) may leverage O&M/Proc-like pools.
    Funding source types (POM, UFR, ProgramBase, External, Partner, Partner_CoDev)
    modulate probability as simple multipliers.
    """
    stage = str(stage)
    early = stage in {"feasibility", "prototype_demo"}
    gc = getattr(model, "gate_config", {}) or {}
    def g(k, default):
        return float(gc.get(k, default))
    if model.regime == "linear":
        base = g("funding_base_linear_early", 0.25) if early else g("funding_base_linear_late", 0.20)
    elif model.regime == "adaptive":
        base = g("funding_base_adaptive_early", 0.40) if early else g("funding_base_adaptive_late", 0.35)
    else:  # shock
        if model.is_in_shock():
            base = g("funding_base_shock_early", 0.15) if early else g("funding_base_shock_late", 0.10)
        else:
            base = g("funding_base_postshock_early", 0.35) if early else g("funding_base_postshock_late", 0.30)

    # Color weights
    mix = g("color_weight_late_mix", 0.5)
    color_weight = model.funding_rdte if early else (mix * model.funding_rdte + (1.0 - mix) * model.funding_om)

    # Funding source multiplier
    source = getattr(researcher, "funding_source", "ProgramBase")
    source_mult = {
        "POM": 0.9,
        "ProgramBase": 1.0,
        "UFR": 0.7,
        "External": 0.8,
        "Partner": 0.75,
        "Partner_CoDev": 0.85,
    }.get(source, 1.0)

    # Apply repeat-failure penalty factor
    factor = model.penalty_factor("funding", researcher, stage)
    p = max(0.02, min(0.98, base * color_weight * source_mult * factor))
    return model.random.random() < p


def legal_review_gate(model, researcher) -> str:
    """
    Return a legal review outcome string.
    Factors: authority (Title10/Title50), domain, kinetic vs non-kinetic.
    """
    authority = getattr(researcher, "authority", "Title10")
    kinetic = getattr(researcher, "kinetic_category", "NonKinetic")

    # Baseline distribution
    gc = getattr(model, "gate_config", {}) or {}
    dist = dict(gc.get("legal_dist", {
        "favorable": 0.6,
        "favorable_with_caveats": 0.25,
        "unfavorable": 0.1,
        "not_conducted": 0.05,
    }))

    # Title 50 tends to shift to more caveats/unfavorable
    if authority == "Title50":
        shift = float(gc.get("legal_title50_shift", 0.10))
        dist["favorable"] = max(0.0, dist["favorable"] - shift)
        dist["favorable_with_caveats"] += 0.07
        dist["unfavorable"] += 0.03

    # Kinetic domains push toward more scrutiny
    if kinetic == "Kinetic":
        shift = float(gc.get("legal_kinetic_shift", 0.05))
        dist["favorable"] = max(0.0, dist["favorable"] - shift)
        dist["favorable_with_caveats"] += 0.03
        dist["unfavorable"] += 0.02

    # Apply repeat-failure penalty by shifting mass from favorable to caveats/unfavorable
    pen = 1.0 - model.penalty_factor("legal", researcher)
    if pen > 0:
        cap = float(gc.get("legal_penalty_shift_cap", 0.5))
        shift = min(dist["favorable"], cap * pen)  # cap shift for stability
        dist["favorable"] -= shift
        # distribute toward caveats (70%) and unfavorable (30%)
        dist["favorable_with_caveats"] += shift * 0.7
        dist["unfavorable"] += shift * 0.3

    # Normalize and sample
    total = sum(dist.values())
    r = model.random.random() * total
    acc = 0.0
    for k, v in dist.items():
        acc += v
        if r <= acc:
            return k
    return "favorable"  # fallback


def contracting_gate(model, researcher) -> bool:
    """Probability that contracting/vehicle path is successful this tick."""
    org = getattr(researcher, "org_type", "GovContractor")

    gc = getattr(model, "gate_config", {}) or {}
    base = (gc.get("contracting_base", {}) or {}).get(org, 0.55)

    # Adaptive regimes ease flexible instruments (e.g., OTA-like paths)
    if model.regime == "adaptive" and org in {"Commercial", "GovContractor"}:
        base += float(gc.get("contracting_adaptive_bonus", 0.10))
    if model.regime == "linear" and org == "Commercial":
        base -= float(gc.get("contracting_linear_commercial_penalty", 0.05))

    if model.regime == "shock" and model.is_in_shock():
        base -= 0.1

    # Apply penalty factor
    factor = model.penalty_factor("contracting", researcher)
    p = max(0.05, min(0.95, base * factor))
    return model.random.random() < p


def test_gate(model, researcher, stage: str, legal_status: str) -> bool:
    """
    Stage-specific technical/test pass probability.
    Factors: stage difficulty, TRL, domain, kinetic, legal caveats, regime, shocks.
    """
    stage = str(stage)
    trl = getattr(researcher, "trl", 3)
    domain = getattr(researcher, "domain", "Generic")
    kinetic = getattr(researcher, "kinetic_category", "NonKinetic")

    # Base difficulty by stage (higher is easier)
    gc = getattr(model, "gate_config", {}) or {}
    base_map = gc.get("test_base", {
        "feasibility": 0.7,
        "prototype_demo": 0.65,
        "functional_test": 0.6,
        "vulnerability_test": 0.55,
        "operational_test": 0.5,
    })
    base = float(base_map.get(stage, 0.6))

    # TRL contribution (TRL 1..9 mapped ~0..0.2)
    trl_bonus = min(float(gc.get("test_trl_bonus_cap", 0.2)), max(0.0, (trl - 3) * float(gc.get("test_trl_bonus_per_level", 0.03))))

    # Domain/Kinetic adjustments
    if kinetic == "Kinetic":
        base -= float(gc.get("test_kinetic_penalty", 0.05))
    if domain in {"Cyber", "EW"} and stage in {"vulnerability_test", "operational_test"}:
        base -= float(gc.get("test_cyber_vuln_ops_penalty", 0.05))

    # Legal caveats penalty; not_conducted slightly riskier
    if legal_status == "favorable_with_caveats":
        base -= 0.03
    elif legal_status == "not_conducted":
        base -= 0.02
    elif legal_status == "unfavorable":
        return False

    # Regime/shock effects
    if model.regime == "adaptive":
        base += float(gc.get("test_adaptive_bonus", 0.03))
    if model.regime == "shock" and model.is_in_shock():
        base -= float(gc.get("test_shock_penalty", 0.05))

    # Apply penalty factor for testing gate
    factor = model.penalty_factor("test", researcher, stage)
    p = max(0.05, min(0.95, (base + trl_bonus) * factor))
    return model.random.random() < p


