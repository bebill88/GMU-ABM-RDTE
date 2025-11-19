"""
Helpers to load the external CSV inputs described in docs/schema_*.md.
Each loader returns typed dictionaries so RdteModel can consume the values.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional


def _read_csv(path: Optional[str]) -> List[Dict[str, str]]:
    if not path:
        return []
    p = Path(path)
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8", errors="ignore") as f:
        reader = csv.DictReader(f)
        return [dict(row) for row in reader]


def load_gao_penalties(path: Optional[str]) -> Dict[str, float]:
    rows = _read_csv(path)
    program_totals: Dict[str, float] = {}
    for row in rows:
        program_id = (row.get("program_id") or "").strip()
        try:
            severity = float(row.get("severity") or 0.0)
        except ValueError:
            severity = 0.0
        repeat = 1.0 if str(row.get("repeat_issue_flag", "")).strip() in {"1", "true", "True"} else 0.0
        weight = severity * (1.0 + 0.5 * repeat)
        if not program_id:
            continue
        program_totals[program_id] = program_totals.get(program_id, 0.0) + weight
    return program_totals


def load_shock_events(path: Optional[str]) -> List[Dict[str, object]]:
    rows = _read_csv(path)
    events: List[Dict[str, object]] = []
    for row in rows:
        try:
            start = int(row.get("start_step") or 0)
        except ValueError:
            start = 0
        try:
            duration = int(row.get("duration_steps") or 0)
        except ValueError:
            duration = 0
        try:
            magnitude = float(row.get("magnitude") or 0.0)
        except ValueError:
            magnitude = 0.0
        events.append({
            "event_id": row.get("event_id", "").strip(),
            "category": row.get("category", "").strip(),
            "start_step": start,
            "duration_steps": max(0, duration),
            "target_dimension_type": (row.get("target_dimension_type") or "all").strip().lower(),
            "target_dimension_value": (row.get("target_dimension_value") or "*").strip(),
            "affected_gate": (row.get("affected_gate") or "all").strip().lower(),
            "effect_type": (row.get("effect_type") or "").strip().lower(),
            "magnitude": magnitude,
            "note": row.get("note", "").strip(),
        })
    return events


def load_performance_penalties(path: Optional[str]) -> Tuple[Dict[str, float], Dict[str, float]]:
    rows = _read_csv(path)
    program_scores: Dict[str, List[float]] = {}
    vendor_scores: Dict[str, List[float]] = {}
    for row in rows:
        program = (row.get("program_id") or "").strip()
        vendor = (row.get("vendor_id") or "").strip()
        def _float(k: str, default: float = 0.0) -> float:
            try:
                return float(row.get(k) or default)
            except ValueError:
                return default
        cost = max(0.0, _float("cost_variance_pct"))
        schedule = max(0.0, _float("schedule_variance_pct"))
        tech = max(0.0, 3.0 - _float("technical_rating"))
        mgmt = max(0.0, 3.0 - _float("management_rating"))
        breach = 2.0 if str(row.get("major_breach_flag", "")).strip() in {"1", "true", "True"} else 0.0
        perf_penalty = 0.01 * cost + 0.01 * schedule + tech + mgmt + breach
        if program:
            program_scores.setdefault(program, []).append(perf_penalty)
        if vendor:
            vendor_scores.setdefault(vendor, []).append(perf_penalty)
    avg = lambda l: sum(l) / len(l) if l else 0.0
    return (
        {k: avg(v) for k, v in program_scores.items()},
        {k: avg(v) for k, v in vendor_scores.items()},
    )


def load_collaboration_bonus(path: Optional[str], current_year: int = 2025) -> Dict[str, float]:
    rows = _read_csv(path)
    scores: Dict[str, float] = {}
    for row in rows:
        try:
            start = int(row.get("start_year") or 0)
        except ValueError:
            start = 0
        try:
            end = int(row.get("end_year") or 0)
        except ValueError:
            end = 0
        if not (start <= current_year <= (end or 9999)):
            continue
        try:
            intensity = float(row.get("intensity") or 0.0)
        except ValueError:
            intensity = 0.0
        if intensity <= 0:
            continue
        a = (row.get("from_entity_id") or "").strip()
        b = (row.get("to_entity_id") or "").strip()
        for node in (a, b):
            if node:
                scores[node] = scores.get(node, 0.0) + intensity
    if not scores:
        return {}
    max_score = max(scores.values())
    if max_score <= 0:
        return {}
    return {k: v / max_score for k, v in scores.items()}
