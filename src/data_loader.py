"""
Helpers to load the external CSV inputs described in docs/schema_*.md.
Each loader returns typed dictionaries so RdteModel can consume the values.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from . import gao_utils


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
    """Wrapper that returns program-level GAO penalties normalized to [0,1]."""
    penalties, _ = gao_utils.load_program_penalties(path)
    return penalties


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


def _capacity_score(entity: Dict[str, str]) -> float:
    """Estimate a normalized 0..1 capacity score using capacity ($M) and staff."""
    try:
        cap = float(entity.get("estimated_rdte_capacity_musd") or 0.0)
    except ValueError:
        cap = 0.0
    try:
        staff = float(entity.get("estimated_rdte_staff") or 0.0)
    except ValueError:
        staff = 0.0
    cap_score = min(1.0, cap / 200.0)
    staff_score = min(1.0, staff / 150.0)
    return max(0.0, min(1.0, 0.6 * cap_score + 0.4 * staff_score))


def _authority_score(flags: str) -> float:
    f = (flags or "").lower()
    if "10/50" in f or "both" in f:
        return 0.9
    if "10" in f:
        return 1.0
    if "50" in f:
        return 0.7
    return 0.6 if f else 0.5


def _classification_penalty(band: str) -> float:
    b = (band or "").lower()
    if "ts" in b:
        return 0.1
    if "c-s" in b or "c/" in b:
        return 0.05
    return 0.0


def _domain_match(program_domain: str, entity_domains: str) -> float:
    if not program_domain:
        return 0.5
    pd = program_domain.strip().lower()
    domains = [d.strip().lower() for d in (entity_domains or "").split(";") if d.strip()]
    return 1.0 if pd in domains else 0.3 if domains else 0.5


def _vendor_risk_score(row: Dict[str, str]) -> float:
    """Estimate vendor risk from historical ratings and cyber findings."""
    try:
        tech = float(row.get("vendor_avg_technical_rating") or 3.0)
    except ValueError:
        tech = 3.0
    try:
        mgmt = float(row.get("vendor_avg_management_rating") or 3.0)
    except ValueError:
        mgmt = 3.0
    try:
        max_cyber = float(row.get("max_cyber_findings") or 0.0)
    except ValueError:
        max_cyber = 0.0
    tech_pen = max(0.0, (5.0 - tech) / 4.0)
    mgmt_pen = max(0.0, (5.0 - mgmt) / 4.0)
    cyber_pen = max(0.0, min(1.0, max_cyber / 5.0))
    return max(0.0, min(1.0, 0.4 * tech_pen + 0.4 * mgmt_pen + 0.2 * cyber_pen))


def load_closed_projects(path: Optional[str]) -> tuple[list[Dict[str, str]], Dict[str, Dict[str, float]]]:
    """
    Load historical closed/transitioned projects and compute empirical transition rates.

    Returns (rows, priors) where priors includes rates by domain, authority_flags,
    vendor_risk_bucket, gao_severity_bucket, program, and overall_rate.
    """
    rows = _read_csv(path)
    if not rows:
        return [], {}

    def bucket_vendor(risk: float) -> str:
        if risk <= 0.3:
            return "low"
        if risk <= 0.6:
            return "medium"
        return "high"

    def bucket_gao(sev: float) -> str:
        if sev <= 1:
            return "0-1"
        if sev <= 2:
            return "2"
        if sev <= 3:
            return "3"
        if sev <= 4:
            return "4"
        return "5+"

    overall = {"total": 0, "succ": 0}
    domain: Dict[str, Dict[str, int]] = {}
    authority: Dict[str, Dict[str, int]] = {}
    vendor_bucket: Dict[str, Dict[str, int]] = {}
    gao_bucket: Dict[str, Dict[str, int]] = {}
    program: Dict[str, Dict[str, int]] = {}

    for row in rows:
        success = str(row.get("close_status", "")).strip().lower() == "transitioned"
        overall["total"] += 1
        if success:
            overall["succ"] += 1
        d = (row.get("primary_domain") or "").strip()
        a = (row.get("authority_flags") or "").strip()
        pid = (row.get("program_id") or "").strip()
        try:
            gsev = float(row.get("gao_avg_severity") or 0.0)
        except ValueError:
            gsev = 0.0
        try:
            risk_val = _vendor_risk_score(row)
        except Exception:
            risk_val = 0.0
        vb = bucket_vendor(risk_val)
        gb = bucket_gao(gsev)

        for bucket, store in [
            (d, domain),
            (a, authority),
            (vb, vendor_bucket),
            (gb, gao_bucket),
            (pid, program),
        ]:
            if not bucket:
                continue
            if bucket not in store:
                store[bucket] = {"total": 0, "succ": 0}
            store[bucket]["total"] += 1
            if success:
                store[bucket]["succ"] += 1

    def rates(store: Dict[str, Dict[str, int]]) -> Dict[str, float]:
        return {k: (v["succ"] / v["total"]) if v["total"] else 0.0 for k, v in store.items()}

    priors = {
        "overall_rate": (overall["succ"] / overall["total"]) if overall["total"] else 0.0,
        "domain": rates(domain),
        "authority": rates(authority),
        "vendor_bucket": rates(vendor_bucket),
        "gao_bucket": rates(gao_bucket),
        "program": rates(program),
    }
    return rows, priors


def load_rdte_entities(path: Optional[str]) -> Dict[str, Dict[str, str]]:
    """Load the expanded RDT&E entity master list keyed by parent_entity_id."""
    rows = _read_csv(path)
    entities: Dict[str, Dict[str, str]] = {}
    for row in rows:
        eid = (row.get("parent_entity_id") or row.get("entity_id") or "").strip()
        if not eid:
            continue
        entities[eid] = dict(row)
        entities[eid]["entity_id"] = eid
    return entities


def load_program_entity_roles(path: Optional[str], entities: Optional[Dict[str, Dict[str, str]]] = None) -> Dict[str, Dict[str, List[Dict[str, object]]]]:
    """
    Load program->entity role mappings and optionally attach entity attributes.
    Returns: {program_id: {role: [entries...]}}
    """
    rows = _read_csv(path)
    roles: Dict[str, Dict[str, List[Dict[str, object]]]] = {}
    for row in rows:
        program_id = (row.get("program_id") or "").strip()
        entity_id = (row.get("entity_id") or "").strip()
        role = (row.get("role") or "").strip().lower()
        if not program_id or not entity_id or not role:
            continue
        try:
            effort = float(row.get("effort_share") or 0.0)
        except ValueError:
            effort = 0.0
        entry: Dict[str, object] = {
            "entity_id": entity_id,
            "effort_share": effort,
            "note": row.get("note", "").strip(),
        }
        if entities is not None:
            ent = entities.get(entity_id)
            if ent:
                entry["entity"] = ent
        roles.setdefault(program_id, {}).setdefault(role, []).append(entry)
    return roles


def derive_role_metrics(roles_by_program: Dict[str, Dict[str, List[Dict[str, object]]]], program_domains: Dict[str, str]) -> Dict[str, Dict[str, float]]:
    """
    Compute coarse metrics (authority strength, capacity, domain alignment, classification penalty)
    from the loaded program-entity roles.
    """
    metrics: Dict[str, Dict[str, float]] = {}
    for program_id, role_map in roles_by_program.items():
        pdomain = program_domains.get(program_id, "")
        sponsor_score = 0.0
        sponsor_weight = 0.0
        exec_score = 0.0
        exec_weight = 0.0
        test_score = 0.0
        test_weight = 0.0
        domain_score = 0.0
        domain_weight = 0.0
        class_penalty = 0.0
        class_weight = 0.0
        transition_count = len(role_map.get("transition_partner", []))

        for role_name, entries in role_map.items():
            for entry in entries:
                ent = entry.get("entity") if isinstance(entry, dict) else None
                effort = float(entry.get("effort_share", 0.0)) if isinstance(entry, dict) else 0.0
                if effort <= 0:
                    effort = 0.1
                if not isinstance(ent, dict):
                    continue
                cap_score = _capacity_score(ent)
                auth_score = _authority_score(ent.get("authority_flags", ""))
                domain_match = _domain_match(pdomain, ent.get("primary_domains", ""))
                c_pen = _classification_penalty(ent.get("classification_band", ""))
                if role_name == "sponsor":
                    sponsor_score += auth_score * effort
                    sponsor_weight += effort
                if role_name in {"executing", "exec"}:
                    exec_score += cap_score * effort
                    exec_weight += effort
                    domain_score += domain_match * effort
                    domain_weight += effort
                if role_name == "test":
                    test_score += cap_score * effort
                    test_weight += effort
                    domain_score += domain_match * effort
                    domain_weight += effort
                class_penalty += c_pen * effort
                class_weight += effort

        def avg(total: float, w: float, default: float = 0.0) -> float:
            return total / w if w > 0 else default

        metrics[program_id] = {
            "sponsor_authority": round(avg(sponsor_score, sponsor_weight, 0.8), 4),
            "executing_capacity": round(avg(exec_score, exec_weight, 0.5), 4),
            "test_capacity": round(avg(test_score, test_weight, 0.5), 4),
            "domain_alignment": round(avg(domain_score, domain_weight, 0.5), 4),
            "classification_penalty": round(avg(class_penalty, class_weight, 0.0), 4),
            "transition_partners": float(transition_count),
        }
    return metrics


def load_vendor_evaluations(path: Optional[str]) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Aggregate vendor evaluations into normalized risk scores.
    Returns (program_risk, vendor_risk) each in [0,1].
    """
    rows = _read_csv(path)
    per_eval: List[Tuple[str, str, float]] = []
    for row in rows:
        program = (row.get("program_id") or "").strip()
        vendor = (row.get("vendor_id") or "").strip()
        if not program and not vendor:
            continue
        try:
            cost = max(0.0, float(row.get("cost_variance_pct") or 0.0))
        except ValueError:
            cost = 0.0
        try:
            sched = max(0.0, float(row.get("schedule_variance_pct") or 0.0))
        except ValueError:
            sched = 0.0
        try:
            tech_rating = float(row.get("technical_rating") or 3.0)
        except ValueError:
            tech_rating = 3.0
        try:
            mgmt_rating = float(row.get("management_rating") or 3.0)
        except ValueError:
            mgmt_rating = 3.0
        try:
            cyber_findings = float(row.get("cyber_findings_count") or 0.0)
        except ValueError:
            cyber_findings = 0.0
        breach = str(row.get("major_breach_flag", "")).strip().lower() in {"1", "true", "yes", "y"}

        cost_score = min(1.0, cost / 30.0)
        sched_score = min(1.0, sched / 30.0)
        tech_pen = min(1.0, (5.0 - tech_rating) / 4.0)
        mgmt_pen = min(1.0, (5.0 - mgmt_rating) / 4.0)
        cyber_pen = min(1.0, cyber_findings / 5.0)
        breach_pen = 0.5 if breach else 0.0
        risk = min(1.0, cost_score * 0.25 + sched_score * 0.25 + tech_pen * 0.2 + mgmt_pen * 0.15 + cyber_pen * 0.1 + breach_pen)
        per_eval.append((program, vendor, risk))

    if not per_eval:
        return {}, {}

    program_scores: Dict[str, List[float]] = {}
    vendor_scores: Dict[str, List[float]] = {}
    for program, vendor, risk in per_eval:
        if program:
            program_scores.setdefault(program, []).append(risk)
        if vendor:
            vendor_scores.setdefault(vendor, []).append(risk)

    def avg(vals: List[float]) -> float:
        return sum(vals) / len(vals) if vals else 0.0

    program_risk = {k: round(avg(v), 6) for k, v in program_scores.items()}
    vendor_risk = {k: round(avg(v), 6) for k, v in vendor_scores.items()}
    return program_risk, vendor_risk


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
