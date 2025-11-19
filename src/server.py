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


class StyleElement(TextElement):
    """Inject bespoke CSS to upgrade the Mesa UI without touching vendor templates."""
    def render(self, model: RdteModel) -> str:  # type: ignore[override]
        return """
        <style>
            :root {
                --bg: #f5f7fb;
                --panel: #ffffff;
                --border: #e5e7eb;
                --text: #0f172a;
                --muted: #4b5563;
                --accent: #2563eb;
                --accent-2: #0ea5e9;
                --success: #16a34a;
                --warn: #d97706;
                --danger: #dc2626;
                --radius: 14px;
                --shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
            }
            body {
                font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                background: radial-gradient(circle at 20% 20%, #e8edfb 0, #f5f7fb 35%, #ffffff 70%);
                color: var(--text);
                margin: 0;
            }
            #elements {
                padding: 12px 16px 24px;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            .mesa-text {
                background: var(--panel);
                border-radius: var(--radius);
                border: 1px solid var(--border);
                box-shadow: var(--shadow);
                padding: 14px 16px;
                line-height: 1.4;
            }
            .card-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
                margin-top: 8px;
            }
            .badge {
                display: inline-block;
                padding: 4px 10px;
                border-radius: 999px;
                background: #e0e7ff;
                color: #1e3a8a;
                font-weight: 600;
                font-size: 12px;
                letter-spacing: 0.01em;
            }
            .kpi {
                background: linear-gradient(135deg, #f1f5ff 0%, #ffffff 100%);
                border: 1px solid var(--border);
                border-radius: 12px;
                padding: 10px 12px;
            }
            .kpi-label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }
            .kpi-value { font-size: 22px; font-weight: 700; }
            .pill-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
            .pill {
                padding: 6px 10px;
                border-radius: 10px;
                background: #eef2ff;
                border: 1px solid #e0e7ff;
                font-size: 13px;
            }
            .headline { font-size: 18px; font-weight: 700; margin: 0 0 6px 0; }
            .subhead { color: var(--muted); margin: 0; }
            .section-title { font-weight: 700; margin: 6px 0 4px 0; }
            /* Slider refresh for a cleaner, pro look */
            input[type=range] {
                -webkit-appearance: none;
                height: 4px;
                border-radius: 999px;
                background: linear-gradient(90deg, var(--accent), var(--accent-2));
                outline: none;
            }
            input[type=range]::-webkit-slider-thumb {
                -webkit-appearance: none;
                appearance: none;
                width: 16px;
                height: 16px;
                border-radius: 50%;
                background: #ffffff;
                border: 2px solid var(--accent);
                box-shadow: 0 8px 16px rgba(37, 99, 235, 0.25);
                cursor: pointer;
            }
            input[type=range]::-moz-range-thumb {
                width: 16px;
                height: 16px;
                border-radius: 50%;
                background: #ffffff;
                border: 2px solid var(--accent);
                box-shadow: 0 8px 16px rgba(37, 99, 235, 0.25);
                cursor: pointer;
            }
        </style>
        """


class HelpElement(TextElement):
    def render(self, model: RdteModel) -> str:  # type: ignore[override]
        return (
            "<div class='headline'>RDT&E Transition Lab</div>"
            "<p class='subhead'>Tune populations, funding, and scenario levers to see how governance regimes influence fielding velocity.</p>"
            "<div class='pill-row'>"
            "<span class='pill'>Step: {step}</span>"
            "<span class='pill'>Regime: {regime}</span>"
            "<span class='pill'>Shock window: {shock}</span>"
            "</div>"
            "<div class='section-title'>Quick tips</div>"
            "<ul style='margin: 6px 0 0 16px; padding-left: 12px;'>"
            "<li>Adjust population and funding sliders to change throughput.</li>"
            "<li>Use portfolio/service/org/funding pattern dropdowns to shape the mix.</li>"
            "<li>Set <code>focus_researcher_id</code> to track a single project (-1 = none).</li>"
            "</ul>"
        ).format(
            step=getattr(model.schedule, "time", 0),
            regime=getattr(model, "regime", "adaptive"),
            shock="on" if model.is_in_shock() else "off",
        )


