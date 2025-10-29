"""
Lightweight plotting utility for experiment outputs.
Intentionally simple: 1) prints dataframe stats, 2) dumps a histogram PNG.
"""
from __future__ import annotations

import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt


def main() -> None:
    p = argparse.ArgumentParser(description="Plot quick metrics from a results.csv file")
    p.add_argument("--path", required=True, help="Path to outputs/*/results.csv")
    args = p.parse_args()

    # Load the CSV produced by run_experiment
    df = pd.read_csv(args.path)
    print(df.describe())

    # Plot a quick histogram of transition rates
    plt.figure()
    df["transition_rate"].plot(kind="hist", bins=10, title="Transition Rate")
    plt.xlabel("transition_rate")
    plt.ylabel("count")
    plt.tight_layout()
    out_png = os.path.join(os.path.dirname(args.path), "transition_rate_hist.png")
    plt.savefig(out_png, dpi=150)
    print(f"Saved {out_png}")


if __name__ == "__main__":
    main()
