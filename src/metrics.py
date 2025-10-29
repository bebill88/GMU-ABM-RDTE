"""
Metrics tracking.
We compute a few simple, decision‑relevant KPIs after each run:
- transition_rate  : % of attempts that successfully transition to field
- avg_cycle_time   : average steps from prototype start to adoption
- diffusion_speed  : average adoptions per tick (rough adoption velocity)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any
import statistics


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

    # Per‑tick measurements (e.g., adoption counts each step)
    adoptions_per_tick: list[int] = field(default_factory=list)

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
        }