class MetricsElement(TextElement):
    def render(self, model: RdteModel) -> str:  # type: ignore[override]
        attempts = model.metrics.attempts
        transitions = model.metrics.transitions
        rate = (transitions / attempts) if attempts else 0.0
        last = model.metrics.adoptions_per_tick[-1] if model.metrics.adoptions_per_tick else 0
        total = sum(model.metrics.adoptions_per_tick) if model.metrics.adoptions_per_tick else 0
        return (
            "<div class='section-title'>Run metrics</div>"
            "<div class='card-grid'>"
            f"<div class='kpi'><div class='kpi-label'>Transition rate</div><div class='kpi-value'>{rate:.1%}</div></div>"
            f"<div class='kpi'><div class='kpi-label'>Attempts</div><div class='kpi-value'>{attempts}</div></div>"
            f"<div class='kpi'><div class='kpi-label'>Transitions</div><div class='kpi-value'>{transitions}</div></div>"
            f"<div class='kpi'><div class='kpi-label'>Adoptions (last)</div><div class='kpi-value'>{last}</div></div>"
            f"<div class='kpi'><div class='kpi-label'>Adoptions (cum.)</div><div class='kpi-value'>{total}</div></div>"
            "</div>"
        )


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
            "<div class='section-title'>Focused project</div>"
            f"<div class='pill-row'>"
            f"<span class='pill'>Id: {focus_id}</span>"
            f"<span class='pill'>Program: {getattr(r, 'program_id', 'NA')}</span>"
            f"<span class='pill'>Service: {getattr(r, 'service_component', 'NA')}</span>"
            f"<span class='pill'>Domain: {getattr(r, 'domain', 'NA')}</span>"
            f"<span class='pill'>Org: {getattr(r, 'org_type', 'NA')}</span>"
            f"</div>"
            f"<div class='pill-row' style='margin-top:6px;'>"
            f"<span class='pill'>Stage: {stage}</span>"
            f"<span class='pill'>TRL: {getattr(r, 'trl', 'NA')}</span>"
            f"<span class='pill'>Status: {getattr(r, 'program_status', 'NA')}</span>"
            f"<span class='pill'>Project success: {rate_str}</span>"
            f"</div>"
        )


class StageFunnelElement(TextElement):
    def render(self, model: RdteModel) -> str:  # type: ignore[override]
        counts = model._stage_counts()
        stages = ["idle"]
        try:
            if model.researchers:
                stages += list(model.researchers[0].STAGES)
        except Exception:
            stages = ["idle"]
        parts = "".join(
            f"<div class='pill'>{stage}: {counts.get(stage, 0)}</div>"
            for stage in stages
        )
        return "<div class='section-title'>Stage distribution</div><div class='pill-row'>" + parts + "</div>"


class GateContextElement(TextElement):
    def render(self, model: RdteModel) -> str:  # type: ignore[override]
        ctx = getattr(model, "_last_gate_context", {}) or {}
        if not ctx:
            return "<div class='section-title'>Last gate context</div><div class='subhead'>(no gate evaluated yet)</div>"
        pills = "".join(f"<div class='pill'>{k}: {ctx[k]}</div>" for k in sorted(ctx.keys()))
        return "<div class='section-title'>Last gate context</div><div class='pill-row'>" + pills + "</div>"


adoptions_chart = ChartModule(
    [
        {"Label": "adoptions_this_tick", "Color": "#1f77b4"},
        {"Label": "cum_adoptions", "Color": "#2ca02c"},
    ],
    data_collector_name="datacollector",
)

stage_chart = ChartModule(
    [
        {"Label": "stage_feasibility", "Color": "#4c78a8"},
        {"Label": "stage_prototype_demo", "Color": "#9ecae9"},
        {"Label": "stage_functional_test", "Color": "#f58518"},
        {"Label": "stage_vulnerability_test", "Color": "#e45756"},
        {"Label": "stage_operational_test", "Color": "#54a24b"},
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
        [
            StyleElement(),
            HelpElement(),
            MetricsElement(),
            ProjectStatusElement(),
            StageFunnelElement(),
            GateContextElement(),
            adoptions_chart,
            stage_chart,
        ],
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

