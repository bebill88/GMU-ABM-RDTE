"""
Agent definitions for the ABM.

We model three roles common in DoD/IC innovation transitions:
- Researcher: Generates and iterates on prototypes based on feedback.
- Policymaker: Allocates funding, applies oversight; may adapt in response to feedback.
- EndUser: Evaluates operational utility and signals feedback pressure upstream.
"""
from __future__ import annotations

from mesa import Agent
from typing import Optional, List


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

    def __init__(self, unique_id, model, prototype_rate: float, learning_rate: float):
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

        # Program context attributes (toy distributions)
        self.project_id = f"proj-{unique_id}"
        self.authority = self.random.choice(["Title10", "Title50"])  # Title 10 vs Title 50
        self.funding_source = self.random.choice(["ProgramBase", "POM", "UFR", "External", "Partner", "Partner_CoDev"])
        self.org_type = self.random.choice(["GovLab", "GovContractor", "Commercial"])
        self.domain = self.random.choice(["ISR", "Cyber", "EW", "Space", "Air", "Land", "Maritime"])
        self.kinetic_category = self.random.choice(["Kinetic", "NonKinetic"])
        self.intel_discipline = self.random.choice(["SIGINT", "GEOINT", "HUMINT", "MASINT", "OSINT"])  # may be N/A
        self.program_office = self.random.choice(["PEO C4I", "AFLCMC", "NAVWAR", "NRL", "DARPA", "DEVCOM"])  # example labels
        self.service_component = self.random.choice(["Army", "Navy", "Air Force", "USMC", "Space Force", "IC"])
        self.sponsor = self.random.choice(["Service HQ", "CCMD", "Agency", "POC-User"])  # simplified
        self.prime_contractor = self.random.choice(["None", "Boeing", "NG", "LM", "SAIC", "Leidos"])  # demo values

        # Policy alignment toggles
        self.align_priority = bool(self.random.random() < 0.5)  # Presidential priorities
        self.align_nds = bool(self.random.random() < 0.6)       # National Defense Strategy
        self.align_ccmd = bool(self.random.random() < 0.5)      # Combatant Command needs
        self.align_agency = bool(self.random.random() < 0.6)    # Agency/Service priorities
        # Precompute alignment score (0..1)
        self.alignment_score = (
            (1.0 if self.align_priority else 0.0)
            + (1.0 if self.align_nds else 0.0)
            + (1.0 if self.align_ccmd else 0.0)
            + (1.0 if self.align_agency else 0.0)
        ) / 4.0
        # Legal status memory (updated by legal gate)
        self.legal_status: str = "not_conducted"

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
            self.current_stage_index = 0
            self.stage_enter_tick = self.model.schedule.time
            # Register an attempt for metrics
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
                        self.has_candidate = False
                        self.current_stage_index = None
                        self.legal_status = "not_conducted"
                        # Compute cycle time only if we recorded a start
                        if self.prototype_start_tick is not None:
                            self.time_to_transition = (
                                self.model.schedule.time - self.prototype_start_tick
                            )
                            self.prototype_start_tick = None
                        if hasattr(self.model, "log_event"):
                            self.model.log_event(self, gate="adoption", stage=None, outcome="success")
                    else:
                        # Negative feedback from ops test; learn modestly
                        self.model.penalty_record_failure("adoption", self)
                        self.quality = min(1.0, self.quality + self.learning_rate * self.random.random())
                        if hasattr(self.model, "log_event"):
                            self.model.log_event(self, gate="adoption", stage=None, outcome="reject")
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
