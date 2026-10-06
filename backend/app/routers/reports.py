import os
import json
import asyncio
import shutil
import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List
from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form,
    Query, BackgroundTasks
)
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_

from app.database import get_db
from app.models import Report, User, Hype, StatusLog, UserRole, ReportStatus, Verification, Location
from app.schemas import (
    ReportOut, ReportListItem, PaginatedReports, StatusUpdate,
    AssignUpdate, HypeOut, StatusLogOut, PriorityBreakdown, VerificationOut,
    CatalogChoice,
)
from app.routers.auth import get_current_user, require_role
from app.services.catalog_classifier import classify_catalog_report, load_catalog, map_to_legacy_fields
from app.services.duplicate_detector import find_similar, compute_and_store_embedding
from app.services.priority_engine import compute_priority, update_priority
from app.services.router import route_report
from app.services.notifier import (
    notify_status_change, notify_resolved, notify_disputed,
    notify_safety_critical, notify_duplicate_merged
)
from app.core.config import get_settings

router = APIRouter(prefix="/reports", tags=["reports"])
settings = get_settings()

HYPE_DAILY_LIMIT = 20
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def _save_upload(file: UploadFile) -> str:
    """Save an uploaded file to the uploads directory and return its path."""
    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename)[-1] or ".jpg"
    filename = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(settings.upload_dir, filename)
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return path


def _build_report_out(report: Report, current_user: User, db: Session) -> ReportOut:
    """Hydrate a ReportOut with computed fields."""
    # Hide reporter identity for anonymous reports (unless admin)
    show_reporter = (
        current_user.role == UserRole.admin
        or report.reporter_id == current_user.id
        or not report.is_anonymous
    )

    status_logs = db.query(StatusLog).filter(
        StatusLog.report_id == report.id
    ).order_by(StatusLog.created_at).all()

    status_history = []
    for log in status_logs:
        changer = db.query(User).filter(User.id == log.changed_by).first()
        status_history.append(StatusLogOut(
            id=log.id,
            old_status=log.old_status,
            new_status=log.new_status,
            note=log.note,
            created_at=log.created_at,
            changer_name=changer.name if changer else None,
        ))

    user_hyped = db.query(Hype).filter(
        Hype.report_id == report.id,
        Hype.user_id == current_user.id
    ).first() is not None

    # Priority breakdown
    loc = db.query(Location).filter(Location.building == report.building).first()
    breakdown = compute_priority(report, location_criticality=loc.criticality if loc else 3)
    pb = PriorityBreakdown(**breakdown)

    return ReportOut(
        id=report.id,
        title=report.title,
        description=report.description,
        image_path=report.image_path,
        building=report.building,
        zone=report.zone,
        lat=report.lat,
        lng=report.lng,
        hazard_type=report.hazard_type,
        category=report.category,
        severity=report.severity,
        is_safety_critical=report.is_safety_critical,
        ai_summary=report.ai_summary,
        ai_reasoning=report.ai_reasoning,
        ai_confidence=report.ai_confidence,
        intent=report.intent or "hazard",
        is_campus_related=report.is_campus_related,
        service_group=report.service_group,
        service_subcategory=report.service_subcategory,
        catalog_id=report.catalog_id,
        intent_confidence=report.intent_confidence,
        group_confidence=report.group_confidence,
        subcategory_confidence=report.subcategory_confidence,
        prompt_version=report.prompt_version,
        confirmation_candidates=json.loads(report.confirmation_candidates or "[]"),
        sla_hours=report.sla_hours,
        status=report.status,
        assigned_department=report.assigned_department,
        priority_score=report.priority_score,
        hype_count=report.hype_count,
        recurrence_count=report.recurrence_count,
        duplicate_of=report.duplicate_of,
        is_anonymous=report.is_anonymous,
        created_at=report.created_at,
        updated_at=report.updated_at,
        resolved_at=report.resolved_at,
        reporter_name=report.reporter.name if show_reporter else "Anonymous",
        reporter_id=report.reporter_id if show_reporter else None,
        current_user_hyped=user_hyped,
        status_history=status_history,
        priority_breakdown=pb,
    )


