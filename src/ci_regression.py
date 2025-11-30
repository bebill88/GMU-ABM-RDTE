"""
Regression smoke tests:
1) Demo config transitions > 0 (fast profile)
2) Priors load with coverage > 0 when closed_projects.csv present
3) No-priors run completes without crash
"""
from __future__ import annotations

import argparse

from .run_experiment import _load_parameters  # type: ignore
from .data_loader import load_closed_projects
from .model import RdteModel


def run_demo(config: str) -> None:
    params = _load_parameters(config)
    data = params.get("data", {}) or {}
    penalties = params.get("penalties", {}) or {}
    gates = params.get("gates", {}) or {}
    agents = params.get("agents", {}) or {}
    model_cfg = params.get("model", {}) or {}
    model = RdteModel(
        n_researchers=20,
        n_policymakers=5,
        n_endusers=15,
        funding_rdte=model_cfg.get("funding_rdte", 1.0),
        funding_om=model_cfg.get("funding_om", 0.5),
        regime="adaptive",
        shock_at=model_cfg.get("shock_at", 80),
        seed=999,
        shock_duration=model_cfg.get("shock_duration", 20),
        testing_profile="demo",
        labs_csv=data.get("labs_locations_csv"),
        rdte_csv=data.get("rdte_fy26_csv"),
        penalty_config=penalties,
        gate_config=gates,
        data_config=data,
        agent_config=agents,
    )
    summary = model.run(steps=80)
    if summary.get("transitions", 0) <= 0:
        raise AssertionError("Demo profile smoke: expected >0 transitions.")
    print(f"[demo] transitions={summary['transitions']} transition_rate={summary['transition_rate']:.3f}")


def check_priors(config: str) -> None:
    params = _load_parameters(config)
    data = params.get("data", {}) or {}
    path = data.get("closed_projects_csv")
    rows, priors = load_closed_projects(path)
    if not rows:
        raise AssertionError(f"Priors missing or empty from {path}")
    coverage = {k: len(v) for k, v in priors.items() if isinstance(v, dict)}
    if priors.get("overall_rate", 0) == 0:
        raise AssertionError("Priors overall rate is zero.")
    print(f"[priors] rows={len(rows)} coverage={coverage}")


def run_no_priors(config: str) -> None:
    params = _load_parameters(config)
    data = params.get("data", {}) or {}
    penalties = params.get("penalties", {}) or {}
    gates = params.get("gates", {}) or {}
    agents = params.get("agents", {}) or {}
    penalties = dict(penalties)
    penalties["enable_priors"] = False
    penalties["closed_priors_weight"] = 0.0
    penalties["prior_weights_by_gate"] = {"funding": 0.0, "contracting": 0.0, "test": 0.0, "adoption": 0.0}
    model = RdteModel(
        n_researchers=20,
        n_policymakers=5,
        n_endusers=15,
        funding_rdte=1.0,
        funding_om=0.5,
        regime="adaptive",
        shock_at=80,
        seed=1001,
        shock_duration=20,
        testing_profile="demo",
        labs_csv=data.get("labs_locations_csv"),
        rdte_csv=data.get("rdte_fy26_csv"),
        penalty_config=penalties,
        gate_config=gates,
        data_config=data,
        agent_config=agents,
    )
    summary = model.run(steps=60)
    print(f"[no-priors] transitions={summary.get('transitions', 0)} (priors disabled run completed)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo_config", type=str, default="parameters.demo.yaml")
    parser.add_argument("--prod_config", type=str, default="parameters.yaml")
    args = parser.parse_args()
    run_demo(args.demo_config)
    check_priors(args.prod_config)
    run_no_priors(args.demo_config)
    print("CI regression smoke checks passed.")


if __name__ == "__main__":
    main()
