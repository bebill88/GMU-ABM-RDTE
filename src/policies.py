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


def _status_multiplier(status: str) -> float:
    s = (status or "").strip().lower()
    if s == "planning":
        return 0.8
    if s == "active":
        return 1.0
    if s == "delayed":
        return 0.5
    if s == "fielded":
        return 0.2
    if s == "terminated":
        return 0.0
    return 1.0


def _portfolio_multiplier(model, researcher, gate: str) -> float:
    """
    Optional per-portfolio weighting for funding/adoption/test gates.
    Scenario definitions can provide e.g. funding_portfolio_weights: {Cyber: 1.2}.
    """
    gc = getattr(model, "gate_config", {}) or {}
    weights = (gc.get(f"{gate}_portfolio_weights", {}) or {})
    portfolio = getattr(researcher, "portfolio", None) or getattr(researcher, "domain", "Generic")
    try:
        return float(weights.get(portfolio, 1.0))
    except Exception:
        return 1.0


def _dependency_multiplier(model, researcher, stage: str) -> float:
    """
    Compute a multiplier based on whether upstream dependencies have
    completed their own targets. Unsatisfied dependencies push the
    program into a Delayed status and reduce progression odds.
    """
    deps = getattr(researcher, "dependencies", None) or []
    if not deps:
        return 1.0

    program_index = getattr(model, "program_index", {}) or {}
    unsatisfied = 0
    for dep_id in deps:
        dep = program_index.get(dep_id)
        if dep is None:
            # Unknown dependency; skip but leave a breadcrumb if logging.
            continue
        dep_status = getattr(dep, "program_status", "Active")
        dep_done = getattr(dep, "time_to_transition", None) is not None or dep_status in {"Fielded", "Terminated"}
        if not dep_done:
            unsatisfied += 1

    if unsatisfied == 0:
        # Clear delay once prerequisites are met.
        if getattr(researcher, "program_status", "Active") == "Delayed":
            researcher.program_status = "Active"
        return 1.0

    # Mark as delayed and reduce transition chance; multiple missing
    # dependencies compound moderately.
    researcher.program_status = "Delayed"
    mult = max(0.1, 1.0 - 0.25 * unsatisfied)
    try:
        model._last_gate_context["dependency_unsatisfied"] = unsatisfied
        model._last_gate_context["dependency_multiplier"] = round(mult, 6)
    except Exception:
        pass
    return mult

def _risk_multiplier(model, researcher, gate: str) -> float:
    """
    Vendor/performance risk factor. Strongest effect on contracting gate.
    """
    perf = max(0.0, float(getattr(researcher, "perf_penalty", 0.0)))
    weight = float(getattr(model, "vendor_weight", 0.3))
    if gate == "contracting":
        effective = min(1.0, weight * perf)
    else:
        effective = min(1.0, 0.3 * weight * perf)
    return max(0.0, 1.0 - effective)


def _ecosystem_multiplier(model, researcher) -> float:
    bonus = getattr(researcher, "ecosystem_bonus", 0.0)
    eco_scale = getattr(model, "ecosystem_scale", 0.05)
    return max(0.0, 1.0 + eco_scale * bonus)


