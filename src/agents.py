"""
Agent definitions for the ABM.

We model three roles common in DoD/IC innovation transitions:
- Researcher: Generates and iterates on prototypes based on feedback.
- Policymaker: Allocates funding, applies oversight; may adapt in response to feedback.
- EndUser: Evaluates operational utility and signals feedback pressure upstream.
"""
from __future__ import annotations

from mesa import Agent
from typing import Optional


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
    def __init__(self, unique_id, model, prototype_rate: float, learning_rate: float):
        super().__init__(unique_id, model)
        self.prototype_rate = float(prototype_rate)
        self.learning_rate = float(learning_rate)
        # Initialize around a middling technical merit so learning can show effect.
        self.quality = self.random.uniform(0.3, 0.7)
        self.has_candidate = False
        self.time_to_transition: Optional[int] = None
        self.prototype_start_tick: Optional[int] = None

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
            # Register an attempt for metrics
            self.model.metrics.on_attempt()

        # 2) Progress existing prototype through policy gates
        if self.has_candidate:
            funding_ok = self.model.policy_gate_allocation(self)
            oversight_ok = self.model.policy_gate_oversight(self)
            if funding_ok and oversight_ok:
                # 3) End‑users evaluate and possibly adopt
                adopted = self.model.evaluate_and_adopt(self)
                if adopted:
                    self.has_candidate = False
                    # Compute cycle time only if we recorded a start
                    if self.prototype_start_tick is not None:
                        self.time_to_transition = (
                            self.model.schedule.time - self.prototype_start_tick
                        )
                        self.prototype_start_tick = None
                else:
                    # Negative feedback: improve quality slightly (capped at 1.0)
                    self.quality = min(1.0, self.quality + self.learning_rate * self.random.random())


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
        This is deliberately simple: we avoid hard‑coding "truth" and let experiments compare regimes.
        """
        if self.model.regime == "adaptive":
            # Convert inbox pressure into small parameter nudges
            adjustment = min(0.2, self.feedback_inbox * 0.1)
            self.allocation_agility = min(1.0, self.allocation_agility + adjustment)
            self.oversight_rigidity = max(0.0, self.oversight_rigidity - adjustment)
            self.feedback_inbox = 0.0  # reset after processing
        # In 'linear' or during 'shock', parameters remain effectively static.


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
        Compute perceived utility as a function of:
        - intrinsic prototype quality,
        - environmental signal (policy headwinds vs. operational pull).
        """
        utility = researcher.quality + self.model.environmental_signal()
        return utility >= self.adoption_threshold

    def provide_feedback(self) -> None:
        """Push a small amount of pressure to each policymaker every tick."""
        for pm in self.model.policymakers:
            pm.receive_feedback(self.feedback_strength * 0.1)

    def step(self) -> None:
        """End‑users continuously provide feedback; evaluation happens on demand."""
        self.provide_feedback()
