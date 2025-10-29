"""
CLI experiment runner.
Usage examples:
    python -m src.run_experiment --scenario linear   --runs 10 --steps 200 --seed 42
    python -m src.run_experiment --scenario adaptive --runs 10 --steps 200 --seed 42
    python -m src.run_experiment --scenario shock    --runs 10 --steps 200 --seed 42 --shock_at 80

Writes results to ./outputs/<scenario_timestamp>/results.csv plus metadata.json
"""
from __future__ import annotations

import argparse
import os
import csv
import json
import time

# Support both `python -m src.run_experiment` and `python src/run_experiment.py`.
# When executed as a script, relative imports fail because there's no package
# context. We detect that case and adjust sys.path to include the project root.
try:  # package context
    from .model import RdteModel
    from .utils import ensure_dir
except ImportError:  # direct script context
    import sys
    from pathlib import Path
    this_file = Path(__file__).resolve()
    project_root = this_file.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from src.model import RdteModel
    from src.utils import ensure_dir


def run_once(args) -> dict:
    """
    Run a single simulation with the given args and return the metrics summary.
    We also pack key parameters into the row for later analysis.
    """
    model = RdteModel(
        n_researchers=args.n_researchers,
        n_policymakers=args.n_policymakers,
        n_endusers=args.n_endusers,
        funding_rdte=args.funding_rdte,
        funding_om=args.funding_om,
        regime=args.scenario,
        shock_at=args.shock_at,
        seed=args.seed,
    )
    summary = model.run(steps=args.steps)
    summary.update({
        "scenario": args.scenario,
        "steps": args.steps,
        "seed": args.seed,
        "n_researchers": args.n_researchers,
        "n_policymakers": args.n_policymakers,
        "n_endusers": args.n_endusers,
        "funding_rdte": args.funding_rdte,
        "funding_om": args.funding_om,
        "shock_at": args.shock_at,
    })
    return summary


def main() -> None:
    # CLI flags keep experiments explicit and reproducible
    p = argparse.ArgumentParser()
    p.add_argument("--scenario", choices=["linear", "adaptive", "shock"], default="linear")
    p.add_argument("--runs", type=int, default=5)
    p.add_argument("--steps", type=int, default=200)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--n_researchers", type=int, default=40)
    p.add_argument("--n_policymakers", type=int, default=10)
    p.add_argument("--n_endusers", type=int, default=30)
    p.add_argument("--funding_rdte", type=float, default=1.0)
    p.add_argument("--funding_om", type=float, default=0.5)
    p.add_argument("--shock_at", type=int, default=80)
    args = p.parse_args()

    # Each run batch gets its own timestamped folder under outputs/
    tstamp = int(time.time())
    outdir = os.path.join("outputs", f"{args.scenario}_{tstamp}")
    ensure_dir(outdir)

    # Execute N runs with incrementing seeds for independence
    rows = []
    for i in range(args.runs):
        args.seed = args.seed + i
        rows.append(run_once(args))

    # Save CSV aggregate
    csv_path = os.path.join(outdir, "results.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # Save metadata for reproducibility
    with open(os.path.join(outdir, "metadata.json"), "w") as f:
        json.dump(vars(args), f, indent=2)

    print(f"Wrote {csv_path}")


if __name__ == "__main__":
    main()
