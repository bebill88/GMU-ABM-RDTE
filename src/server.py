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


class HelpElement(TextElement):
    def render(self, model: RdteModel) -> str:  # type: ignore[override]
        return (
            "<b>How to use this UI</b><br/>"
            "- Adjust population and funding sliders to change throughput.<br/>"
            "- Use scenario dropdowns (portfolio, service, org mix, funding pattern) to shape the portfolio mix.<br/>"
            "- Set <code>focus_researcher_id</code> to track a single project (-1 = none; valid ids are 0..N-1)."
        )


class MetricsElement(TextElement):
    def render(self, model: RdteModel) -> str:  # type: ignore[override]
        attempts = model.metrics.attempts
        transitions = model.metrics.transitions
        last = model.metrics.adoptions_per_tick[-1] if model.metrics.adoptions_per_tick else 0
        total = sum(model.metrics.adoptions_per_tick) if model.metrics.adoptions_per_tick else 0
        return (
            f"<b>Run metrics</b><br/>"
            f"Attempts: {attempts} | Transitions: {transitions}<br/>"
            f"Adoptions (last tick): {last} | Cumulative adoptions: {total}"
        )


class TransitionProbabilityElement(TextElement):
    def render(self, model: RdteModel) -> str:  # type: ignore[override]
        attempts = model.metrics.attempts
        transitions = model.metrics.transitions
        if attempts:
            rate = transitions / attempts
            return f"<b>Portfolio transition success (so far)</b>: {rate:.1%} ({transitions}/{attempts})"
        return "<b>Portfolio transition success (so far)</b>: N/A (no attempts yet)"


class ProjectStatusElement(TextElement):
    def render(self, model: RdteModel) -> str:  # type: ignore[override]
        focus_id = getattr(model, "focus_researcher_id", -1)
        if not isinstance(focus_id, int):
            try:
                focus_id = int(focus_id)
            except Exception:
                focus_id = -1
        if focus_id < 0 or focus_id >= len(model.researchers):
            return "Focused project: none (set focus_researcher_id to a valid researcher id)"
        r = model.researchers[focus_id]
        stage = (
            r.STAGES[r.current_stage_index]
            if getattr(r, "current_stage_index", None) is not None
            and 0 <= r.current_stage_index < len(r.STAGES)
            else "none"
        )
        attempts = getattr(r, "attempts", 0)
        transitions = getattr(r, "transitions", 0)
        if attempts:
            proj_rate = transitions / attempts
            rate_str = f"{proj_rate:.1%} ({transitions}/{attempts})"
        else:
            rate_str = "N/A (no attempts yet)"
        return (
            "<b>Focused project view</b><br/>"
            f"Id: {focus_id} | Program: {getattr(r, 'program_id', 'NA')} | "
            f"Service: {getattr(r, 'service_component', 'NA')} | "
            f"Domain: {getattr(r, 'domain', 'NA')} | Org: {getattr(r, 'org_type', 'NA')}<br/>"
            f"Stage: {stage} | TRL: {getattr(r, 'trl', 'NA')} | Status: {getattr(r, 'program_status', 'NA')}<br/>"
            f"Project transition success (so far): {rate_str}"
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
        "n_researchers": Slider("Number of researchers", 40, 10, 200, 5),
        "n_policymakers": Slider("Number of policymakers", 10, 1, 40, 1),
        "n_endusers": Slider("Number of end users", 30, 5, 200, 5),
        "funding_rdte": Slider("RDT&E funding level", 1.0, 0.0, 2.0, 0.1),
        "funding_om": Slider("O&M/Proc funding level", 0.5, 0.0, 2.0, 0.1),
        "regime": Choice("Governance regime", "adaptive", choices=["linear", "adaptive", "shock"]),
        "shock_at": Slider("Shock start tick", 80, 0, 500, 5),
        "shock_duration": Slider("Shock duration (ticks)", 20, 0, 200, 5),
        "seed": NumberInput("Random seed", 42),
        "focus_researcher_id": NumberInput("Focused researcher id (-1 = none)", -1),
        # Scenario/category controls derived from data
        "portfolio_focus": Choice(
            "Portfolio focus",
            "Mixed",
            choices=["Mixed", "ISR", "Cyber", "EW", "Space", "Air", "Land", "Maritime"],
        ),
        "service_focus": Choice(
            "Service focus",
            "Joint",
            choices=["Joint", "Army", "Navy", "Air Force", "USMC", "Space Force", "IC"],
        ),
        "org_mix": Choice(
            "Org type mix",
            "Balanced",
            choices=["Balanced", "GovLab-heavy", "Contractor-heavy", "Commercial-heavy"],
        ),
        "funding_pattern": Choice(
            "Funding pattern",
            "ProgramBase",
            choices=["ProgramBase", "POM-heavy", "UFR-heavy", "Partner-heavy"],
        ),
        "alignment_profile": Choice(
            "Priority alignment profile",
            "Medium",
            choices=["Low", "Medium", "High"],
        ),
        "digital_maturity_profile": Choice(
            "Digital maturity / MBSE",
            "Medium",
            choices=["Low", "Medium", "High"],
        ),
        "shock_resilience": Choice(
            "Shock resilience",
            "Medium",
            choices=["Low", "Medium", "High"],
        ),
        "ecosystem_support": Choice(
            "Ecosystem support (labs/industry)",
            "Medium",
            choices=["Low", "Medium", "High"],
        ),
    }

    server = ModularServer(
        RdteModel,
        [HelpElement(), MetricsElement(), TransitionProbabilityElement(), ProjectStatusElement(), adoptions_chart],
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

