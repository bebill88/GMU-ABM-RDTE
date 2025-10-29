"""
Policy gate functions capture "governance regimes" without hard‑coding ideology.
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
