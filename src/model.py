"""
Core Mesa model.
Owns the agent population, scheduling, regime/shock state, and
exposes helper functions for policy gates and adoption evaluation.
"""
from __future__ import annotations

from datetime import datetime
from mesa import Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
from typing import List, Dict, Any, Optional
import csv
from pathlib import Path
import logging

from .agents import ResearcherAgent, PolicymakerAgent, EndUserAgent
from . import policies
from .metrics import MetricTracker, PenaltyBook, EventLogger
from .data_loader import (
    load_gao_penalties,
    load_shock_events,
    load_vendor_evaluations,
    load_collaboration_bonus,
    load_rdte_entities,
    load_program_entity_roles,
    derive_role_metrics,
    load_closed_projects,
)


class RdteModel(Model):
    """
    ABM of RDT&E transitions under different governance regimes.
    Parameters
    ----------
    n_researchers, n_policymakers, n_endusers : int
        Population sizes per role.
    funding_rdte, funding_om : float
        Normalized budget "weights" feeding funding_gate decisions.
    regime : {"linear", "adaptive", "shock"}
        Select governance style / shock testing.
    shock_at : int
        Simulation step when a shock starts (shock duration is hard‑coded to 20 steps for simplicity).
    seed : int | None
        Randomness seed for reproducibility.
    """
    def __init__(self,
                 n_researchers: int = 40,
                 n_policymakers: int = 10,
                 n_endusers: int = 30,
                 funding_rdte: float = 1.0,
                 funding_om: float = 0.5,
                 regime: str = "linear",
                 shock_at: int = 80,
                 seed: int | None = None,
                 shock_duration: int = 20,
                 labs_csv: Optional[str] = None,
                 rdte_csv: Optional[str] = None,
                 penalty_config: Optional[Dict[str, Any]] = None,
                 gate_config: Optional[Dict[str, Any]] = None,
                 events_path: Optional[str] = None,
                 alignment_profile: str = "Medium",
                 digital_maturity_profile: str = "Medium",
                 shock_resilience: str = "Medium",
                 ecosystem_support: str = "Medium",
                 portfolio_focus: str = "Mixed",
                 service_focus: str = "Joint",
                 org_mix: str = "Balanced",
                 funding_pattern: str = "ProgramBase",
                 focus_researcher_id: int = -1,
                 focus_program_id: str = "",
                 focus_selection_mode: str = "Random",
                 data_config: Optional[Dict[str, Any]] = None,
                 agent_config: Optional[Dict[str, Any]] = None,
                 trend_start_tick: int = 0,
                 trend_end_tick: int = 200,
                 ui_mode: str = "Standard",
                 what_if_quality_delta: float = 0.0,
                 custom_project_enabled: str | bool = False,
                 custom_project_stage: str = "feasibility",
                 custom_project_quality: float = 0.6,
                 custom_project_gao_penalty: float = 0.0,
                 custom_project_perf_penalty: float = 0.0,
                 custom_project_domain_alignment: float = 0.5,
                 custom_project_exec_capacity: float = 0.5,
                 custom_project_test_capacity: float = 0.5,
                 custom_project_class_penalty: float = 0.0):
        super().__init__(seed=seed)

        # Scheduler drives agent step order each tick
        self.schedule = RandomActivation(self)

        # Keep a local RNG (Mesa also seeds its own); using both is fine for a toy model
        
        

        # Model‑level state
        self.regime = regime
        self.shock_at = int(shock_at)
        self.shock_duration = int(shock_duration)
        self.funding_rdte = float(funding_rdte)
        self.funding_om = float(funding_om)
        self.metrics = MetricTracker()
        self._in_shock = False
        # Scenario-level knobs derived from data categories
        self.alignment_profile = str(alignment_profile)
        self.digital_maturity_profile = str(digital_maturity_profile)
        self.shock_resilience = str(shock_resilience)
        self.ecosystem_support = str(ecosystem_support)
        self.portfolio_focus = str(portfolio_focus)
        self.service_focus = str(service_focus)
        self.org_mix = str(org_mix)
        self.funding_pattern = str(funding_pattern)
        self.focus_researcher_id = int(focus_researcher_id)
        self.focus_program_id = str(focus_program_id or "")
        self.focus_selection_mode = str(focus_selection_mode or "Random")
        self.trend_start_tick = int(trend_start_tick)
        self.trend_end_tick = int(trend_end_tick)
        self.ui_mode = str(ui_mode)
        self.what_if_quality_delta = float(what_if_quality_delta)
        self.custom_project_enabled = str(custom_project_enabled).lower() in {"true", "1", "yes", "on"}
        self.custom_project_stage = str(custom_project_stage or "feasibility")
        self.custom_project_quality = float(custom_project_quality)
        self.custom_project_gao_penalty = float(custom_project_gao_penalty)
        self.custom_project_perf_penalty = float(custom_project_perf_penalty)
        self.custom_project_domain_alignment = float(custom_project_domain_alignment)
        self.custom_project_exec_capacity = float(custom_project_exec_capacity)
        self.custom_project_test_capacity = float(custom_project_test_capacity)
        self.custom_project_class_penalty = float(custom_project_class_penalty)
        self.labs: List[Dict[str, Any]] = self._load_labs(labs_csv)
        self.rdte_fy26: List[Dict[str, Any]] = self._load_rdte(rdte_csv)
        # Map of program_id -> researcher will be populated after agent creation
        self.program_index: Dict[str, ResearcherAgent] = {}
        self.gate_config: Dict[str, Any] = gate_config or {}
        self._logger = logging.getLogger(__name__)
        self._events: Optional[EventLogger] = EventLogger(events_path) if events_path else None
        # Last gate context (populated by policies to enrich event logs)
        self._last_gate_context: Dict[str, Any] = {}
        # Data collector for Mesa visualization (ChartModule expects this attribute)
        self.datacollector: DataCollector = DataCollector(
            model_reporters={
                "adoptions_this_tick": lambda m: (m.metrics.adoptions_per_tick[-1]
                                                   if m.metrics.adoptions_per_tick else 0),
                "cum_adoptions": lambda m: (sum(m.metrics.adoptions_per_tick)
                                             if m.metrics.adoptions_per_tick else 0),
                "stage_idle": lambda m: m._stage_counts().get("idle", 0),
                "stage_feasibility": lambda m: m._stage_counts().get("feasibility", 0),
                "stage_prototype_demo": lambda m: m._stage_counts().get("prototype_demo", 0),
                "stage_functional_test": lambda m: m._stage_counts().get("functional_test", 0),
                "stage_vulnerability_test": lambda m: m._stage_counts().get("vulnerability_test", 0),
                "stage_operational_test": lambda m: m._stage_counts().get("operational_test", 0),
            }
        )
        # Penalties setup
        pc = penalty_config or {}
        self.penalties = PenaltyBook(
            per_failure=float(pc.get("per_failure", 0.05)),
            max_penalty=float(pc.get("max_penalty", 0.3)),
            decay=float(pc.get("decay", 0.0)),
        )
        self.penalty_axes_by_gate: Dict[str, List[str]] = pc.get("axes_by_gate", {
            "funding": ["researcher", "funding_source", "org_type", "portfolio"],
            "contracting": ["researcher", "org_type", "portfolio"],
            "test": ["researcher", "domain", "kinetic_category", "portfolio"],
            "legal": ["researcher", "authority", "domain", "kinetic_category", "portfolio"],
            "adoption": ["researcher", "domain", "portfolio"],
        })
        self.gao_penalty_scale = float(pc.get("gao_penalty_scale", 0.02))
        self.perf_penalty_scale = float(pc.get("perf_penalty_scale", 0.02))
        self.ecosystem_scale = float(pc.get("ecosystem_scale", 0.05))
        self.gao_weight = float(pc.get("gao_weight", 0.5))
        self.vendor_weight = float(pc.get("vendor_weight", 0.4))

        self.data_config = data_config or {}
        try:
            current_year = int(self.data_config.get("current_year", datetime.now().year))
        except Exception:
            current_year = datetime.now().year
        self.gaop: Dict[str, float] = load_gao_penalties(self.data_config.get("gao_findings_csv"))
        self.shocks: List[Dict[str, object]] = load_shock_events(self.data_config.get("shock_events_csv"))
        self.vendor_penalty: Dict[str, float]
        self.program_perf_penalty: Dict[str, float]
        self.program_perf_penalty, self.vendor_penalty = load_vendor_evaluations(
            self.data_config.get("program_vendor_evals_csv")
        )
        self.ecosystem_bonus: Dict[str, float] = load_collaboration_bonus(
            self.data_config.get("collaboration_network_csv"),
            current_year,
        )
        self.entity_master: Dict[str, Dict[str, Any]] = load_rdte_entities(self.data_config.get("rdte_entities_csv"))
        self.program_roles: Dict[str, Dict[str, Any]] = load_program_entity_roles(
            self.data_config.get("program_entity_roles_csv"),
            self.entity_master,
        )
        self.role_metrics: Dict[str, Dict[str, float]] = derive_role_metrics(
            self.program_roles,
            self._program_domains(),
        )
        self.closed_projects: List[Dict[str, Any]]
        self.closed_priors: Dict[str, Dict[str, float]]
        self.closed_projects, self.closed_priors = load_closed_projects(self.data_config.get("closed_projects_csv"))

        # Agent configuration overrides (from parameters.yaml -> agents.*)
        ag_cfg = agent_config or {}
        rcfg = (ag_cfg.get("researcher") or ag_cfg.get("researchers") or {})
        pcfg = (ag_cfg.get("policymaker") or ag_cfg.get("policymakers") or {})
        ecfg = (ag_cfg.get("enduser") or ag_cfg.get("endusers") or {})

        # --- Create agents and register with scheduler ---
        # Optionally map researchers onto RDT&E programs (if any rows loaded)
        rdte_programs: List[Dict[str, Any]] = list(self.rdte_fy26) if self.rdte_fy26 else []
        self.researchers: List[ResearcherAgent] = []
        for i in range(n_researchers):
            rdte_row = rdte_programs[i % len(rdte_programs)] if rdte_programs else None
            proto_rate = float(rcfg.get("prototype_rate", 0.05))
            learn_rate = float(rcfg.get("learning_rate", 0.1))
            a = ResearcherAgent(i, self, prototype_rate=proto_rate, learning_rate=learn_rate, rdte_program=rdte_row)
            self.schedule.add(a)
            self.researchers.append(a)
            entity_id = getattr(a, "entity_id", getattr(a, "program_id", ""))
            vendor_id = getattr(a, "vendor_id", "")
            program_id = getattr(a, "program_id", "")
            a.gao_penalty = self.gaop.get(program_id, 0.0)
            perf_base = self.program_perf_penalty.get(program_id, 0.0)
            vendor_bonus = self.vendor_penalty.get(vendor_id, 0.0)
            a.perf_penalty = min(1.0, perf_base + vendor_bonus)
            a.ecosystem_bonus = self.ecosystem_bonus.get(entity_id, 0.0)
            a.roles = self.program_roles.get(program_id, {})
            rm = self.role_metrics.get(program_id, {}) if isinstance(self.role_metrics, dict) else {}
            a.sponsor_authority = rm.get("sponsor_authority", 0.8)
            a.executing_capacity = rm.get("executing_capacity", 0.5)
            a.test_capacity = rm.get("test_capacity", 0.5)
            a.domain_alignment = rm.get("domain_alignment", 0.5)
            a.classification_penalty = rm.get("classification_penalty", 0.0)
            a.transition_partners = rm.get("transition_partners", 0.0)
            # Index by program_id if present
            if isinstance(program_id, str) and program_id:
                # Last writer wins if duplicates; this is acceptable for a coarse dependency model
                self.program_index[program_id] = a

        offset = n_researchers
        self.policymakers: List[PolicymakerAgent] = []
        for i in range(n_policymakers):
            agility = float(pcfg.get("allocation_agility", 0.1))
            rigidity = float(pcfg.get("oversight_rigidity", 0.8))
            a = PolicymakerAgent(offset + i, self, allocation_agility=agility, oversight_rigidity=rigidity)
            self.schedule.add(a)
            self.policymakers.append(a)

        offset += n_policymakers
        self.endusers: List[EndUserAgent] = []
        for i in range(n_endusers):
            adoption_threshold = float(ecfg.get("adoption_threshold", 0.6))
            feedback_strength = float(ecfg.get("feedback_strength", 0.4))
            a = EndUserAgent(offset + i, self, adoption_threshold=adoption_threshold, feedback_strength=feedback_strength)
            self.schedule.add(a)
            self.endusers.append(a)

        # Apply initial focus selection (random/best/worst/manual)
        try:
            self._apply_focus_selection()
        except Exception:
            pass

    # ---- Policy gates (delegation to policies.py) ----
    def policy_gate_allocation(self, researcher: ResearcherAgent) -> bool:
        """Return True if funding passes this step for the given researcher."""
        return policies.funding_gate(self, researcher)

    def policy_gate_oversight(self, researcher: ResearcherAgent) -> bool:
        """Return True if oversight passes this step for the given researcher."""
        return policies.oversight_gate(self, researcher)

    # Extended gates for stage pipeline
    def policy_gate_funding(self, stage: str, researcher: ResearcherAgent) -> bool:
        return policies.funding_gate_stage(self, researcher, stage)

    def policy_gate_legal(self, researcher: ResearcherAgent) -> str:
        return policies.legal_review_gate(self, researcher)

    def policy_gate_contracting(self, researcher: ResearcherAgent) -> bool:
        return policies.contracting_gate(self, researcher)

    def policy_gate_test(self, stage: str, researcher: ResearcherAgent, legal_status: str) -> bool:
        return policies.test_gate(self, researcher, stage, legal_status)

    # ---- Penalty helpers ----
    def _penalty_keys(self, gate: str, researcher: ResearcherAgent, stage: Optional[str] = None) -> List[str]:
        axes = self.penalty_axes_by_gate.get(gate, ["researcher"])
        keys: List[str] = []
        for a in axes:
            if a == "researcher":
                keys.append(f"researcher:{researcher.unique_id}")
            elif a == "domain":
                keys.append(f"domain:{getattr(researcher, 'domain', 'NA')}")
            elif a == "org_type":
                keys.append(f"org:{getattr(researcher, 'org_type', 'NA')}")
            elif a == "funding_source":
                keys.append(f"funding:{getattr(researcher, 'funding_source', 'NA')}")
            elif a == "authority":
                keys.append(f"authority:{getattr(researcher, 'authority', 'NA')}")
            elif a == "kinetic_category":
                keys.append(f"kinetic:{getattr(researcher, 'kinetic_category', 'NA')}")
            elif a == "intel_discipline":
                keys.append(f"intel:{getattr(researcher, 'intel_discipline', 'NA')}")
            elif a == "stage" and stage is not None:
                keys.append(f"stage:{stage}")
            elif a == "portfolio":
                keys.append(f"portfolio:{getattr(researcher, 'portfolio', 'NA')}")
        return keys

    def penalty_factor(self, gate: str, researcher: ResearcherAgent, stage: Optional[str] = None) -> float:
        return self.penalties.factor_for(self._penalty_keys(gate, researcher, stage))

    def penalty_record_failure(self, gate: str, researcher: ResearcherAgent, stage: Optional[str] = None) -> None:
        self.penalties.bump(self._penalty_keys(gate, researcher, stage))

    def apply_gao_modifier(self, base_prob: float, program: ResearcherAgent) -> float:
        """
        Down-weight a base probability using the program's GAO penalty.
        penalty is normalized [0,1]; gao_weight controls sensitivity.
        """
        try:
            penalty = float(getattr(program, "gao_penalty", 0.0))
        except Exception:
            penalty = 0.0
        effective = max(0.0, self.gao_weight * penalty)
        return max(0.0, min(1.0, base_prob * (1.0 - effective)))

    def preview_transition_probability(self, researcher: ResearcherAgent, quality_delta: float | None = None) -> Dict[str, float]:
        """
        Estimate a one-step transition probability (no random draw).
        quality_delta supports UI "what-if" previews without mutating the agent.
        """
        delta = float(self.what_if_quality_delta if quality_delta is None else quality_delta)
        try:
            return policies.estimate_transition_probability(self, researcher, quality_delta=delta)
        except Exception:
            return {"stage": "NA", "funding": 0.0, "contracting": 0.0, "test": 0.0, "adoption": 0.0, "overall": 0.0}

    def custom_project_probability(self) -> Dict[str, float]:
        """Simulate a custom project probability without altering the live agents."""
        if not self.custom_project_enabled:
            return {}
        # Minimal stub with required attributes for policy helpers
        class _Stub:
            STAGES = ResearcherAgent.STAGES
            def __init__(self, model: "RdteModel"):
                self.model = model
                self.program_id = "CUSTOM"
                self.entity_id = "CUSTOM"
                self.vendor_id = ""
                self.domain = "Custom"
                self.portfolio = "Custom"
                self.org_type = "Custom"
                self.budget_activity = "BA3"
                self.funding_source = "ProgramBase"
                self.lab_support_factor = 1.0
                self.industry_support_factor = 1.0
                self.authority_alignment_score = 0.5
                self.priority_alignment_service = 0.5
                self.shock_sensitivity = 0.5
                self.program_status = "Active"
                self.stage_enter_tick = getattr(model.schedule, "time", 0)
                self.roles = {}
                self.stage_gate_start = model.custom_project_stage
                self.current_stage_index = self.STAGES.index(model.custom_project_stage) if model.custom_project_stage in self.STAGES else 0
                self.trl = 4
                self.gao_penalty = model.custom_project_gao_penalty
                self.perf_penalty = model.custom_project_perf_penalty
                self.domain_alignment = model.custom_project_domain_alignment
                self.sponsor_authority = 0.8
                self.executing_capacity = model.custom_project_exec_capacity
                self.test_capacity = model.custom_project_test_capacity
                self.classification_penalty = model.custom_project_class_penalty
                self.digital_maturity_score = 0.5
                self.mbse_coverage = 0.5
                self.priority_alignment_nds = 0.5
                self.priority_alignment_ccmd = 0.5
                self.priority_alignment_service = 0.5
                self.authority = "Title10"
                self.kinetic_category = "NonKinetic"
                self.intel_discipline = ""
                self.quality = model.custom_project_quality
                self.stage = self.STAGES[self.current_stage_index]
                self.legal_status = "not_conducted"
        stub = _Stub(self)
        probs = policies.estimate_transition_probability(self, stub, quality_delta=0.0)
        return probs

    def empirical_prior(self, researcher: ResearcherAgent) -> float:
        """
        Retrieve an empirical transition prior based on closed_projects.csv.
        Uses domain, authority, vendor risk bucket, GAO severity bucket, and program id.
        """
        if not getattr(self, "closed_priors", None):
            return 0.5
        pri = self.closed_priors
        scores: List[float] = []

        domain = str(getattr(researcher, "domain", "") or getattr(researcher, "portfolio", "") or "")
        if domain and domain in pri.get("domain", {}):
            scores.append(pri["domain"][domain])

        auth = str(getattr(researcher, "authority", "") or getattr(researcher, "authority_flags", "") or "")
        if auth and auth in pri.get("authority", {}):
            scores.append(pri["authority"][auth])

        # Vendor risk bucket derived from current perf penalty
        risk = max(0.0, min(1.0, float(getattr(researcher, "perf_penalty", 0.0))))
        if risk <= 0.3:
            rb = "low"
        elif risk <= 0.6:
            rb = "medium"
        else:
            rb = "high"
        if rb in pri.get("vendor_bucket", {}):
            scores.append(pri["vendor_bucket"][rb])

        # GAO severity bucket derived from gao_penalty
        gpen = max(0.0, min(1.0, float(getattr(researcher, "gao_penalty", 0.0))))
        if gpen <= 0.2:
            gb = "0-1"
        elif gpen <= 0.4:
            gb = "2"
        elif gpen <= 0.6:
            gb = "3"
        elif gpen <= 0.8:
            gb = "4"
        else:
            gb = "5+"
        if gb in pri.get("gao_bucket", {}):
            scores.append(pri["gao_bucket"][gb])

        pid = str(getattr(researcher, "program_id", "") or "")
        if pid and pid in pri.get("program", {}):
            scores.append(pri["program"][pid])

        if scores:
            return sum(scores) / len(scores)
        return float(pri.get("overall_rate", 0.5))

    def _apply_focus_selection(self) -> None:
        """Set the focused program/agent based on selection mode (random/best/worst/manual)."""
        if not self.researchers:
            return
        mode = str(getattr(self, "focus_selection_mode", "Manual") or "Manual").lower()
        selected = None
        if mode == "random":
            selected = self.random.choice(self.researchers)
        elif mode in {"best", "worst"}:
            scored = []
            for r in self.researchers:
                try:
                    p = self.preview_transition_probability(r).get("overall", 0.0)
                except Exception:
                    p = 0.0
                scored.append((p, r))
            if scored:
                scored.sort(key=lambda x: x[0])
                selected = scored[-1][1] if mode == "best" else scored[0][1]
        else:  # manual: keep explicit selections if valid
            pid = (self.focus_program_id or "").strip()
            if pid and pid in self.program_index:
                selected = self.program_index[pid]
            elif 0 <= self.focus_researcher_id < len(self.researchers):
                selected = self.researchers[self.focus_researcher_id]

        if selected is None:
            selected = self.random.choice(self.researchers)
        try:
            self.focus_program_id = str(getattr(selected, "program_id", "") or "")
        except Exception:
            self.focus_program_id = ""
        try:
            self.focus_researcher_id = int(getattr(selected, "unique_id", -1))
        except Exception:
            self.focus_researcher_id = -1

    # ---- Environment helpers ----
    def environmental_signal(self, researcher: ResearcherAgent | None = None) -> float:
        """
        Small nudge capturing policy headwinds or operational pull.
        Tuned per regime to make differences measurable without dominating quality.
        """
        base = 0.0
        if self.regime == "adaptive":
            base = 0.1    # positive pull from fast feedback
        elif self.regime == "linear":
            base = -0.05  # mild headwind from rigid processes
        else:  # shock regime
            base = -0.1 if self.is_in_shock() else 0.0

        # Add alignment-based bias if researcher provided (maps 0..1 -> -0.05..+0.05)
        if researcher is not None:
            align = getattr(researcher, "alignment_score", 0.5)
            base += 0.05 * (2.0 * align - 1.0)
            # Adoption penalty reduces signal with accumulated failures
            adopt_factor = self.penalty_factor("adoption", researcher)
            base -= 0.05 * (1.0 - adopt_factor)
        # Small bonus if labs dataset is present (represents ecosystem support)
        if getattr(self, "labs", None):
            try:
                if len(self.labs) > 0:
                    base += 0.01
            except Exception:
                pass
        return base

    def _stage_counts(self) -> Dict[str, int]:
        """Return counts of researchers by current stage (or idle if no candidate)."""
        counts = {k: 0 for k in ["idle"] + ResearcherAgent.STAGES}
        for r in self.researchers:
            idx = getattr(r, "current_stage_index", None)
            if idx is None:
                counts["idle"] += 1
            elif 0 <= idx < len(ResearcherAgent.STAGES):
                counts[ResearcherAgent.STAGES[idx]] += 1
        return counts

    # ---- Data loading helpers ----
    def _load_labs(self, labs_csv: Optional[str]) -> List[Dict[str, Any]]:
        """
        Load labs/hubs locations.

        If an explicit path is provided and exists, use it. If no path is
        provided or the file is missing, fall back to the shipped
        `data/templates/labs_template.csv` when present so the model has a
        small but non-empty ecosystem dataset out of the box.
        """
        try:
            path: Optional[Path] = None
            if labs_csv:
                candidate = Path(labs_csv)
                if candidate.exists():
                    path = candidate
                else:
                    logging.getLogger(__name__).warning(
                        f"Labs CSV not found at {candidate}; falling back to data/templates/labs_template.csv if available."
                    )
            if path is None:
                template = Path("data") / "templates" / "labs_template.csv"
                if template.exists():
                    path = template
                    logging.getLogger(__name__).info(f"Using labs template CSV at {template}")
                else:
                    if not labs_csv:
                        return []
                    logging.getLogger(__name__).warning(
                        f"Labs CSV not found and template missing; proceeding without labs data."
                    )
                    return []

            rows: List[Dict[str, Any]] = []
            with path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                # normalize column names
                def norm(s: str) -> str:
                    return s.strip().lower().replace(" ", "_")
                fieldmap = {norm(c): c for c in reader.fieldnames or []}
                # guess lat/lon columns
                lat_key = next((fieldmap[k] for k in ["lat", "latitude"] if k in fieldmap), None)
                lon_key = next((fieldmap[k] for k in ["lon", "lng", "longitude"] if k in fieldmap), None)
                name_key = next((fieldmap[k] for k in ["name", "site", "facility", "lab_name"] if k in fieldmap), None)
                for r in reader:
                    try:
                        lat = float(r[lat_key]) if lat_key and r.get(lat_key) not in (None, "") else None
                        lon = float(r[lon_key]) if lon_key and r.get(lon_key) not in (None, "") else None
                    except Exception:
                        lat, lon = None, None
                    rows.append({
                        "name": (r.get(name_key) if name_key else None),
                        "lat": lat,
                        "lon": lon,
                        "raw": r,
                    })
            logging.getLogger(__name__).info(f"Loaded labs: {len(rows)} rows from {path}")
            return rows
        except Exception:
            logging.getLogger(__name__).warning("Failed to load labs CSV; proceeding without labs data.")
            return []

    def _load_rdte(self, rdte_csv: Optional[str]) -> List[Dict[str, Any]]:
        """
        Load FY26 RDT&E line items and normalize into a rich schema.

        New fields are optional; when absent we backfill sane defaults so
        behavioral logic can still operate:
            - lab_support_factor / industry_support_factor -> 1.0
            - authority_alignment_score / digital_maturity_score /
              mbse_coverage / shock_sensitivity -> 0.5
            - priority_alignment_* -> 0.5
            - stage_gate_start derived from budget_activity when missing.
        """
        if not rdte_csv:
            return []
        try:
            path = Path(rdte_csv)
            if not path.exists():
                logging.getLogger(__name__).warning(f"RDT&E CSV not found: {path}")
                return []

            def norm(s: str) -> str:
                return s.strip().lower().replace(" ", "_")

            # Support either a single CSV file or a directory of FY CSVs.
            paths: List[Path]
            if path.is_file():
                paths = [path]
            elif path.is_dir():
                candidates = sorted(p for p in path.glob("*.csv"))
                if not candidates:
                    logging.getLogger(__name__).warning(f"No RDT&E CSVs found in directory: {path}")
                    return []
                paths = candidates
            else:
                logging.getLogger(__name__).warning(f"RDT&E path is neither file nor directory: {path}")
                return []

            rows: List[Dict[str, Any]] = []
            for csv_path in paths:
                with csv_path.open("r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    if not reader.fieldnames:
                        continue
                    fieldmap = {norm(c): c for c in reader.fieldnames}

                    def col(*names: str) -> Optional[str]:
                        for n in names:
                            key = norm(n)
                            if key in fieldmap:
                                return fieldmap[key]
                        return None

                    # Legacy FY26 columns for compatibility
                    pe_col = col("program_id", "pe_number", "pe_id", "project_id")
                    service_col = col("service_component", "service")
                    ba_col = col("budget_activity", "BA")
                    amount_col = col("funding_fy26", "amount", "fy26_request_$k", "fy26_request")
                    color_col = col("funding_color", "appropriation")

                    # New rich fields (optional)
                    portfolio_col = col("portfolio")
                    mission_focus_col = col("mission_focus", "portfolio_or_mission_area")
                    lab_support_col = col("lab_support_factor")
                    industry_support_col = col("industry_support_factor")
                    stage_start_col = col("stage_gate_start")
                    authority_align_col = col("authority_alignment_score", "authority_alignment")
                    nds_align_col = col("priority_alignment_nds")
                    ccmd_align_col = col("priority_alignment_ccmd")
                    service_align_col = col("priority_alignment_service")
                    digital_maturity_col = col("digital_maturity_score", "tech_maturity_level")
                    mbse_coverage_col = col("mbse_coverage")
                    shock_sensitivity_col = col("shock_sensitivity")
                    entity_col = col("entity_id", "lab_unit_or_contractor")
                    vendor_col = col("vendor_id", "prime_contractor", "vendor")
                    deps_col = col("dependencies")
                    status_col = col("program_status")
                    reprogramming_col = col("reprogramming_eligible")
                    intel_col = col("intel_discipline", "intel")

                    for raw in reader:
                        rec: Dict[str, Any] = {"raw": dict(raw)}
                        # Identity and core fields
                        program_id = raw.get(pe_col) if pe_col else None
                        if not program_id:
                            program_id = raw.get("PE_number") or raw.get("PE") or None
                        if not program_id:
                            # Fallback to a synthetic identifier
                            program_id = f"PE-{len(rows)}"
                        rec["program_id"] = str(program_id)

                        rec["service_component"] = (raw.get(service_col) if service_col else None) or ""
                        budget_activity = (raw.get(ba_col) if ba_col else None) or ""
                        rec["budget_activity"] = str(budget_activity)

                        try:
                            amt_raw = raw.get(amount_col) if amount_col else None
                            rec["funding_fy26"] = float(amt_raw) if amt_raw not in (None, "") else 0.0
                        except Exception:
                            rec["funding_fy26"] = 0.0

                        rec["funding_color"] = (raw.get(color_col) if color_col else None) or "RDT&E"

                        # New workbook fields with defaults
                        portfolio_val = (raw.get(portfolio_col) if portfolio_col else None) or (
                            raw.get(mission_focus_col) if mission_focus_col else None
                        ) or ""
                        rec["portfolio"] = portfolio_val
                        rec["mission_focus"] = (raw.get(mission_focus_col) if mission_focus_col else None) or ""

                        def _f(colname: Optional[str], default: float) -> float:
                            if not colname:
                                return default
                            try:
                                val = raw.get(colname)
                                return float(val) if val not in (None, "") else default
                            except Exception:
                                return default

                        rec["lab_support_factor"] = _f(lab_support_col, 1.0)
                        rec["industry_support_factor"] = _f(industry_support_col, 1.0)

                        stage_start = (raw.get(stage_start_col) if stage_start_col else None) or ""
                        rec["stage_gate_start"] = stage_start

                        authority_raw = raw.get(authority_align_col) if authority_align_col else None
                        if authority_raw not in (None, ""):
                            try:
                                authority_score = float(authority_raw)
                            except Exception:
                                norm_val = str(authority_raw).strip().lower()
                                if norm_val.startswith("title10"):
                                    authority_score = 0.9
                                elif norm_val.startswith("title50"):
                                    authority_score = 0.3
                                else:
                                    authority_score = 0.5
                        else:
                            authority_score = 0.5
                        rec["authority_alignment_score"] = authority_score
                        rec["authority"] = str(authority_raw) if authority_raw not in (None, "") else ""

                        rec["priority_alignment_nds"] = _f(nds_align_col, 0.5)
                        rec["priority_alignment_ccmd"] = _f(ccmd_align_col, 0.5)
                        rec["priority_alignment_service"] = _f(service_align_col, 0.5)

                        digital_score = _f(digital_maturity_col, 0.5)
                        if digital_score > 1.0:
                            digital_score = min(1.0, digital_score / 10.0)
                        rec["digital_maturity_score"] = digital_score
                        rec["mbse_coverage"] = _f(mbse_coverage_col, 0.5)
                        rec["shock_sensitivity"] = _f(shock_sensitivity_col, 0.5)

                        deps_raw = (raw.get(deps_col) if deps_col else "") or ""
                        rec["dependencies"] = deps_raw
                        rec["intel_discipline"] = (raw.get(intel_col) if intel_col else None) or ""
                        rec["program_status"] = (raw.get(status_col) if status_col else None) or "Active"
                        entity_val = (raw.get(entity_col) if entity_col else None) or ""
                        rec["entity_id"] = str(entity_val) if entity_val else rec["program_id"]
                        rec["vendor_id"] = (raw.get(vendor_col) if vendor_col else None) or ""

                        rep_raw = (raw.get(reprogramming_col) if reprogramming_col else None)
                        if isinstance(rep_raw, str):
                            rec["reprogramming_eligible"] = rep_raw.strip().lower() in {"1", "true", "yes", "y"}
                        elif rep_raw is None:
                            rec["reprogramming_eligible"] = False
                        else:
                            rec["reprogramming_eligible"] = bool(rep_raw)

                        # Backfill stage_gate_start from budget activity if needed
                        if not rec["stage_gate_start"]:
                            ba = str(rec["budget_activity"]).upper()
                            if ba.endswith("2"):
                                rec["stage_gate_start"] = "feasibility"
                            elif ba.endswith("3"):
                                rec["stage_gate_start"] = "prototype_demo"
                            elif ba.endswith("4"):
                                rec["stage_gate_start"] = "functional_test"
                            elif ba.endswith("5"):
                                rec["stage_gate_start"] = "vulnerability_test"
                            elif ba.endswith("6") or ba.endswith("7"):
                                rec["stage_gate_start"] = "operational_test"

                        rows.append(rec)

            logging.getLogger(__name__).info(f"Loaded RDT&E: {len(rows)} rows from {path}")
            return rows
        except Exception:
            logging.getLogger(__name__).warning("Failed to load RDT&E CSV; proceeding without rdte data.")
            return []

    def _program_domains(self) -> Dict[str, str]:
        """
        Map program_id -> domain for role alignment scoring.
        """
        domains: Dict[str, str] = {}
        try:
            for row in self.rdte_fy26 or []:
                pid = row.get("program_id") or row.get("project_id")
                domain = row.get("domain") or row.get("mission_focus") or row.get("portfolio") or ""
                if pid:
                    domains[str(pid)] = str(domain)
        except Exception:
            pass
        return domains

    def get_shock_modifier(self, gate: str, researcher: ResearcherAgent) -> float:
        """
        Compute a cumulative multiplier for the current tick/gate based on loaded shocks.
        """
        if not getattr(self, "shocks", None):
            return 1.0
        total = 0.0
        gate_key = (gate or "all").lower()
        tick = getattr(self.schedule, "time", 0)
        for event in self.shocks:
            duration = int(event.get("duration_steps", 0))
            start = int(event.get("start_step", 0))
            if duration <= 0 or not (start <= tick < start + duration):
                continue
            affected_gate = str(event.get("affected_gate", "all") or "all").lower()
            if affected_gate not in {"all", gate_key}:
                continue
            if not self._matches_shock_dimension(event, researcher):
                continue
            total += float(event.get("magnitude", 0.0))
        return max(0.0, 1.0 + total)

    def _matches_shock_dimension(self, event: Dict[str, object], researcher: ResearcherAgent) -> bool:
        dim = str(event.get("target_dimension_type", "all") or "all").lower()
        value = str(event.get("target_dimension_value", "*") or "*")
        if dim == "all" or value == "*" or not value:
            return True
        attr_map = {
            "funding_source": "funding_source",
            "ba": "budget_activity",
            "budget_activity": "budget_activity",
            "domain": "domain",
            "org_type": "org_type",
            "authority": "authority",
            "service_component": "service_component",
            "entity_id": "entity_id",
        }
        attr = attr_map.get(dim)
        if not attr:
            return True
        current = getattr(researcher, attr, "")
        if not current:
            return False
        normalized = str(current).strip().lower()
        target = value.strip().lower()
        return normalized == target

    def is_in_shock(self) -> bool:
        """Whether the system is currently in a shock window."""
        return self._in_shock

    # ---- Event logging ----
    def log_event(self, researcher: ResearcherAgent, gate: str, stage: Optional[str], outcome: str) -> None:
        if not self._events:
            return
        row: Dict[str, Any] = {
            "tick": self.schedule.time,
            "researcher_id": getattr(researcher, "unique_id", None),
            "gate": gate,
            "stage": stage,
            "outcome": outcome,
            "trl": getattr(researcher, "trl", None),
            "authority": getattr(researcher, "authority", None),
            "funding_source": getattr(researcher, "funding_source", None),
            "org_type": getattr(researcher, "org_type", None),
            "domain": getattr(researcher, "domain", None),
            "kinetic": getattr(researcher, "kinetic_category", None),
            "intel": getattr(researcher, "intel_discipline", None),
            "legal_status": getattr(researcher, "legal_status", None),
            "project_id": getattr(researcher, "project_id", None),
            "program_office": getattr(researcher, "program_office", None),
            "service_component": getattr(researcher, "service_component", None),
            "sponsor": getattr(researcher, "sponsor", None),
            "prime_contractor": getattr(researcher, "prime_contractor", None),
        }
        # Stage latency if we track entry tick
        try:
            if stage is not None and getattr(researcher, "stage_enter_tick", None) is not None:
                row["latency_in_stage"] = int(self.schedule.time - researcher.stage_enter_tick)  # type: ignore[arg-type]
        except Exception:
            pass
        # Copy last gate probability context if present
        if self._last_gate_context and isinstance(self._last_gate_context, dict):
            for k, v in self._last_gate_context.items():
                if k not in row:
                    row[k] = v
        # Append to events
        self._events.log(row)

    # ---- Evaluation and adoption ----
    def evaluate_and_adopt(self, researcher: ResearcherAgent) -> bool:
        """
        Ask a random sample of end‑users to evaluate the prototype.
        We use a simple majority vote to decide adoption.
        """
        # Delegate behavior to adoption_gate, keeping legacy logic for reference.
        return policies.adoption_gate(self, researcher)
        k = max(1, len(self.endusers) // 5)  # sample 20% (rounded down), at least 1
        sample = self.random.sample(self.endusers, k=k)
        votes = [eu.evaluate(researcher) for eu in sample]
        adopted = sum(votes) >= max(1, len(sample) // 2)  # simple majority
        return adopted

    # ---- Simulation loop ----
    def step(self) -> None:
        """
        One full model tick:
        - Toggle shock state as appropriate.
        - Step all agents.
        - Record new adoptions for diffusion metrics.
        """
        # Toggle shock on/off in the 'shock' regime
        if self.regime == "shock" and self.schedule.time == self.shock_at:
            self._in_shock = True
        if self.regime == "shock" and self.schedule.time == self.shock_at + self.shock_duration:
            self._in_shock = False

        # Count transitions before stepping (to compute "new" adoptions this tick)
        pre_transitions = sum(1 for r in self.researchers if r.time_to_transition is not None)

        # Step all agents once (order randomized by RandomActivation)
        self.schedule.step()

        # Compute how many new transitions occurred during this tick
        post_transitions = sum(1 for r in self.researchers if r.time_to_transition is not None)
        self.metrics.register_tick(adopted_count=max(0, post_transitions - pre_transitions))
        # Optionally decay penalty counts
        try:
            self.penalties.decay_all()
        except Exception:
            pass
        # Collect for visualization
        try:
            self.datacollector.collect(self)
        except Exception:
            pass

    def run(self, steps: int = 200) -> Dict[str, Any]:
        """
        Run the model for a fixed number of steps and return a metrics summary.
        We also extract per‑agent cycle times for any that transitioned.
        """
        for _ in range(int(steps)):
            self.step()

        # Collect cycle times after the simulation ends
        for r in self.researchers:
            if r.time_to_transition is not None:
                self.metrics.on_transition(r.time_to_transition)
        # Flush any event logs if configured
        try:
            if self._events:
                self._events.flush()
        except Exception:
            pass
        return self.metrics.summary()

