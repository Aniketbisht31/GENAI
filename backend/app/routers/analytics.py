from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from statistics import median
from typing import List

from app.database import get_db
from app.models import Report, User, Hype, UserRole, ReportStatus
from app.schemas import AnalyticsSummary
from app.routers.auth import require_role

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    all_reports = db.query(Report).all()
    total = len(all_reports)
    open_count = sum(1 for r in all_reports if r.status not in (ReportStatus.resolved,))
    resolved = sum(1 for r in all_reports if r.status == ReportStatus.resolved)
    critical_open = sum(1 for r in all_reports if r.is_safety_critical and r.status != ReportStatus.resolved)

    # Duplicates
    duplicates = sum(1 for r in all_reports if r.duplicate_of is not None)
    dup_pct = round((duplicates / total * 100) if total else 0, 1)

    # Resolution times
    res_times = []
    for r in all_reports:
        if r.resolved_at and r.created_at:
            delta = (r.resolved_at - r.created_at).total_seconds() / 3600
            res_times.append(delta)
    avg_res = round(sum(res_times) / len(res_times), 1) if res_times else None
    med_res = round(median(res_times), 1) if res_times else None

    # By status
    by_status = {}
    for r in all_reports:
        key = r.status.value
        by_status[key] = by_status.get(key, 0) + 1

    # By category
    by_category = {}
    for r in all_reports:
        key = r.category.value if r.category else "unknown"
        by_category[key] = by_category.get(key, 0) + 1

    by_service_group = {}
    for r in all_reports:
        key = r.service_group or "Unclassified"
        by_service_group[key] = by_service_group.get(key, 0) + 1

    # Top buildings
    building_counts = {}
    for r in all_reports:
        building_counts[r.building] = building_counts.get(r.building, 0) + 1
    top_buildings = sorted(
        [{"building": k, "count": v} for k, v in building_counts.items()],
        key=lambda x: x["count"], reverse=True
    )[:5]

    # Recurring issues
    recurring = sorted(
        [r for r in all_reports if r.recurrence_count > 0],
        key=lambda x: x.recurrence_count, reverse=True
    )[:10]
    recurring_issues = [
        {"id": r.id, "title": r.title, "building": r.building, "recurrence_count": r.recurrence_count}
        for r in recurring
    ]

    # Reports per day (last 30 days)
    thirty_ago = datetime.utcnow() - timedelta(days=30)
    day_counts = {}
    for r in all_reports:
        if r.created_at >= thirty_ago:
            day = r.created_at.strftime("%Y-%m-%d")
            day_counts[day] = day_counts.get(day, 0) + 1
    reports_per_day = [{"date": k, "count": v} for k, v in sorted(day_counts.items())]

    # Hype leaderboard (top reported buildings by hype)
    hype_map = {}
    for r in all_reports:
        hype_map[r.building] = hype_map.get(r.building, 0) + r.hype_count
    hype_leaderboard = sorted(
        [{"building": k, "total_hypes": v} for k, v in hype_map.items()],
        key=lambda x: x["total_hypes"], reverse=True
    )[:5]

    # Resolution time by department
    dept_times: dict = {}
    for r in all_reports:
        if r.resolved_at and r.created_at and r.assigned_department:
            hrs = (r.resolved_at - r.created_at).total_seconds() / 3600
            dept_times.setdefault(r.assigned_department, []).append(hrs)
    resolution_by_department = [
        {
            "department": dept,
            "avg_hours": round(sum(times) / len(times), 1),
            "count": len(times),
        }
        for dept, times in dept_times.items()
    ]

    return AnalyticsSummary(
        total_reports=total,
        open_reports=open_count,
        resolved_reports=resolved,
        avg_resolution_hours=avg_res,
        median_resolution_hours=med_res,
        duplicate_percentage=dup_pct,
        critical_open=critical_open,
        by_status=by_status,
        by_category=by_category,
        top_buildings=top_buildings,
        recurring_issues=recurring_issues,
        reports_per_day=reports_per_day,
        hype_leaderboard=hype_leaderboard,
        resolution_by_department=resolution_by_department,
        by_service_group=by_service_group,
    )
