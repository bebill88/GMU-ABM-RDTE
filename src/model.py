"""
Core Mesa model.
Owns the agent population, scheduling, regime/shock state, and
exposes helper functions for policy gates and adoption evaluation.
"""
from __future__ import annotations

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
                 events_path: Optional[str] = None):
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
        self.labs: List[Dict[str, Any]] = self._load_labs(labs_csv)
        self.rdte_fy26: List[Dict[str, Any]] = self._load_rdte(rdte_csv)
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
            "funding": ["researcher", "funding_source", "org_type"],
            "contracting": ["researcher", "org_type"],
            "test": ["researcher", "domain", "kinetic_category"],
            "legal": ["researcher", "authority", "domain", "kinetic_category"],
            "adoption": ["researcher", "domain"],
        })

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
        return keys

    def penalty_factor(self, gate: str, researcher: ResearcherAgent, stage: Optional[str] = None) -> float:
        return self.penalties.factor_for(self._penalty_keys(gate, researcher, stage))

    def penalty_record_failure(self, gate: str, researcher: ResearcherAgent, stage: Optional[str] = None) -> None:
        self.penalties.bump(self._penalty_keys(gate, researcher, stage))

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

    # ---- Data loading helpers ----
    def _load_labs(self, labs_csv: Optional[str]) -> List[Dict[str, Any]]:
        if not labs_csv:
            return []
        try:
            path = Path(labs_csv)
            if not path.exists():
                logging.getLogger(__name__).warning(f"Labs CSV not found: {path}")
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
        if not rdte_csv:
            return []
        try:
            path = Path(rdte_csv)
            if not path.exists():
                logging.getLogger(__name__).warning(f"RDT&E CSV not found: {path}")
                return []
            rows: List[Dict[str, Any]] = []
            with path.open("r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for r in reader:
                    rows.append(dict(r))
            logging.getLogger(__name__).info(f"Loaded RDT&E: {len(rows)} rows from {path}")
            return rows
        except Exception:
            logging.getLogger(__name__).warning("Failed to load RDT&E CSV; proceeding without rdte data.")
            return []

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