def _apply_external_modifiers(model, researcher, gate: str, base_prob: float) -> float:
    prob = model.apply_gao_modifier(base_prob, researcher)
    risk = _risk_multiplier(model, researcher, gate)
    ecosystem = _ecosystem_multiplier(model, researcher)
    shock = 1.0
    try:
        shock = model.get_shock_modifier(gate, researcher)
    except Exception:
        pass
    return max(0.0, min(1.0, prob * risk * ecosystem * shock))


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

    status_mult = _status_multiplier(getattr(researcher, "program_status", "Active"))
    port_mult = _portfolio_multiplier(model, researcher, gate="funding")
    p = max(0.0, min(1.0, p * status_mult * port_mult))

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
    base_prob = max(0.02, min(0.98, base * color_weight * source_mult))

    # Support and alignment multipliers
    lab_support = max(0.0, min(2.0, float(getattr(researcher, "lab_support_factor", 1.0))))
    industry_support = max(0.0, min(2.0, float(getattr(researcher, "industry_support_factor", 1.0))))
    authority_align = max(0.0, min(1.0, float(getattr(researcher, "authority_alignment_score", 0.5))))
    svc_align = max(0.0, min(1.0, float(getattr(researcher, "priority_alignment_service", 0.5))))

    support_mult = 0.2 + 0.2 * lab_support + 0.2 * industry_support + 0.2 * authority_align + 0.2 * svc_align
    sponsor_strength = max(0.0, min(1.2, float(getattr(researcher, "sponsor_authority", 0.8))))
    sponsor_mult = 0.7 + 0.6 * sponsor_strength  # mild boost for strong sponsors
    class_pen = max(0.0, min(0.3, float(getattr(researcher, "classification_penalty", 0.0))))
    domain_align = max(0.0, min(1.0, float(getattr(researcher, "domain_alignment", 0.5))))
    domain_mult = 0.8 + 0.4 * domain_align

    status_mult = _status_multiplier(getattr(researcher, "program_status", "Active"))
    portfolio_mult = _portfolio_multiplier(model, researcher, gate="funding")

    shock_factor = 1.0
    if model.regime == "shock" and model.is_in_shock():
        base_shock = float(gc.get("funding_shock_penalty", 0.15))
        shock_sens = max(0.0, min(1.0, float(getattr(researcher, "shock_sensitivity", 0.5))))
        effective_shock = base_shock * shock_sens
        shock_factor = max(0.2, 1.0 - effective_shock)

    # Mild stall relief: if stuck in a stage for many ticks, slowly raise odds.
    stage_age = 0
    try:
        if getattr(researcher, "stage_enter_tick", None) is not None:
            stage_age = model.schedule.time - researcher.stage_enter_tick
    except Exception:
        stage_age = 0
    # Stronger stall relief to avoid deadlocks; cap keeps probabilities sane.
    latency_boost = 1.0 + min(max(stage_age, 0), 200) * 0.02  # up to +400%

    p = max(
        0.02,
        min(
            0.98,
            base_prob
            * factor
            * support_mult
            * sponsor_mult
            * status_mult
            * portfolio_mult
            * domain_mult
            * shock_factor
            * latency_boost
            * (1.0 - class_pen),
        ),
    )
    # Record gate context for logging
    model._last_gate_context = {
        "gate_prob_base": round(base_prob, 6),
        "gate_penalty_factor": round(factor, 6),
        "gate_support_mult": round(support_mult, 6),
        "gate_sponsor_mult": round(sponsor_mult, 6),
        "gate_status_mult": round(status_mult, 6),
        "gate_portfolio_mult": round(portfolio_mult, 6),
        "gate_domain_mult": round(domain_mult, 6),
        "gate_shock_factor": round(shock_factor, 6),
        "gate_latency_boost": round(latency_boost, 6),
        "gate_stage_age": stage_age,
        "gate_prob_final": round(p, 6),
        "funding_source": source,
        "funding_color_weight": round(color_weight, 6),
        "funding_class_penalty": round(class_pen, 6),
    }
    p = _apply_external_modifiers(model, researcher, "funding", p)
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
    status_mult = _status_multiplier(getattr(researcher, "program_status", "Active"))
    if status_mult < 1.0:
        pen = min(1.0, pen + (1.0 - status_mult))
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
            # Save context for logging
            try:
                model._last_gate_context = {
                    "legal_penalty_applied": round(pen, 6),
                    "legal_favorable": round(dist.get("favorable", 0.0) / total, 6),
                    "legal_caveats": round(dist.get("favorable_with_caveats", 0.0) / total, 6),
                    "legal_unfavorable": round(dist.get("unfavorable", 0.0) / total, 6),
                    "legal_status_mult": round(status_mult, 6),
                }
            except Exception:
                pass
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

    # Apply penalty factor and program status
    factor = model.penalty_factor("contracting", researcher)
    status_mult = _status_multiplier(getattr(researcher, "program_status", "Active"))
    exec_capacity = max(0.0, min(1.2, float(getattr(researcher, "executing_capacity", 0.5))))
    exec_mult = 0.7 + 0.6 * exec_capacity
    domain_align = max(0.0, min(1.0, float(getattr(researcher, "domain_alignment", 0.5))))
    domain_mult = 0.85 + 0.3 * domain_align
    class_pen = max(0.0, min(0.3, float(getattr(researcher, "classification_penalty", 0.0))))
    # Mild stall relief if stuck in the stage a long time
    stage_age = 0
    try:
        if getattr(researcher, "stage_enter_tick", None) is not None:
            stage_age = model.schedule.time - researcher.stage_enter_tick
    except Exception:
        stage_age = 0
    latency_boost = 1.0 + min(max(stage_age, 0), 200) * 0.02
    base_prob = max(0.05, min(0.95, float(base)))
    p = max(
        0.05,
        min(
            0.95,
            base_prob
            * factor
            * status_mult
            * exec_mult
            * domain_mult
            * (1.0 - class_pen)
            * latency_boost,
        ),
    )
    model._last_gate_context = {
        "gate_prob_base": round(base_prob, 6),
        "gate_penalty_factor": round(factor, 6),
        "gate_status_mult": round(status_mult, 6),
        "gate_exec_mult": round(exec_mult, 6),
        "gate_domain_mult": round(domain_mult, 6),
        "gate_class_penalty": round(class_pen, 6),
        "gate_latency_boost": round(latency_boost, 6),
        "gate_stage_age": stage_age,
        "gate_prob_final": round(p, 6),
        "contract_org_type": org,
    }
    p = _apply_external_modifiers(model, researcher, "contracting", p)
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

    shock_factor = 1.0
    if model.regime == "shock" and model.is_in_shock():
        base_shock = float(gc.get("test_shock_penalty", 0.05))
        shock_sens = max(0.0, min(1.0, float(getattr(researcher, "shock_sensitivity", 0.5))))
        effective_shock = base_shock * shock_sens
        shock_factor = max(0.2, 1.0 - effective_shock)

    # Apply penalty factor for testing gate, status, portfolio, digital/MBSE evidence, and dependencies
    factor = model.penalty_factor("test", researcher, stage)
    status_mult = _status_multiplier(getattr(researcher, "program_status", "Active"))
    portfolio_mult = _portfolio_multiplier(model, researcher, gate="test")
    dependency_mult = _dependency_multiplier(model, researcher, stage)
    test_capacity = max(0.0, min(1.2, float(getattr(researcher, "test_capacity", 0.5))))
    test_mult = 0.7 + 0.6 * test_capacity
    domain_align = max(0.0, min(1.0, float(getattr(researcher, "domain_alignment", 0.5))))
    domain_mult = 0.85 + 0.3 * domain_align
    class_pen = max(0.0, min(0.3, float(getattr(researcher, "classification_penalty", 0.0))))

    digital = max(0.0, min(1.0, float(getattr(researcher, "digital_maturity_score", 0.5))))
    mbse_cov = max(0.0, min(1.0, float(getattr(researcher, "mbse_coverage", 0.5))))
    # Blend evidence so weak signals do not zero-out progression.
    evidence_mult = 0.5 + 0.5 * (digital * 0.5 + mbse_cov * 0.5)

    # Mild stall relief: if stuck in stage, slowly increase probability.
    stage_age = 0
    try:
        if getattr(researcher, "stage_enter_tick", None) is not None:
            stage_age = model.schedule.time - researcher.stage_enter_tick
    except Exception:
        stage_age = 0
    latency_boost = 1.0 + min(max(stage_age, 0), 200) * 0.02

    base_prob = max(0.05, min(0.95, (base + trl_bonus)))
    p = max(
        0.05,
        min(
            0.95,
            base_prob
            * factor
            * status_mult
            * portfolio_mult
            * evidence_mult
            * shock_factor
            * dependency_mult
            * latency_boost
            * test_mult
            * domain_mult
            * (1.0 - class_pen),
        ),
    )
    model._last_gate_context = {
        "gate_prob_base": round(base_prob, 6),
        "gate_penalty_factor": round(factor, 6),
        "gate_status_mult": round(status_mult, 6),
        "gate_portfolio_mult": round(portfolio_mult, 6),
        "gate_evidence_mult": round(evidence_mult, 6),
        "gate_shock_factor": round(shock_factor, 6),
        "gate_dependency_mult": round(dependency_mult, 6),
        "gate_latency_boost": round(latency_boost, 6),
        "gate_stage_age": stage_age,
        "gate_prob_final": round(p, 6),
        "legal_status_at_test": legal_status,
        "gate_test_mult": round(test_mult, 6),
        "gate_domain_mult": round(domain_mult, 6),
        "gate_class_penalty": round(class_pen, 6),
    }
    p = _apply_external_modifiers(model, researcher, "test", p)
    return model.random.random() < p


