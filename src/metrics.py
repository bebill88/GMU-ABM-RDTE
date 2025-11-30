"""
Metrics tracking.
We compute a few simple, decision-relevant KPIs after each run:
- transition_rate  : % of attempts that successfully transition to field
- avg_cycle_time   : average steps from prototype start to adoption
- diffusion_speed  : average adoptions per tick (rough adoption velocity)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any
import statistics
import csv
from pathlib import Path


@dataclass
class MetricTracker:
    # Cumulative counters
    transitions: int = 0
    attempts: int = 0

    # Distributions
    cycle_times: list[int] = field(default_factory=list)
    feedback_lags: list[int] = field(default_factory=list)  # reserved for future use

    # Shock bookkeeping (reserved for resilience metrics)
    shocks: int = 0
    recoveries: int = 0

    # Per-tick measurements (e.g., adoption counts each step)
    adoptions_per_tick: list[int] = field(default_factory=list)
    gate_counts: dict = field(default_factory=dict)          # gate -> {'pass': int, 'fail': int}
    gate_stage_counts: dict = field(default_factory=dict)    # (gate, stage) -> {'pass': int, 'fail': int}

    def on_attempt(self) -> None:
        """Register a prototype attempt (future hook; not used in basic flow)."""
        self.attempts += 1

    def on_transition(self, cycle_time: int) -> None:
        """Record a successful transition and its cycle time."""
        self.transitions += 1
        self.cycle_times.append(int(cycle_time))

    def register_tick(self, adopted_count: int) -> None:
        """Record number of new adoptions for this tick (for diffusion speed)."""
        self.adoptions_per_tick.append(int(adopted_count))

    def record_gate(self, gate: str, stage: str | None, passed: bool) -> None:
        """Record gate pass/fail counts (aggregate and by stage)."""
        outcome = "pass" if passed else "fail"
        g = self.gate_counts.setdefault(gate, {"pass": 0, "fail": 0})
        g[outcome] += 1
        if stage is not None:
            key = (gate, stage)
            gs = self.gate_stage_counts.setdefault(key, {"pass": 0, "fail": 0})
            gs[outcome] += 1

    def summary(self) -> Dict[str, Any]:
        """Compute simple summary stats for the run."""
        transition_rate = (self.transitions / self.attempts) if self.attempts else 0.0
        avg_cycle = statistics.mean(self.cycle_times) if self.cycle_times else 0.0
        diffusion_speed = statistics.mean(self.adoptions_per_tick) if self.adoptions_per_tick else 0.0
        return {
            "transition_rate": transition_rate,
            "avg_cycle_time": avg_cycle,
            "diffusion_speed": diffusion_speed,
            "attempts": self.attempts,
            "transitions": self.transitions,
            "gate_counts": self.gate_counts,
            "gate_stage_counts": self.gate_stage_counts,
        }


class PenaltyBook:
    """
    Tracks failure counts for entities and provides multiplicative penalty factors.
    Keys are free-form strings like "researcher:42" or "domain:Cyber".
    """
    def __init__(self, per_failure: float = 0.05, max_penalty: float = 0.3, decay: float = 0.0):
        self.per_failure = float(per_failure)
        self.max_penalty = float(max_penalty)
        self.decay = float(decay)
        self.counts: Dict[str, int] = {}

    def bump(self, keys: List[str]) -> None:
        for k in keys:
            self.counts[k] = self.counts.get(k, 0) + 1

    def factor_for(self, keys: List[str]) -> float:
        """
        Combine penalties multiplicatively across keys.
        factor = Π (1 - min(max_penalty, per_failure * count))
        We also enforce a soft floor so a few bad runs do not freeze the pipeline.
        """
        f = 1.0
        for k in keys:
            c = self.counts.get(k, 0)
            pen = min(self.max_penalty, self.per_failure * c)
            f *= max(0.0, 1.0 - pen)
        # Soft floor keeps probabilities from collapsing to ~0 after repeated failures.
        return max(0.4, min(1.0, f))

    def decay_all(self) -> None:
        if self.decay <= 0:
            return
        for k, c in list(self.counts.items()):
            new_c = max(0, int(round(c * (1.0 - self.decay))))
            if new_c == 0:
                self.counts.pop(k, None)
            else:
                self.counts[k] = new_c


class EventLogger:
    """Collects per-event rows and writes them to CSV on demand."""
    def __init__(self, path: str):
        self.path = Path(path)
        self.rows: List[Dict[str, Any]] = []

    def log(self, row: Dict[str, Any]) -> None:
        self.rows.append(row)

    def flush(self) -> None:
        if not self.rows:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # stable header order
        header = sorted({k for r in self.rows for k in r.keys()})
        with self.path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            w.writerows(self.rows)
