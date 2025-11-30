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
import csv
import yaml
from mesa.visualization.modules import ChartModule, TextElement
from mesa.visualization.ModularVisualization import ModularServer
from mesa.visualization.UserParam import Slider, Choice, NumberInput

from .model import RdteModel
from .run_experiment import _load_parameters  # type: ignore


class StyleElement(TextElement):
    """Inject bespoke CSS to upgrade the Mesa UI without touching vendor templates."""
    def render(self, model: RdteModel) -> str:  # type: ignore[override]
        return """
        <style>
            :root {
                --bg: #f7f7f5;
                --panel: #ffffff;
                --border: #d9d9d9;
                --text: #1f2937;
                --muted: #4b5563;
                --accent: #0f766e;     /* teal for color-blind friendly contrast */
                --accent-2: #22c55e;   /* green accent */
                --success: #15803d;
                --warn: #c2410c;
                --danger: #b91c1c;
                --radius: 14px;
                --shadow: 0 10px 24px rgba(17, 24, 39, 0.08);
            }
            body {
                font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
                background: linear-gradient(135deg, #f5f5f5 0%, #ffffff 60%, #f3f7f6 100%);
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
                background: #e5f3f1;
                color: #0f5132;
                font-weight: 600;
                font-size: 12px;
                letter-spacing: 0.01em;
            }
            .kpi {
                background: linear-gradient(135deg, #f5fbf9 0%, #ffffff 100%);
                border: 1px solid #dfe7e3;
                border-radius: 12px;
                padding: 10px 12px;
            }
            .kpi-label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }
            .kpi-value { font-size: 22px; font-weight: 700; }
            .pill-row { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
            .pill {
                padding: 6px 10px;
                border-radius: 10px;
                background: #eef5f3;
                border: 1px solid #d9e6e1;
                font-size: 13px;
            }
            .pill.override {
                background: #fee2e2;
                border: 1px solid #fca5a5;
                color: #7f1d1d;
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
            "<span class='pill'>UI: {ui_mode}</span>"
            "<span class='pill'>Focus: {focus_mode}</span>"
            "</div>"
            "<div class='section-title'>Quick tips</div>"
            "<ul style='margin: 6px 0 0 16px; padding-left: 12px;'>"
            "<li>Adjust population and funding sliders to change throughput.</li>"
            "<li>Use portfolio/service/org/funding pattern dropdowns to shape the mix.</li>"
            "<li>Set trend start/end ticks to view adoption trends for a custom window.</li>"
            "<li>Focus a project (prefer <code>focus_program_id</code>) and open Advanced mode to inspect full fields and probability previews.</li>"
            "<li>Use selection mode (Random/Best/Worst/Manual) or set <code>focus_researcher_id</code> (-1 = none).</li>"
            "</ul>"
        ).format(
            step=getattr(model.schedule, "time", 0),
            regime=getattr(model, "regime", "adaptive"),
            shock="on" if model.is_in_shock() else "off",
            ui_mode=getattr(model, "ui_mode", "Standard"),
            focus_mode=getattr(model, "focus_selection_mode", "Manual"),
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
        # Resolve focus by program_id first, then fallback to numeric index
        target = None
        focus_pid = str(getattr(model, "focus_program_id", "") or "").strip()
        if focus_pid:
            for r in model.researchers:
                if str(getattr(r, "program_id", "")).strip() == focus_pid:
                    target = r
                    break
        if target is None:
            focus_id = getattr(model, "focus_researcher_id", -1)
            if not isinstance(focus_id, int):
                try:
                    focus_id = int(focus_id)
                except Exception:
                    focus_id = -1
            if 0 <= focus_id < len(model.researchers):
                target = model.researchers[focus_id]
        if target is None:
            return "Focused project: none (set focus_program_id or focus_researcher_id to a valid value)"
        r = target
        focus_id = getattr(r, "unique_id", -1)
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
        advanced = str(getattr(model, "ui_mode", "Standard")).lower().startswith("adv")
        detail_html = ""
        if advanced:
            # Detect overrides vs. loaded data for highlighting
            def override_cls(val_name: str, current_val) -> str:
                # If what-if quality delta is applied, highlight quality and derived penalties
                if val_name in {"gao_penalty", "perf_penalty", "quality"} and getattr(model, "what_if_quality_delta", 0.0) != 0:
                    return "pill override"
                # Could be extended with raw source comparison if source stored; for now only what-if
                return "pill"
            q_class = override_cls("quality", getattr(r, "quality", 0.0))
            gao_class = override_cls("gao_penalty", getattr(r, "gao_penalty", 0.0))
            perf_class = override_cls("perf_penalty", getattr(r, "perf_penalty", 0.0))
            exec_class = "pill"
            test_class = "pill"
            domain_class = "pill"
            class_class = "pill"
            detail_html = (
                "<div class='section-title'>Project details</div>"
                "<div class='pill-row'>"
                f"<span class='pill'>Authority: {getattr(r, 'authority', 'NA')}</span>"
                f"<span class='pill'>Funding source: {getattr(r, 'funding_source', 'NA')}</span>"
                f"<span class='pill'>Budget activity: {getattr(r, 'budget_activity', 'NA')}</span>"
                f"<span class='pill'>Entity: {getattr(r, 'entity_id', 'NA')}</span>"
                f"<span class='pill'>Vendor: {getattr(r, 'vendor_id', 'NA')}</span>"
                "</div>"
                "<div class='pill-row'>"
                f"<span class='{gao_class}'>GAO penalty: {getattr(r, 'gao_penalty', 0.0):.2f}</span>"
                f"<span class='{perf_class}'>Vendor risk: {getattr(r, 'perf_penalty', 0.0):.2f}</span>"
                f"<span class='pill'>Sponsor strength: {getattr(r, 'sponsor_authority', 0.0):.2f}</span>"
                f"<span class='{exec_class}'>Exec capacity: {getattr(r, 'executing_capacity', 0.0):.2f}</span>"
                f"<span class='{test_class}'>Test capacity: {getattr(r, 'test_capacity', 0.0):.2f}</span>"
                "</div>"
                "<div class='pill-row'>"
                f"<span class='{domain_class}'>Domain alignment: {getattr(r, 'domain_alignment', 0.0):.2f}</span>"
                f"<span class='{class_class}'>Class band: {getattr(r, 'classification_penalty', 0.0):.2f}</span>"
                f"<span class='{q_class}'>Digital maturity: {getattr(r, 'digital_maturity_score', 0.0):.2f}</span>"
                f"<span class='{q_class}'>MBSE: {getattr(r, 'mbse_coverage', 0.0):.2f}</span>"
                "</div>"
            )
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
            f"</div>{detail_html}"
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


class TrendElement(TextElement):
    def render(self, model: RdteModel) -> str:  # type: ignore[override]
        start = max(0, int(getattr(model, "trend_start_tick", 0)))
        end = max(start, int(getattr(model, "trend_end_tick", start)))
        series = getattr(model.metrics, "adoptions_per_tick", [])
        end = min(end, len(series))
        window = series[start:end] if end > start else []
        total = sum(window) if window else 0
        avg = (total / len(window)) if window else 0.0
        return (
            "<div class='section-title'>Trend window</div>"
            f"<div class='pill-row'>"
            f"<span class='pill'>Start tick: {start}</span>"
            f"<span class='pill'>End tick: {end}</span>"
            f"<span class='pill'>Adoptions: {total}</span>"
            f"<span class='pill'>Avg/tick: {avg:.2f}</span>"
            "</div>"
        )


class ProbabilityElement(TextElement):
    def render(self, model: RdteModel) -> str:  # type: ignore[override]
        # Resolve focus by program_id first, then fallback to numeric index
        r = None
        focus_pid = str(getattr(model, "focus_program_id", "") or "").strip()
        if focus_pid:
            for cand in model.researchers:
                if str(getattr(cand, "program_id", "")).strip() == focus_pid:
                    r = cand
                    break
        if r is None:
            focus_id = getattr(model, "focus_researcher_id", -1)
            if not isinstance(focus_id, int):
                try:
                    focus_id = int(focus_id)
                except Exception:
                    focus_id = -1
            if 0 <= focus_id < len(model.researchers):
                r = model.researchers[focus_id]
        if r is None:
            return "<div class='section-title'>Probability preview</div><div class='subhead'>Set focus_program_id or focus_researcher_id to preview.</div>"
        base_probs = model.preview_transition_probability(r, quality_delta=0.0)
        delta = float(getattr(model, "what_if_quality_delta", 0.0))
        what_if_probs = model.preview_transition_probability(r, quality_delta=delta)

        def fmt(prob: float) -> str:
            return f"{max(0.0, min(1.0, prob)):.1%}"

        custom = getattr(model, "custom_project_enabled", False)
        custom_probs = model.custom_project_probability() if custom else {}

        return (
            "<div class='section-title'>Probability preview</div>"
            f"<div class='subhead'>Program: {getattr(r, 'program_id', 'NA')} | Stage: {base_probs.get('stage', 'NA')} | What-if quality delta: {delta:+.2f}</div>"
            "<div class='pill-row'>"
            f"<span class='pill'>Funding: {fmt(base_probs.get('funding', 0.0))} -> {fmt(what_if_probs.get('funding', 0.0))}</span>"
            f"<span class='pill'>Contracting: {fmt(base_probs.get('contracting', 0.0))} -> {fmt(what_if_probs.get('contracting', 0.0))}</span>"
            f"<span class='pill'>Test: {fmt(base_probs.get('test', 0.0))} -> {fmt(what_if_probs.get('test', 0.0))}</span>"
            f"<span class='pill'>Adoption: {fmt(base_probs.get('adoption', 0.0))} -> {fmt(what_if_probs.get('adoption', 0.0))}</span>"
            "</div>"
            "<div class='pill-row'>"
            f"<span class='pill'>Overall: {fmt(base_probs.get('overall', 0.0))} -> {fmt(what_if_probs.get('overall', 0.0))}</span>"
            "</div>"
            + (
                "<div class='section-title'>Custom project (preview only unless persist is ON)</div>"
                "<div class='subhead'>Preview values only; not part of the live run unless persist is ON.</div>"
                f"<div class='subhead'>Stage: {custom_probs.get('stage', 'n/a')} | Quality: {getattr(model, 'custom_project_quality', 0.0):.2f}</div>"
                "<div class='pill-row'>"
                f"<span class='pill override'>Funding: {fmt(custom_probs.get('funding', 0.0))}</span>"
                f"<span class='pill override'>Contracting: {fmt(custom_probs.get('contracting', 0.0))}</span>"
                f"<span class='pill override'>Test: {fmt(custom_probs.get('test', 0.0))}</span>"
                f"<span class='pill override'>Adoption: {fmt(custom_probs.get('adoption', 0.0))}</span>"
                "</div>"
                "<div class='pill-row'>"
                f"<span class='pill override'>Overall: {fmt(custom_probs.get('overall', 0.0))}</span>"
                "</div>"
            ) if custom_probs else ""
        )


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


def _load_server_params(config_path: str | None = None) -> dict:
    """Load parameters.yaml to hydrate data/penalty/gate configs for the GUI."""
    params = _load_parameters(config_path or os.path.join(os.getcwd(), "parameters.yaml"))
    return params or {}


def launch(port: int = 8521, host: str = "127.0.0.1", open_browser: bool = False, config_path: str | None = None):
    params_yaml = _load_server_params(config_path)
    penalty_config = params_yaml.get("penalties", {}) or {}
    gates_config = params_yaml.get("gates", {}) or {}
    agent_config = params_yaml.get("agents", {}) or {}
    data_config = params_yaml.get("data", {}) or {}
    model_config = params_yaml.get("model", {}) or {}

    def _program_choices() -> list[str]:
        """Collect program_id choices from program_entity_roles.csv if available."""
        path = data_config.get("program_entity_roles_csv") or os.path.join("data", "program_entity_roles.csv")
        ids = set()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        pid = (row.get("program_id") or "").strip()
                        if pid:
                            ids.add(pid)
            except Exception:
                ids = set()
        if not ids:
            ids = {
                "PRG-ISR-001",
                "PRG-CYB-002",
                "PRG-AI-003",
                "PRG-SAT-004",
                "PRG-EW-005",
                "PRG-MAR-006",
                "PRG-GEO-007",
                "PRG-CBRN-008",
                "PRG-UAV-009",
                "PRG-SIG-010",
            }
        choices = [""] + sorted(ids)
        return choices

    params = {
        "n_researchers": Slider("Number of researchers", 40, 10, 200, 5),
        "n_policymakers": Slider("Number of policymakers", 10, 1, 40, 1),
        "n_endusers": Slider("Number of end users", 30, 5, 200, 5),
        "funding_rdte": Slider("RDT&E funding level", 1.0, 0.0, 2.0, 0.1),
        "funding_om": Slider("O&M/Proc funding level", 0.5, 0.0, 2.0, 0.1),
        "regime": Choice("Governance regime", "adaptive", choices=["linear", "adaptive", "shock"]),
        "shock_at": Slider("Shock start tick", 80, 0, 500, 5),
        "shock_duration": Slider("Shock duration (ticks)", 20, 0, 200, 5),
        "seed": NumberInput("Random seed", int(model_config.get("seed", 42))),
        "testing_profile": Choice("Testing profile", model_config.get("testing_profile", "demo"), choices=["demo", "production"]),
        "focus_researcher_id": NumberInput("Focused researcher index (-1 = none)", -1),
        "focus_program_id": Choice("Focused program id (optional)", "", choices=_program_choices()),
        "focus_selection_mode": Choice("Focus selection mode", "Random", choices=["Random", "Best", "Worst", "Manual"]),
        "trend_start_tick": NumberInput("Trend window start tick", 0),
        "trend_end_tick": NumberInput("Trend window end tick", 200),
        "what_if_quality_delta": Slider("What-if quality delta (preview only)", 0.0, -0.3, 0.3, 0.01),
        "ui_mode": Choice("UI mode", "Standard", choices=["Standard", "Advanced"]),
        # Custom project simulation (preview only; does not alter agents)
        "custom_project_enabled": Choice("Custom project simulation", "Off", choices=["Off", "On"]),
        "custom_project_stage": Choice("Custom stage", "feasibility", choices=["feasibility", "prototype_demo", "functional_test", "vulnerability_test", "operational_test"]),
        "custom_project_quality": Slider("Custom quality (0-1)", 0.6, 0.0, 1.0, 0.01),
        "custom_project_gao_penalty": Slider("Custom GAO penalty (0-1)", 0.0, 0.0, 1.0, 0.01),
        "custom_project_perf_penalty": Slider("Custom vendor/perf penalty (0-1)", 0.0, 0.0, 1.0, 0.01),
        "custom_project_domain_alignment": Slider("Custom domain alignment (0-1)", 0.5, 0.0, 1.0, 0.01),
        "custom_project_exec_capacity": Slider("Custom exec capacity (0-1.2)", 0.5, 0.0, 1.2, 0.01),
        "custom_project_test_capacity": Slider("Custom test capacity (0-1.2)", 0.5, 0.0, 1.2, 0.01),
        "custom_project_class_penalty": Slider("Custom classification penalty (0-0.3)", 0.0, 0.0, 0.3, 0.01),
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
            TrendElement(),
            ProjectStatusElement(),
            ProbabilityElement(),
            StageFunnelElement(),
            GateContextElement(),
            adoptions_chart,
            stage_chart,
        ],
        "RDT&E ABM",
        {
            **params,
            "penalty_config": penalty_config,
            "gate_config": gates_config,
            "data_config": data_config,
            "agent_config": agent_config,
        },
    )
    print(
        f"[server] config={config_path or 'parameters.yaml'} | testing_profile={model_config.get('testing_profile', 'production')} "
        f"| priors_enabled={penalty_config.get('enable_priors', True)} "
        f"| prior_weights={penalty_config.get('prior_weights_by_gate', {})}"
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

