"""
Smart routing — maps hazard category to department and auto-assigns to least-loaded authority.
"""
import logging
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Report, User, UserRole, ReportStatus, StatusLog
from app.services.notifier import notify_assigned
from app.services.catalog_classifier import load_catalog

logger = logging.getLogger(__name__)

LEGACY_CATEGORY_DEPARTMENT = {
    "electrical": "Electrical",
    "civil": "Civil",
    "security": "Security",
    "other": "Admin",
}


def route_report(report: Report, db: Session) -> None:
    """
    Auto-assign a report to the least-loaded authority in the appropriate department.
    Sets status to 'assigned' and writes a StatusLog entry.
    """
    catalog_entry = next(
        (entry for entry in load_catalog() if entry["id"] == report.catalog_id), None
    ) if report.catalog_id else None
    category = getattr(report.category, "value", report.category or "other")
    department = catalog_entry["owner_department"] if catalog_entry else LEGACY_CATEGORY_DEPARTMENT.get(category, "Admin")
    report.assigned_department = department

    # Find least-loaded authority in this department
    open_statuses = [ReportStatus.assigned, ReportStatus.in_progress]
    authority = (
        db.query(User)
        .filter(User.role == UserRole.authority, User.department == department)
        .outerjoin(
            Report,
            (Report.assigned_to == User.id) & (Report.status.in_(open_statuses))
        )
        .group_by(User.id)
        .order_by(func.count(Report.id).asc())
        .first()
    )

    old_status = report.status.value if report.status else "reported"

    if authority:
        report.assigned_to = authority.id
        report.status = ReportStatus.assigned
        log = StatusLog(
            report_id=report.id,
            old_status=old_status,
            new_status=ReportStatus.assigned.value,
            changed_by=authority.id,
            note=f"Auto-assigned to {authority.name} ({department})",
        )
        db.add(log)
        db.commit()
        notify_assigned(db, report)
        logger.info(f"Report #{report.id} routed to {authority.name} ({department})")
    else:
        # No authority available in this department — assign to any admin
        admin = db.query(User).filter(User.role == UserRole.admin).first()
        if admin:
            report.assigned_to = admin.id
        report.assigned_department = department
        report.status = ReportStatus.assigned
        log = StatusLog(
            report_id=report.id,
            old_status=old_status,
            new_status=ReportStatus.assigned.value,
            changed_by=admin.id if admin else report.reporter_id,
            note=f"Routed to {department} — no authority available, assigned to admin queue.",
        )
        db.add(log)
        db.commit()
        logger.warning(f"No authority for {department}, report #{report.id} assigned to admin")