@router.post("", status_code=201)
async def create_report(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: Optional[str] = Form(None),
    building: str = Form(...),
    zone: Optional[str] = Form(None),
    lat: Optional[float] = Form(None),
    lng: Optional[float] = Form(None),
    is_anonymous: bool = Form(False),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    image_path = None
    if image:
        if image.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(400, "Only JPEG, PNG, WebP, GIF images allowed")
        image_path = _save_upload(image)

    report = Report(
        reporter_id=current_user.id,
        title=title,
        description=description,
        image_path=image_path,
        building=building,
        zone=zone,
        lat=lat,
        lng=lng,
        is_anonymous=is_anonymous,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # AI classification
    location = db.query(Location).filter(Location.building == building).first()
    ai_result = await classify_catalog_report(
        image_path, description or title, building, zone or "",
        location.building_type if location else "campus_wide",
    )
    legacy_fields = map_to_legacy_fields(ai_result)
    report.hazard_type = legacy_fields["hazard_type"]
    report.category = legacy_fields["category"]
    report.severity = ai_result.get("severity")
    report.is_safety_critical = ai_result.get("is_safety_critical", False)
    report.intent = ai_result.get("intent", "hazard")
    report.is_campus_related = ai_result.get("is_campus_related", True)
    report.service_group = ai_result.get("service_group")
    report.service_subcategory = ai_result.get("service_subcategory")
    report.catalog_id = ai_result.get("catalog_id")
    report.intent_confidence = ai_result.get("intent_confidence")
    report.group_confidence = ai_result.get("group_confidence")
    report.subcategory_confidence = ai_result.get("subcategory_confidence")
    report.prompt_version = ai_result.get("prompt_version")
    report.confirmation_candidates = json.dumps(ai_result.get("candidates", []))
    report.sla_hours = ai_result.get("sla_hours")
    report.ai_summary = ai_result.get("summary")
    report.ai_reasoning = ai_result.get("reasoning")
    report.ai_confidence = ai_result.get("confidence")
    if report.ai_summary and not title:
        report.title = report.ai_summary
    db.commit()

    # Generate embedding
    await compute_and_store_embedding(report, db)

    # Duplicate detection
    dup_result = await find_similar(report, db)
    if dup_result["status"] == "DUPLICATE":
        parent = db.query(Report).filter(Report.id == dup_result["duplicate_of"]).first()
        if parent:
            report.duplicate_of = parent.id
            parent.hype_count += 1
            db.commit()
            notify_duplicate_merged(db, current_user.id, parent)
            update_priority(parent, db)
    elif dup_result["status"] in ("RECURRING",):
        report.recurrence_count = dup_result["recurrence_count"]
        db.commit()

    # Priority score
    update_priority(report, db)

    # Auto-route
    route_report(report, db)

    # Safety critical alert
    if report.is_safety_critical:
        notify_safety_critical(db, report)

    db.refresh(report)
    return {
        "report": _build_report_out(report, current_user, db),
        "ai_result": ai_result,
        "duplicate_check": dup_result,
    }


@router.get("", response_model=PaginatedReports)
def list_reports(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    building: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    sort: str = Query("priority", enum=["priority", "newest", "hype"]),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Report).filter(Report.duplicate_of == None)

    if status:
        q = q.filter(Report.status == status)
    if category:
        q = q.filter(Report.category == category)
    if building:
        q = q.filter(Report.building == building)
    if department:
        q = q.filter(Report.assigned_department == department)

    if sort == "priority":
        q = q.order_by(desc(Report.priority_score))
    elif sort == "newest":
        q = q.order_by(desc(Report.created_at))
    elif sort == "hype":
        q = q.order_by(desc(Report.hype_count))

    total = q.count()
    reports = q.offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for r in reports:
        show_reporter = (
            current_user.role == UserRole.admin
            or r.reporter_id == current_user.id
            or not r.is_anonymous
        )
        hyped = db.query(Hype).filter(
            Hype.report_id == r.id, Hype.user_id == current_user.id
        ).first() is not None
        items.append(ReportListItem(
            id=r.id,
            title=r.title,
            building=r.building,
            zone=r.zone,
            hazard_type=r.hazard_type,
            category=r.category,
            severity=r.severity,
            is_safety_critical=r.is_safety_critical,
            status=r.status,
            priority_score=r.priority_score,
            hype_count=r.hype_count,
            recurrence_count=r.recurrence_count,
            is_anonymous=r.is_anonymous,
            created_at=r.created_at,
            reporter_name=r.reporter.name if show_reporter else "Anonymous",
            current_user_hyped=hyped,
            image_path=r.image_path,
            intent=r.intent or "hazard",
            service_group=r.service_group,
            service_subcategory=r.service_subcategory,
            prompt_version=r.prompt_version,
        ))

    return PaginatedReports(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, (total + page_size - 1) // page_size),
    )


@router.get("/mine", response_model=List[ReportListItem])
def my_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reports = db.query(Report).filter(
        Report.reporter_id == current_user.id
    ).order_by(desc(Report.created_at)).all()
    return [
        ReportListItem(
            id=r.id, title=r.title, building=r.building, zone=r.zone,
            hazard_type=r.hazard_type, category=r.category, severity=r.severity,
            is_safety_critical=r.is_safety_critical, status=r.status,
            priority_score=r.priority_score, hype_count=r.hype_count,
            recurrence_count=r.recurrence_count, is_anonymous=r.is_anonymous,
            created_at=r.created_at, reporter_name=current_user.name,
            current_user_hyped=False, image_path=r.image_path,
            intent=r.intent or "hazard", service_group=r.service_group,
            service_subcategory=r.service_subcategory, prompt_version=r.prompt_version,
        )
        for r in reports
    ]


@router.get("/{report_id}", response_model=ReportOut)
def get_report(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    return _build_report_out(report, current_user, db)


@router.patch("/{report_id}/classification", response_model=ReportOut)
def confirm_classification(
    report_id: int,
    data: CatalogChoice,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Let the reporter confirm one of the classifier's suggested catalog entries."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    if report.reporter_id != current_user.id and current_user.role != UserRole.admin:
        raise HTTPException(403, "Only the reporter can confirm this classification")
    candidate = next((entry for entry in load_catalog() if entry["id"] == data.catalog_id), None)
    if not candidate:
        raise HTTPException(404, "Catalog entry not found")
    allowed_ids = {item.get("id") for item in json.loads(report.confirmation_candidates or "[]")}
    if data.catalog_id not in allowed_ids:
        raise HTTPException(400, "Choose one of the suggested classifications")

    report.catalog_id = candidate["id"]
    report.service_group = candidate["group"]
    report.service_subcategory = candidate["subcategory"]
    report.intent = candidate["intent"]
    report.sla_hours = candidate["sla_hours"]
    report.assigned_department = candidate["owner_department"]
    if report.intent == "service_request":
        report.severity = None
        report.is_safety_critical = False
    else:
        report.severity = candidate.get("default_severity") or report.severity or 3
    legacy_fields = map_to_legacy_fields({
        "is_campus_related": True,
        "intent": report.intent,
        "service_group": report.service_group,
        "service_subcategory": report.service_subcategory,
    })
    report.category = legacy_fields["category"]
    report.hazard_type = legacy_fields["hazard_type"]
    report.confirmation_candidates = "[]"
    report.ai_reasoning = (report.ai_reasoning or "") + " Classification confirmed by reporter."
    db.commit()
    update_priority(report, db)
    route_report(report, db)
    db.refresh(report)
    return _build_report_out(report, current_user, db)


@router.patch("/{report_id}/status")
def update_status(
    report_id: int,
    data: StatusUpdate,
    current_user: User = Depends(require_role(UserRole.authority, UserRole.admin)),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")

    old_status = report.status.value
    report.status = data.status
    if data.status == ReportStatus.resolved:
        report.resolved_at = datetime.utcnow()

    log = StatusLog(
        report_id=report_id,
        old_status=old_status,
        new_status=data.status.value,
        changed_by=current_user.id,
        note=data.note,
    )
    db.add(log)
    db.commit()

    notify_status_change(db, report, old_status, data.status.value)
    update_priority(report, db)

    return {"status": report.status, "message": "Status updated"}


@router.patch("/{report_id}/assign")
def reassign_report(
    report_id: int,
    data: AssignUpdate,
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    new_authority = db.query(User).filter(User.id == data.assigned_to).first()
    if not new_authority:
        raise HTTPException(404, "User not found")

    old_assigned = report.assigned_to
    report.assigned_to = data.assigned_to
    log = StatusLog(
        report_id=report_id,
        old_status=report.status.value,
        new_status=report.status.value,
        changed_by=current_user.id,
        note=data.note or f"Reassigned from user #{old_assigned} to {new_authority.name}",
    )
    db.add(log)
    db.commit()
    return {"message": f"Reassigned to {new_authority.name}"}


@router.post("/{report_id}/hype", response_model=HypeOut)
def add_hype(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    if report.reporter_id == current_user.id:
        raise HTTPException(400, "You cannot hype your own report")

    # Check daily limit
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_hypes = db.query(Hype).filter(
        Hype.user_id == current_user.id,
        Hype.created_at >= today_start,
    ).count()
    if today_hypes >= HYPE_DAILY_LIMIT:
        raise HTTPException(429, f"Daily hype limit of {HYPE_DAILY_LIMIT} reached")

    existing = db.query(Hype).filter(
        Hype.report_id == report_id, Hype.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(400, "Already hyped this report")

    hype = Hype(report_id=report_id, user_id=current_user.id)
    db.add(hype)
    report.hype_count += 1
    db.commit()
    update_priority(report, db)

    return HypeOut(report_id=report_id, hype_count=report.hype_count, current_user_hyped=True)


@router.delete("/{report_id}/hype", response_model=HypeOut)
def remove_hype(
    report_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")

    hype = db.query(Hype).filter(
        Hype.report_id == report_id, Hype.user_id == current_user.id
    ).first()
    if not hype:
        raise HTTPException(400, "You have not hyped this report")

    db.delete(hype)
    report.hype_count = max(0, report.hype_count - 1)
    db.commit()
    update_priority(report, db)

    return HypeOut(report_id=report_id, hype_count=report.hype_count, current_user_hyped=False)


@router.post("/{report_id}/resolve")
async def resolve_report(
    report_id: int,
    note: str = Form(...),
    after_image: Optional[UploadFile] = File(None),
    current_user: User = Depends(require_role(UserRole.authority, UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Authority submits after-photo. Status -> pending_confirmation."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")

    old_status = report.status.value
    if report.intent == "service_request":
        report.status = ReportStatus.resolved
        report.resolved_at = datetime.utcnow()
        db.add(StatusLog(
            report_id=report_id,
            old_status=old_status,
            new_status=ReportStatus.resolved.value,
            changed_by=current_user.id,
            note=note,
        ))
        db.commit()
        notify_status_change(db, report, old_status, ReportStatus.resolved.value)
        update_priority(report, db)
        return {"message": "Service request completed without photo verification.", "ai_match": None, "flagged_for_review": False}

    if not after_image:
        raise HTTPException(400, "An after-photo is required for hazard verification")

    after_path = _save_upload(after_image)

    # AI verification
    ai_match = {"same_location": None, "issue_resolved": None, "confidence": None}
    if settings.gemini_api_key:
        try:
            from google import genai
            from google.genai import types as genai_types
            from PIL import Image as PILImage
            import json as _json

            client = genai.Client(api_key=settings.gemini_api_key)
            parts = ["Compare these two campus images and return ONLY JSON: "
                     '{"same_location": true/false, "issue_resolved": true/false, "confidence": 0.0-1.0}']
            if report.image_path and os.path.exists(report.image_path):
                parts.append(PILImage.open(report.image_path))
            parts.append(PILImage.open(after_path))
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.gemini_model,
                contents=parts,
                config=genai_types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                    response_schema={
                        "type": "OBJECT",
                        "properties": {
                            "same_location": {"type": "BOOLEAN"},
                            "issue_resolved": {"type": "BOOLEAN"},
                            "confidence": {"type": "NUMBER"},
                        },
                        "required": ["same_location", "issue_resolved", "confidence"],
                    },
                ),
            )
            raw = response.text or ""
            import re
            m = re.search(r"\{.*\}", raw, re.DOTALL)
            if m:
                ai_match = _json.loads(m.group())
        except Exception as e:
            pass

    flagged = (
        ai_match.get("confidence") is not None
        and ai_match["confidence"] < 0.6
    )

    verif = Verification(
        report_id=report_id,
        after_image_path=after_path,
        verified_by_authority=current_user.id,
        ai_match_score=ai_match.get("confidence"),
        ai_same_location=ai_match.get("same_location"),
        ai_issue_resolved=ai_match.get("issue_resolved"),
        flagged_for_review=flagged,
    )
    db.add(verif)

    old_status = report.status.value
    report.status = ReportStatus.pending_confirmation
    log = StatusLog(
        report_id=report_id,
        old_status=old_status,
        new_status=ReportStatus.pending_confirmation.value,
        changed_by=current_user.id,
        note=note,
    )
    db.add(log)
    db.commit()
    notify_resolved(db, report)

    return {
        "message": "Resolution submitted. Awaiting reporter confirmation.",
        "ai_match": ai_match,
        "flagged_for_review": flagged,
    }


@router.post("/{report_id}/confirm")
def confirm_resolution(
    report_id: int,
    confirmed: bool = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Reporter confirms or disputes the resolution."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(404, "Report not found")
    if report.reporter_id != current_user.id:
        raise HTTPException(403, "Only the reporter can confirm resolution")
    if report.status != ReportStatus.pending_confirmation:
        raise HTTPException(400, "Report is not pending confirmation")

    verif = db.query(Verification).filter(Verification.report_id == report_id).first()
    if verif:
        verif.reporter_confirmed = confirmed

    old_status = report.status.value
    if confirmed:
        report.status = ReportStatus.resolved
        report.resolved_at = datetime.utcnow()
        new_status = "resolved"
    else:
        report.status = ReportStatus.reopened
        new_status = "reopened"
        notify_disputed(db, report)

    log = StatusLog(
        report_id=report_id,
        old_status=old_status,
        new_status=new_status,
        changed_by=current_user.id,
        note="Confirmed by reporter" if confirmed else "Disputed by reporter",
    )
    db.add(log)
    db.commit()
    update_priority(report, db)

    return {"status": report.status, "confirmed": confirmed}


@router.post("/admin/auto-resolve-stale")
def auto_resolve_stale(
    current_user: User = Depends(require_role(UserRole.admin)),
    db: Session = Depends(get_db),
):
    """Auto-resolve reports unanswered beyond their catalog SLA (72h legacy default)."""
    now = datetime.utcnow()
    pending = db.query(Report).filter(Report.status == ReportStatus.pending_confirmation).all()
    stale = [
        report for report in pending
        if report.updated_at <= now - timedelta(hours=report.sla_hours or 72)
    ]
    count = 0
    for report in stale:
        report.status = ReportStatus.resolved
        report.resolved_at = datetime.utcnow()
        verif = db.query(Verification).filter(Verification.report_id == report.id).first()
        if verif:
            verif.reporter_confirmed = True  # auto-confirmed
        log = StatusLog(
            report_id=report.id,
            old_status="pending_confirmation",
            new_status="resolved",
            changed_by=current_user.id,
            note=f"Auto-resolved after {report.sla_hours or 72}h SLA elapsed with no reporter response",
        )
        db.add(log)
        count += 1
    db.commit()
    return {"auto_resolved": count}
