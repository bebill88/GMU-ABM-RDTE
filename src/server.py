"""
Mesa ModularServer for the RDT&E ABM.

Launch (default port 8521):
    python -m src.server

Custom port/host:
    python -m src.server --port 8522 --host 127.0.0.1 --open-browser

Then open http://<host>:<port> in your browser.
"""
from __future__ import annotations

import argparse
import os
from mesa.visualization.modules import ChartModule, TextElement
from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import Slider, Choice, NumberInput

from .model import RdteModel


class MetricsElement(TextElement):
    def render(self, model: RdteModel) -> str:  # type: ignore[override]
        attempts = model.metrics.attempts
        transitions = model.metrics.transitions
        last = model.metrics.adoptions_per_tick[-1] if model.metrics.adoptions_per_tick else 0
        total = sum(model.metrics.adoptions_per_tick) if model.metrics.adoptions_per_tick else 0
        return (
            f"Attempts: {attempts} | Transitions: {transitions} | "
            f"Adoptions (last tick): {last} | Cumulative: {total}"
        )


adoptions_chart = ChartModule(
    [
        {"Label": "adoptions_this_tick", "Color": "#1f77b4"},
        {"Label": "cum_adoptions", "Color": "#2ca02c"},
    ],
    data_collector_name="datacollector",
)


def launch(port: int = 8521, host: str = "127.0.0.1", open_browser: bool = False):
    params = {
        "n_researchers": Slider("n_researchers", 40, 10, 200, 5),
        "n_policymakers": Slider("n_policymakers", 10, 1, 40, 1),
        "n_endusers": Slider("n_endusers", 30, 5, 200, 5),
        "funding_rdte": Slider("funding_rdte", 1.0, 0.0, 2.0, 0.1),
        "funding_om": Slider("funding_om", 0.5, 0.0, 2.0, 0.1),
        "regime": Choice("regime", "adaptive", choices=["linear", "adaptive", "shock"]),
        "shock_at": Slider("shock_at", 80, 0, 500, 5),
        "shock_duration": Slider("shock_duration", 20, 0, 200, 5),
        "seed": NumberInput("seed", 42),
    }

    server = ModularServer(
        RdteModel,
        [MetricsElement(), adoptions_chart],
        "RDT&E ABM",
        params,
    )
    server.port = int(port)
    # Mesa binds to 127.0.0.1 by default; host override is supported on newer Mesa
    try:
        server.launch(open_browser=open_browser)
    except TypeError:
        # Backward compatibility with older Mesa that lacks open_browser arg
        server.launch()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the RDT&E ABM Mesa server")
    parser.add_argument("--port", type=int, default=int(os.environ.get("MESA_PORT", 8521)))
    parser.add_argument("--host", type=str, default=os.environ.get("MESA_HOST", "127.0.0.1"))
    parser.add_argument("--open-browser", action="store_true", help="Open a browser tab on launch")
    args = parser.parse_args()
    print(f"Starting RDT&E ABM server on http://{args.host}:{args.port}")
    launch(port=args.port, host=args.host, open_browser=args.open_browser)