def adoption_gate(model, researcher) -> bool:
    """
    Adoption decision wrapper that incorporates portfolio weighting and
    rich priority alignment factors before sampling end-users.
    """
    # Base majority vote using existing EndUser evaluation
    k = max(1, len(model.endusers) // 5)
    sample = model.random.sample(model.endusers, k=k)
    votes = [eu.evaluate(researcher) for eu in sample]
    base_accepted = sum(votes) >= max(1, len(sample) // 2)

    # Map alignment scores into a modest multiplier on adoption odds
    nds = max(0.0, min(1.0, float(getattr(researcher, "priority_alignment_nds", 0.5))))
    ccmd = max(0.0, min(1.0, float(getattr(researcher, "priority_alignment_ccmd", 0.5))))
    svc = max(0.0, min(1.0, float(getattr(researcher, "priority_alignment_service", 0.5))))
    authority_align = max(0.0, min(1.0, float(getattr(researcher, "authority_alignment_score", 0.5))))

    align_mult = 0.25 * (nds + ccmd + svc + authority_align)

    status_mult = _status_multiplier(getattr(researcher, "program_status", "Active"))
    portfolio_mult = _portfolio_multiplier(model, researcher, gate="adoption")

    # Translate the base boolean and multipliers into a probability
    base_prob = 0.7 if base_accepted else 0.3
    p = max(
        0.01,
        min(
            0.99,
            base_prob * (0.5 + align_mult) * status_mult * portfolio_mult,
        ),
    )

    # Record for logging
    try:
        model._last_gate_context = {
            "adoption_base_vote": int(base_accepted),
            "adoption_align_mult": round(align_mult, 6),
            "adoption_status_mult": round(status_mult, 6),
            "adoption_portfolio_mult": round(portfolio_mult, 6),
            "gate_prob_final": round(p, 6),
        }
    except Exception:
        pass

    p = _apply_external_modifiers(model, researcher, "adoption", p)
    return model.random.random() < p


