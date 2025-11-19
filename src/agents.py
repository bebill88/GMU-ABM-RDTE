"""
Agent definitions for the ABM.

We model three roles common in DoD/IC innovation transitions:
- Researcher: Generates and iterates on prototypes based on feedback.
- Policymaker: Allocates funding, applies oversight; may adapt in response to feedback.
- EndUser: Evaluates operational utility and signals feedback pressure upstream.
"""
from __future__ import annotations

from mesa import Agent
from typing import Optional, List, Dict, Any


class ResearcherAgent(Agent):
    """
    Produces prototypes and learns from feedback.
    Attributes
    ----------
    prototype_rate : float
        Probability each step to initiate a new prototype if none is in progress.
    learning_rate : float
        Magnitude of quality improvement after negative feedback (0..1).
    quality : float
        Technical merit / maturity proxy (0..1). Higher is better.
    has_candidate : bool
        Whether a prototype is currently in the pipeline for this agent.
    time_to_transition : Optional[int]
        Cycle time (steps) for successful transition; set when adoption occurs.
    """
    STAGES: List[str] = [
        "feasibility",
        "prototype_demo",
        "functional_test",
        "vulnerability_test",
        "operational_test",
    ]

    def __init__(self, unique_id, model, prototype_rate: float, learning_rate: float, rdte_program: Optional[Dict[str, Any]] = None):
        super().__init__(unique_id, model)
        self.prototype_rate = float(prototype_rate)
        self.learning_rate = float(learning_rate)
        # Initialize around a middling technical merit so learning can show effect.
        self.quality = self.random.uniform(0.3, 0.7)
        self.has_candidate = False
        self.time_to_transition: Optional[int] = None
        self.prototype_start_tick: Optional[int] = None
        # Stage-pipeline attributes
        self.trl: int = int(self.random.randint(2, 4))
        self.current_stage_index: Optional[int] = None
        self.stage_enter_tick: Optional[int] = None
        # Per-project attempt/transition counters for focused projections
        self.attempts: int = 0
        self.transitions: int = 0

        # Program context attributes.
        # If an RDT&E program row is provided, prefer its fields; otherwise fall back to toy distributions.
        self._init_from_rdte(rdte_program)

        # Legal status memory (updated by legal gate)
        self.legal_status: str = "not_conducted"

    def _init_from_rdte(self, rdte_program: Optional[Dict[str, Any]]) -> None:
        """
        Initialize program context from an optional RDT&E workbook row.
        This wires rich FY26 fields into the agent while maintaining sensible defaults.
        """
        # Defaults for random/toy initialization (used when no program row or missing fields)
        self.project_id = f"proj-{self.unique_id}"
        self.program_id = self.project_id
        self.authority = self.random.choice(["Title10", "Title50"])
        self.funding_source = self.random.choice(["ProgramBase", "POM", "UFR", "External", "Partner", "Partner_CoDev"])
        self.org_type = self.random.choice(["GovLab", "GovContractor", "Commercial"])
        self.domain = self.random.choice(["ISR", "Cyber", "EW", "Space", "Air", "Land", "Maritime"])
        self.portfolio = self.domain
        self.kinetic_category = self.random.choice(["Kinetic", "NonKinetic"])
        self.intel_discipline = self.random.choice(["SIGINT", "GEOINT", "HUMINT", "MASINT", "OSINT"])
        self.program_office = self.random.choice(["PEO C4I", "AFLCMC", "NAVWAR", "NRL", "DARPA", "DEVCOM"])
        self.service_component = self.random.choice(["Army", "Navy", "Air Force", "USMC", "Space Force", "IC"])
        self.sponsor = self.random.choice(["Service HQ", "CCMD", "Agency", "POC-User"])
        self.prime_contractor = self.random.choice(["None", "Boeing", "NG", "LM", "SAIC", "Leidos"])

        # New rich program fields with defaults
        self.budget_activity = "BA3"
        self.funding_fy26 = 0.0
        self.funding_color = "RDT&E"
        self.reprogramming_eligible = False

        self.lab_support_factor = 1.0
        self.industry_support_factor = 1.0

        self.stage_gate_start = "feasibility"
        self.authority_alignment_score = 0.5
        self.priority_alignment_nds = 0.5
        self.priority_alignment_ccmd = 0.5
        self.priority_alignment_service = 0.5

        self.digital_maturity_score = 0.5
        self.mbse_coverage = 0.5

        self.shock_sensitivity = 0.5

        self.dependencies: List[str] = []
        self.program_status = "Active"
        self.entity_id = self.program_id
        self.vendor_id = ""
        self.gao_penalty = 0.0
        self.perf_penalty = 0.0
        self.ecosystem_bonus = 0.0

        if not rdte_program:
            # Policy alignment toggles for the toy setup
            self.align_priority = bool(self.random.random() < 0.5)
            self.align_nds = bool(self.random.random() < 0.6)
            self.align_ccmd = bool(self.random.random() < 0.5)
            self.align_agency = bool(self.random.random() < 0.6)
        else:
            # Normalize keys defensively (the loader already does this for new fields).
            def _get(key: str, default: Any) -> Any:
                return rdte_program.get(key, default)

            self.program_id = str(_get("program_id", self.program_id))
            self.project_id = self.program_id or self.project_id
            sc = _get("service_component", self.service_component)
            if sc:
                self.service_component = str(sc)
            portfolio = _get("portfolio", self.portfolio)
            if portfolio:
                self.portfolio = str(portfolio)
            ba = _get("budget_activity", self.budget_activity)
            if ba:
                self.budget_activity = str(ba)
            try:
                self.funding_fy26 = float(_get("funding_fy26", self.funding_fy26) or 0.0)
            except Exception:
                self.funding_fy26 = 0.0
            fc = _get("funding_color", self.funding_color)
            if fc:
                self.funding_color = str(fc)
            self.reprogramming_eligible = bool(_get("reprogramming_eligible", self.reprogramming_eligible))

            # Support factors and alignments
            for attr, default in [
                ("lab_support_factor", self.lab_support_factor),
                ("industry_support_factor", self.industry_support_factor),
                ("authority_alignment_score", self.authority_alignment_score),
                ("priority_alignment_nds", self.priority_alignment_nds),
                ("priority_alignment_ccmd", self.priority_alignment_ccmd),
                ("priority_alignment_service", self.priority_alignment_service),
                ("digital_maturity_score", self.digital_maturity_score),
                ("mbse_coverage", self.mbse_coverage),
                ("shock_sensitivity", self.shock_sensitivity),
            ]:
                try:
                    val = float(_get(attr, default))
                except Exception:
                    val = default
                setattr(self, attr, val)

            deps_raw = str(_get("dependencies", "") or "")
            self.dependencies = [d.strip() for d in deps_raw.split(";") if d.strip()]
            status = str(_get("program_status", self.program_status) or self.program_status)
            self.program_status = status

            authority_val = _get("authority", self.authority)
            if authority_val:
                self.authority = str(authority_val)
            intel_val = _get("intel_discipline", self.intel_discipline)
            if intel_val:
                self.intel_discipline = str(intel_val)
            domain_val = _get("domain", "") or ""
            if not domain_val:
                domain_val = _get("mission_focus", "") or ""
            if domain_val:
                self.domain = str(domain_val)

            # Stage gate starting point may be provided directly; otherwise derive from BA.
            stage_start = str(_get("stage_gate_start", "") or "").strip().lower()
            if stage_start in self.STAGES:
                self.stage_gate_start = stage_start
            else:
                self.stage_gate_start = self._stage_from_budget_activity(self.budget_activity)

            # Alignment booleans are now derived from scores when an rdte_program exists
            self.align_priority = self.authority_alignment_score >= 0.5
            self.align_nds = self.priority_alignment_nds >= 0.5
            self.align_ccmd = self.priority_alignment_ccmd >= 0.5
            self.align_agency = self.priority_alignment_service >= 0.5
            entity_id = _get("entity_id", "")
            if entity_id:
                self.entity_id = str(entity_id)
            vendor_val = _get("vendor_id", "")
            if vendor_val:
                self.vendor_id = str(vendor_val)

        # Apply scenario-level profiles and recompute alignment score
        self._apply_scenario_profiles()

    def _stage_from_budget_activity(self, budget_activity: str) -> str:
        """
        Map budget activity (BA2/3/4/5/6/7) to a starting stage label.
        Defaults to feasibility when unknown.
        """
        ba = str(budget_activity).upper().strip()
        if ba.endswith("2"):
            return "feasibility"
        if ba.endswith("3"):
            return "prototype_demo"
        if ba.endswith("4"):
            return "functional_test"
        if ba.endswith("5"):
            return "vulnerability_test"
        if ba.endswith("6") or ba.endswith("7"):
            return "operational_test"
        return "feasibility"

    def _apply_scenario_profiles(self) -> None:
        """
        Apply scenario-level GUI profiles (from the model) to this
        researcher's program attributes, then recompute alignment score.
        """
        model = getattr(self, "model", None)
        if model is not None:
            # Portfolio/domain focus
            focus = getattr(model, "portfolio_focus", "Mixed")
            if isinstance(focus, str) and focus != "Mixed":
                if self.random.random() < 0.8:
                    self.domain = focus
                    self.portfolio = focus

            # Service component focus
            service_focus = getattr(model, "service_focus", "Joint")
            if isinstance(service_focus, str) and service_focus != "Joint":
                if self.random.random() < 0.8:
                    self.service_component = service_focus

            # Organization type mix
            org_mix = getattr(model, "org_mix", "Balanced")
            org_choices = ["GovLab", "GovContractor", "Commercial"]
            org_weights_map = {
                "Balanced": [1, 1, 1],
                "GovLab-heavy": [3, 1, 1],
                "Contractor-heavy": [1, 3, 1],
                "Commercial-heavy": [1, 1, 3],
            }
            weights = org_weights_map.get(org_mix, org_weights_map["Balanced"])
            total = float(sum(weights))
            r = self.random.random() * total
            acc = 0.0
            for name, w in zip(org_choices, weights):
                acc += float(w)
                if r <= acc:
                    self.org_type = name
                    break

            # Funding source pattern
            pattern = getattr(model, "funding_pattern", "ProgramBase")
            source_choices = ["ProgramBase", "POM", "UFR", "External", "Partner", "Partner_CoDev"]
            source_weights_map = {
                "ProgramBase": [3, 2, 1, 1, 1, 1],
                "POM-heavy": [1, 3, 1, 1, 1, 1],
                "UFR-heavy": [1, 1, 3, 1, 1, 1],
                "Partner-heavy": [1, 1, 1, 1, 2, 2],
            }
            sweights = source_weights_map.get(pattern, source_weights_map["ProgramBase"])
            stotal = float(sum(sweights))
            sr = self.random.random() * stotal
            sacc = 0.0
            for name, w in zip(source_choices, sweights):
                sacc += float(w)
                if sr <= sacc:
                    self.funding_source = name
                    break

            # Alignment profile scaling
            align_profile = getattr(model, "alignment_profile", "Medium")
            align_scale_map = {"Low": 0.7, "Medium": 1.0, "High": 1.3}
            a_scale = float(align_scale_map.get(align_profile, 1.0))
            for attr in [
                "authority_alignment_score",
                "priority_alignment_nds",
                "priority_alignment_ccmd",
                "priority_alignment_service",
            ]:
                val = float(getattr(self, attr, 0.5))
                val = max(0.0, min(1.0, val * a_scale))
                setattr(self, attr, val)

            # Digital maturity / MBSE coverage profile
            dig_profile = getattr(model, "digital_maturity_profile", "Medium")
            dig_scale_map = {"Low": 0.7, "Medium": 1.0, "High": 1.3}
            d_scale = float(dig_scale_map.get(dig_profile, 1.0))
            for attr in ["digital_maturity_score", "mbse_coverage"]:
                val = float(getattr(self, attr, 0.5))
                val = max(0.0, min(1.0, val * d_scale))
                setattr(self, attr, val)

            # Shock resilience profile (maps to shock_sensitivity)
            shock_prof = getattr(model, "shock_resilience", "Medium")
            if shock_prof == "High":  # highly resilient => lower sensitivity
                s_scale = 0.5
            elif shock_prof == "Low":  # low resilience => higher sensitivity
                s_scale = 1.5
            else:
                s_scale = 1.0
            val = float(getattr(self, "shock_sensitivity", 0.5))
            val = max(0.0, min(1.0, val * s_scale))
            setattr(self, "shock_sensitivity", val)

            # Ecosystem support profile (labs/industry support)
            eco_profile = getattr(model, "ecosystem_support", "Medium")
            eco_scale_map = {"Low": 0.7, "Medium": 1.0, "High": 1.3}
            e_scale = float(eco_scale_map.get(eco_profile, 1.0))
            for attr in ["lab_support_factor", "industry_support_factor"]:
                sval = float(getattr(self, attr, 1.0))
                sval = max(0.0, min(2.0, sval * e_scale))
                setattr(self, attr, sval)

        # Recompute alignment booleans and score from (possibly updated) scores
        self.align_priority = self.authority_alignment_score >= 0.5
        self.align_nds = self.priority_alignment_nds >= 0.5
        self.align_ccmd = self.priority_alignment_ccmd >= 0.5
        self.align_agency = self.priority_alignment_service >= 0.5

        # Precompute alignment score (0..1)
        self.alignment_score = (
            (1.0 if self.align_priority else 0.0)
            + (1.0 if self.align_nds else 0.0)
            + (1.0 if self.align_ccmd else 0.0)
            + (1.0 if self.align_agency else 0.0)
        ) / 4.0

    def step(self) -> None:
        """
        One simulation step of behavior for the researcher:
        1) Optionally start a prototype if idle.
        2) If a candidate exists, attempt to pass funding and oversight gates.
        3) If gates pass, end‑users vote on adoption.
           - On adoption: record cycle time and clear candidate.
           - On rejection: apply learning to increase quality modestly.
        """
        # 1) Try to start a new prototype if currently idle
        if not self.has_candidate and (self.random.random() < self.prototype_rate):
            self.has_candidate = True
            self.prototype_start_tick = self.model.schedule.time
            # Initialize pipeline stage from program starting point if available
            try:
                start_stage = getattr(self, "stage_gate_start", None)
                if isinstance(start_stage, str) and start_stage in self.STAGES:
                    self.current_stage_index = self.STAGES.index(start_stage)
                else:
                    self.current_stage_index = 0
            except Exception:
                self.current_stage_index = 0
            self.stage_enter_tick = self.model.schedule.time
            # Register an attempt for metrics
            self.attempts += 1
            self.model.metrics.on_attempt()
            if hasattr(self.model, "log_event"):
                self.model.log_event(self, gate="attempt", stage=None, outcome="start")

        # 2) Progress existing prototype through stage pipeline
        if self.has_candidate:
            # Ensure we have a stage index
            if self.current_stage_index is None:
                self.current_stage_index = 0
                self.stage_enter_tick = self.model.schedule.time

            stage = self.STAGES[self.current_stage_index]

            # Legal gate: only refresh if not favorable/favorable_with_caveats
            if self.legal_status in {"not_conducted"}:
                self.legal_status = self.model.policy_gate_legal(self)
                if self.legal_status == "unfavorable":
                    # Rejected on legal grounds; abandon candidate, learn slightly
                    self.model.penalty_record_failure("legal", self)
                    if hasattr(self.model, "log_event"):
                        self.model.log_event(self, gate="legal", stage=stage, outcome="unfavorable")
                    self.has_candidate = False
                    self.current_stage_index = None
                    self.quality = min(1.0, self.quality + 0.5 * self.learning_rate * self.random.random())
                    return

            # Funding and contracting gates
            if not self.model.policy_gate_funding(stage, self):
                self.model.penalty_record_failure("funding", self, stage)
                if hasattr(self.model, "log_event"):
                    self.model.log_event(self, gate="funding", stage=stage, outcome="fail")
                return  # stalled this tick
            if not self.model.policy_gate_contracting(self):
                self.model.penalty_record_failure("contracting", self)
                if hasattr(self.model, "log_event"):
                    self.model.log_event(self, gate="contracting", stage=stage, outcome="fail")
                return  # stalled this tick

            # Stage-specific test gate
            test_ok = self.model.policy_gate_test(stage, self, self.legal_status)
            if test_ok:
                # Advance stage and TRL
                trl_increments = {
                    "feasibility": 1,
                    "prototype_demo": 1,
                    "functional_test": 1,
                    "vulnerability_test": 1,
                    "operational_test": 2,
                }
                self.trl = min(9, self.trl + trl_increments.get(stage, 1))
                if hasattr(self.model, "log_event"):
                    self.model.log_event(self, gate="test", stage=stage, outcome="pass")
                self.current_stage_index += 1
                self.stage_enter_tick = self.model.schedule.time

                # If we've completed last stage, proceed to end-user evaluation/adoption
                if self.current_stage_index >= len(self.STAGES):
                    adopted = self.model.evaluate_and_adopt(self)
                    if adopted:
                        # Mark program as successfully fielded
                        try:
                            self.program_status = "Fielded"
                        except Exception:
                            pass
                        self.has_candidate = False
                        self.current_stage_index = None
                        self.legal_status = "not_conducted"
                        # Compute cycle time only if we recorded a start
                        if self.prototype_start_tick is not None:
                            self.time_to_transition = (
                                self.model.schedule.time - self.prototype_start_tick
                            )
                            self.prototype_start_tick = None
                        self.transitions += 1
                        if hasattr(self.model, "log_event"):
                            self.model.log_event(self, gate="adoption", stage=None, outcome="success")
                    else:
                        # Negative feedback from ops test; learn modestly
                        self.model.penalty_record_failure("adoption", self)
                        self.quality = min(1.0, self.quality + self.learning_rate * self.random.random())
                        # Keep the program at the final stage for another try
                        self.current_stage_index = len(self.STAGES) - 1
                        self.stage_enter_tick = self.model.schedule.time
                        if hasattr(self.model, "log_event"):
                            self.model.log_event(self, gate="adoption", stage=None, outcome="reject")
                return

            # Failed test; learn slightly and try again
            self.model.penalty_record_failure("test", self, stage)
            self.quality = min(1.0, self.quality + 0.5 * self.learning_rate * self.random.random())
            if hasattr(self.model, "log_event"):
                self.model.log_event(self, gate="test", stage=stage, outcome="fail")
            return


