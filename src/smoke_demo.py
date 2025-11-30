"""
CI/Smoke helper: run a short demo-profile simulation and assert we see at least one transition.
Usage:
    python -m src.smoke_demo
"""
from __future__ import annotations

import os
import sys
import yaml

from .run_experiment import run_once, _load_parameters  # type: ignore
from .model import RdteModel


def main() -> None:
    # Load parameters and force demo profile for higher transition odds
    params_path = os.path.join(os.getcwd(), "parameters.yaml")
    params = _load_parameters(params_path)
    params.setdefault("model", {})
    params["model"]["testing_profile"] = "demo"
    penalty_config = params.get("penalties", {}) or {}
    gates_config = params.get("gates", {}) or {}
    agent_config = params.get("agents", {}) or {}
    data_config = params.get("data", {}) or {}

    model = RdteModel(
        n_researchers=20,
        n_policymakers=5,
        n_endusers=15,
        funding_rdte=1.0,
        funding_om=0.5,
        regime="adaptive",
        shock_at=80,
        seed=123,
        shock_duration=10,
        testing_profile="demo",
        labs_csv=data_config.get("labs_locations_csv"),
        rdte_csv=data_config.get("rdte_fy26_csv"),
        penalty_config=penalty_config,
        gate_config=gates_config,
        events_path=None,
        data_config=data_config,
        agent_config=agent_config,
    )
    summary = model.run(steps=60)
    transitions = summary.get("transitions", 0)
    if transitions <= 0:
        raise AssertionError(f"Smoke demo expected >0 transitions; got {transitions}.")
    print(f"Smoke demo OK: transitions={transitions}, transition_rate={summary.get('transition_rate'):.3f}")


if __name__ == "__main__":
    main()
