"""
Priority Engine — computes a 0-100 priority score for each report.

Formula:
  score = 0.40*severity_norm + 0.25*hype_norm + 0.20*recurrence_norm
        + 0.15*location_criticality_norm + age_bonus
  Safety-critical reports: score is forced to >= 90
"""
import math
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models import Report, Location


# Weights
W_SEVERITY = 0.40
W_HYPE = 0.25
W_RECURRENCE = 0.20
W_LOCATION = 0.15

HYPE_CAP = 50          # log-scaling cap to prevent hype gaming
MAX_AGE_BONUS = 5.0    # max extra points for age
AGE_FULL_BONUS_DAYS = 14  # reach max bonus after 2 weeks unresolved


def _severity_norm(severity: Optional[int]) -> float:
    """Normalize severity 1-5 to 0-1."""
    if not severity:
        return 0.2
    return (severity - 1) / 4.0


def _hype_norm(hype_count: int) -> float:
    """Log-scaled hype, capped to prevent gaming."""
    if hype_count <= 0:
        return 0.0
    capped = min(hype_count, HYPE_CAP)
    return math.log1p(capped) / math.log1p(HYPE_CAP)


def _recurrence_norm(recurrence_count: int) -> float:
    """Normalize recurrence — caps at 5 recurrences."""
    if recurrence_count <= 0:
        return 0.0
    return min(recurrence_count, 5) / 5.0


def _location_norm(criticality: Optional[int]) -> float:
    """Normalize location criticality 1-5 to 0-1."""
    if not criticality:
        return 0.4  # default medium
    return (criticality - 1) / 4.0


def _age_bonus(created_at: datetime) -> float:
    """Small bonus for unresolved issues that have been open a long time."""
    age_days = (datetime.utcnow() - created_at).total_seconds() / 86400
    fraction = min(age_days / AGE_FULL_BONUS_DAYS, 1.0)
    return fraction * MAX_AGE_BONUS


def compute_priority(
    report: Report,
    location_criticality: Optional[int] = None,
    db: Optional[Session] = None,
) -> dict:
    """
    Compute priority score for a report.
    Returns a breakdown dict + final score (0-100).
    """
    # Try to get location criticality from DB if not provided
    if location_criticality is None and db is not None:
        loc = db.query(Location).filter(
            Location.building == report.building
        ).first()
        location_criticality = loc.criticality if loc else 3

    is_service_request = (getattr(report, "intent", None) or "hazard") == "service_request"
    sev = 0.0 if is_service_request else _severity_norm(report.severity)
    hype = _hype_norm(report.hype_count)
    rec = _recurrence_norm(report.recurrence_count)
    loc = _location_norm(location_criticality)

    raw = (W_SEVERITY * sev + W_HYPE * hype + W_RECURRENCE * rec + W_LOCATION * loc) * 100
    age = _age_bonus(report.created_at)

    final = raw + age

    # Safety-critical override
    safety_override = False
    if report.is_safety_critical and not is_service_request and final < 90:
        final = 90.0
        safety_override = True

    final = round(min(100.0, final), 2)

    return {
        "severity_norm": round(sev, 4),
        "hype_norm": round(hype, 4),
        "recurrence_norm": round(rec, 4),
        "location_criticality_norm": round(loc, 4),
        "age_bonus": round(age, 4),
        "final_score": final,
        "safety_critical_override": safety_override,
    }


def update_priority(report: Report, db: Session) -> float:
    """Recompute and persist priority_score on a report."""
    breakdown = compute_priority(report, db=db)
    report.priority_score = breakdown["final_score"]
    db.commit()
    return breakdown["final_score"]