class PolicymakerAgent(Agent):
    """
    Allocates funding and applies oversight.
    In adaptive regimes, responds to feedback pressure by
    increasing allocation agility and reducing oversight rigidity.
    """
    def __init__(self, unique_id, model, allocation_agility: float, oversight_rigidity: float):
        super().__init__(unique_id, model)
        self.allocation_agility = float(allocation_agility)  # 0..1 (higher == more nimble)
        self.oversight_rigidity = float(oversight_rigidity)  # 0..1 (higher == more drag)
        self.feedback_inbox = 0.0  # accumulates signal from EndUser agents

    def receive_feedback(self, amount: float) -> None:
        """Accumulate feedback signal to be processed in step()."""
        self.feedback_inbox += float(amount)

    def step(self) -> None:
        """
        If the model regime is 'adaptive', bend parameters in response to feedback.
        This is deliberately simple and scenario-comparable.
        """
        if self.model.regime == "adaptive":
            adjustment = min(0.2, self.feedback_inbox * 0.1)
            self.allocation_agility = min(1.0, self.allocation_agility + adjustment)
            self.oversight_rigidity = max(0.0, self.oversight_rigidity - adjustment)
            self.feedback_inbox = 0.0


class EndUserAgent(Agent):
    """
    Represents operational users (warfighters, analysts) who evaluate utility and
    generate feedback pressure on policymakers each tick.
    """
    def __init__(self, unique_id, model, adoption_threshold: float, feedback_strength: float):
        super().__init__(unique_id, model)
        self.adoption_threshold = float(adoption_threshold)  # min utility required for adoption
        self.feedback_strength = float(feedback_strength)    # how strongly this agent signals upstream

    def evaluate(self, researcher: ResearcherAgent) -> bool:
        """
        Compute perceived utility as a function of intrinsic prototype quality
        plus environmental signal (policy headwinds vs. operational pull) with
        alignment/penalty bias from the model when available.
        """
        utility = researcher.quality + self.model.environmental_signal(researcher)
        return utility >= self.adoption_threshold

    def provide_feedback(self) -> None:
        """Push a small amount of pressure to each policymaker every tick."""
        for pm in self.model.policymakers:
            pm.receive_feedback(self.feedback_strength * 0.1)

    def step(self) -> None:
        """End-users continuously provide feedback; evaluation happens on demand."""
        self.provide_feedback()
