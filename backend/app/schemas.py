from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime
from app.models import UserRole, ReportStatus, HazardType, Category


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.student
    department: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    department: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ── Location ──────────────────────────────────────────────────────────────────

class LocationOut(BaseModel):
    id: int
    building: str
    zone: Optional[str]
    criticality: int
    building_type: str = "campus_wide"

    class Config:
        from_attributes = True


# ── Report ────────────────────────────────────────────────────────────────────

class AIResult(BaseModel):
    hazard_type: Optional[str] = None
    category: Optional[str] = None
    severity: Optional[int] = None
    is_safety_critical: bool = False
    summary: Optional[str] = None
    reasoning: Optional[str] = None
    confidence: Optional[float] = None
    intent: Optional[str] = None
    is_campus_related: bool = True
    service_group: Optional[str] = None
    service_subcategory: Optional[str] = None
    catalog_id: Optional[str] = None
    intent_confidence: Optional[float] = None
    group_confidence: Optional[float] = None
    subcategory_confidence: Optional[float] = None
    prompt_version: Optional[str] = None
    candidates: List[dict] = Field(default_factory=list)


class PriorityBreakdown(BaseModel):
    severity_norm: float
    hype_norm: float
    recurrence_norm: float
    location_criticality_norm: float
    age_bonus: float
    final_score: float
    safety_critical_override: bool


class StatusLogOut(BaseModel):
    id: int
    old_status: Optional[str]
    new_status: str
    note: Optional[str]
    created_at: datetime
    changer_name: Optional[str] = None

    class Config:
        from_attributes = True


class ReportOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    image_path: Optional[str]
    building: str
    zone: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    hazard_type: Optional[HazardType]
    category: Optional[Category]
    severity: Optional[int]
    is_safety_critical: bool
    ai_summary: Optional[str]
    ai_reasoning: Optional[str]
    ai_confidence: Optional[float]
    intent: str = "hazard"
    is_campus_related: bool = True
    service_group: Optional[str] = None
    service_subcategory: Optional[str] = None
    catalog_id: Optional[str] = None
    intent_confidence: Optional[float] = None
    group_confidence: Optional[float] = None
    subcategory_confidence: Optional[float] = None
    prompt_version: Optional[str] = None
    confirmation_candidates: List[dict] = Field(default_factory=list)
    sla_hours: Optional[int] = None
    status: ReportStatus
    assigned_department: Optional[str]
    priority_score: float
    hype_count: int
    recurrence_count: int
    duplicate_of: Optional[int]
    is_anonymous: bool
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]

    # Hydrated fields (set by endpoint)
    reporter_name: Optional[str] = None
    reporter_id: Optional[int] = None
    current_user_hyped: bool = False
    status_history: List[StatusLogOut] = []
    priority_breakdown: Optional[PriorityBreakdown] = None

    class Config:
        from_attributes = True


class ReportListItem(BaseModel):
    id: int
    title: str
    building: str
    zone: Optional[str]
    hazard_type: Optional[HazardType]
    category: Optional[Category]
    severity: Optional[int]
    is_safety_critical: bool
    status: ReportStatus
    priority_score: float
    hype_count: int
    recurrence_count: int
    is_anonymous: bool
    created_at: datetime
    reporter_name: Optional[str] = None
    current_user_hyped: bool = False
    image_path: Optional[str] = None
    intent: str = "hazard"
    service_group: Optional[str] = None
    service_subcategory: Optional[str] = None
    prompt_version: Optional[str] = None

    class Config:
        from_attributes = True


class PaginatedReports(BaseModel):
    items: List[ReportListItem]
    total: int
    page: int
    page_size: int
    pages: int


# ── Status update ─────────────────────────────────────────────────────────────

class StatusUpdate(BaseModel):
    status: ReportStatus
    note: Optional[str] = None


class AssignUpdate(BaseModel):
    assigned_to: int
    note: Optional[str] = None


class CatalogChoice(BaseModel):
    catalog_id: str


# ── Hype ──────────────────────────────────────────────────────────────────────

class HypeOut(BaseModel):
    report_id: int
    hype_count: int
    current_user_hyped: bool


# ── Duplicate ─────────────────────────────────────────────────────────────────

class DuplicateResult(BaseModel):
    status: str  # DUPLICATE | POSSIBLE_DUPLICATE | UNIQUE | RECURRING
    duplicate_of: Optional[int] = None
    suggestions: List[dict] = []
    recurrence_count: int = 0
    message: Optional[str] = None


# ── Verification ─────────────────────────────────────────────────────────────

class VerificationOut(BaseModel):
    id: int
    after_image_path: str
    reporter_confirmed: Optional[bool]
    ai_match_score: Optional[float]
    ai_same_location: Optional[bool]
    ai_issue_resolved: Optional[bool]
    flagged_for_review: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Notification ─────────────────────────────────────────────────────────────

class NotificationOut(BaseModel):
    id: int
    report_id: Optional[int]
    message: str
    channel: str
    sent_at: datetime
    read: bool

    class Config:
        from_attributes = True


# ── Analytics ─────────────────────────────────────────────────────────────────

class AnalyticsSummary(BaseModel):
    total_reports: int
    open_reports: int
    resolved_reports: int
    avg_resolution_hours: Optional[float]
    median_resolution_hours: Optional[float]
    duplicate_percentage: float
    critical_open: int
    by_status: dict
    by_category: dict
    top_buildings: List[dict]
    recurring_issues: List[dict]
    reports_per_day: List[dict]
    hype_leaderboard: List[dict]
    resolution_by_department: List[dict]
    by_service_group: dict = Field(default_factory=dict)
