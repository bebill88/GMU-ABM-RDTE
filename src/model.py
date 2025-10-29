"""
Core Mesa model.
Owns the agent population, scheduling, regime/shock state, and
exposes helper functions for policy gates and adoption evaluation.
"""
from __future__ import annotations

from mesa import Model
from mesa.time import RandomActivation
from typing import List, Dict, Any

from .agents import ResearcherAgent, PolicymakerAgent, EndUserAgent
from . import policies
from .metrics import MetricTracker


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
                 seed: int | None = None):
        super().__init__(seed=seed)

        # Scheduler drives agent step order each tick
        self.schedule = RandomActivation(self)

        # Keep a local RNG (Mesa also seeds its own); using both is fine for a toy model
        import random as _random
        self.random = _random.Random(seed)

        # Model‑level state
        self.regime = regime
        self.shock_at = int(shock_at)
        self.funding_rdte = float(funding_rdte)
        self.funding_om = float(funding_om)
        self.metrics = MetricTracker()
        self._in_shock = False

        # --- Create agents and register with scheduler ---
        self.researchers: List[ResearcherAgent] = []
        for i in range(n_researchers):
            a = ResearcherAgent(i, self, prototype_rate=0.05, learning_rate=0.1)
            self.schedule.add(a)
            self.researchers.append(a)

        offset = n_researchers
        self.policymakers: List[PolicymakerAgent] = []
        for i in range(n_policymakers):
            a = PolicymakerAgent(offset + i, self, allocation_agility=0.1, oversight_rigidity=0.8)
            self.schedule.add(a)
            self.policymakers.append(a)

        offset += n_policymakers
        self.endusers: List[EndUserAgent] = []
        for i in range(n_endusers):
            a = EndUserAgent(offset + i, self, adoption_threshold=0.6, feedback_strength=0.4)
            self.schedule.add(a)
            self.endusers.append(a)

    # ---- Policy gates (delegation to policies.py) ----
    def policy_gate_allocation(self, researcher: ResearcherAgent) -> bool:
        """Return True if funding passes this step for the given researcher."""
        return policies.funding_gate(self, researcher)

    def policy_gate_oversight(self, researcher: ResearcherAgent) -> bool:
        """Return True if oversight passes this step for the given researcher."""
        return policies.oversight_gate(self, researcher)

    # ---- Environment helpers ----
    def environmental_signal(self) -> float:
        """
        Small nudge capturing policy headwinds or operational pull.
        Tuned per regime to make differences measurable without dominating quality.
        """
        if self.regime == "adaptive":
            return 0.1    # positive pull from fast feedback
        if self.regime == "linear":
            return -0.05  # mild headwind from rigid processes
        # shock regime
        return -0.1 if self.is_in_shock() else 0.0

    def is_in_shock(self) -> bool:
        """Whether the system is currently in a shock window."""
        return self._in_shock

    # ---- Evaluation and adoption ----
    def evaluate_and_adopt(self, researcher: ResearcherAgent) -> bool:
        """
        Ask a random sample of end‑users to evaluate the prototype.
        We use a simple majority vote to decide adoption.
        """
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
        if self.regime == "shock" and self.schedule.time == self.shock_at + 20:
            self._in_shock = False

        # Count transitions before stepping (to compute "new" adoptions this tick)
        pre_transitions = sum(1 for r in self.researchers if r.time_to_transition is not None)

        # Step all agents once (order randomized by RandomActivation)
        self.schedule.step()

        # Compute how many new transitions occurred during this tick
        post_transitions = sum(1 for r in self.researchers if r.time_to_transition is not None)
        self.metrics.register_tick(adopted_count=max(0, post_transitions - pre_transitions))

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

        return self.metrics.summary()
