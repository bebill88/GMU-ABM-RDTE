"""
Utilities for loading and aggregating GAO findings into per-program penalties.

We normalize the GAO findings table to the richer header and compute a
program-level risk score so downstream gates can down-weight success odds.
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


def _row_score(row: Dict[str, str]) -> float:
    """Compute a row-level risk score using the provided formula."""
    try:
        severity = float(row.get("severity") or 0.0)
    except ValueError:
        severity = 0.0
    try:
        repeat = int(row.get("repeat_issue_flag") or 0)
    except ValueError:
        repeat = 0
    try:
        recs = float(row.get("recommendation_count") or 0.0)
    except ValueError:
        recs = 0.0
    try:
        open_recs = float(row.get("open_recs") or 0.0)
    except ValueError:
        open_recs = 0.0

    unresolved_ratio = (open_recs / recs) if recs > 0 else 0.0
    return severity * (1.0 + float(repeat)) * (0.5 + 0.5 * unresolved_ratio)


def load_program_penalties(path: Optional[str]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Read GAO findings and return:
      - program_penalty: program_id -> normalized [0,1] penalty
      - raw_scores: program_id -> unnormalized aggregate score
    """
    rows = _read_csv(path)
    raw_scores: Dict[str, float] = {}
    for row in rows:
        program_id = (row.get("program_id") or "").strip()
        if not program_id:
            continue
        score = _row_score(row)
        if score <= 0:
            continue
        raw_scores[program_id] = raw_scores.get(program_id, 0.0) + score

    if not raw_scores:
        return {}, {}

    max_score = max(raw_scores.values())
    if max_score <= 0:
        return {k: 0.0 for k in raw_scores}, raw_scores

    program_penalty = {k: round(v / max_score, 6) for k, v in raw_scores.items()}
    return program_penalty, raw_scores

