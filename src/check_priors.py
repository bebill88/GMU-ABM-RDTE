"""
Quick validation script to ensure closed_projects priors load and have coverage.
Usage:
    python -m src.check_priors [--config parameters.yaml]
"""
from __future__ import annotations

import argparse
import os
import sys

from .run_experiment import _load_parameters  # type: ignore
from .data_loader import load_closed_projects


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=str, default=None, help="Path to parameters.yaml")
    args = parser.parse_args()

    params = _load_parameters(args.config)
    data_cfg = params.get("data", {}) or {}
    path = data_cfg.get("closed_projects_csv")
    rows, priors = load_closed_projects(path)
    if not rows:
        raise SystemExit(f"closed_projects_csv missing or empty at {path}; priors unavailable.")
    coverage = {k: len(v) for k, v in priors.items() if isinstance(v, dict)}
    print(f"Loaded {len(rows)} closed projects from {path}")
    print(f"Priors coverage: {coverage}")
    if not priors.get("overall_rate", 0):
        raise SystemExit("Overall prior rate is zero; check closed_projects data.")
    print("Priors validation OK")


if __name__ == "__main__":
    main()
