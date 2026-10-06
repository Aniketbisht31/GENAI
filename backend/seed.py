"""
Seed script: creates admin, 3 authorities, 5 students,
12 campus locations, and 25 realistic sample reports.
Run from /backend: python seed.py
"""
import os
import sys
import json
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base, apply_sqlite_migrations
from app.models import User, Report, Hype, StatusLog, Location, Notification, UserRole, ReportStatus
from app.routers.auth import hash_password
from app.services.priority_engine import compute_priority

apply_sqlite_migrations()
Base.metadata.create_all(bind=engine)
db = SessionLocal()

# ── Wipe existing data ────────────────────────────────────────────────────────
db.query(Notification).delete()
db.query(StatusLog).delete()
db.query(Hype).delete()
db.query(Report).delete()
db.query(Location).delete()
db.query(User).delete()
db.commit()
print("Cleared existing data.")

# ── Locations ─────────────────────────────────────────────────────────────────
locations_data = [
    ("Main Library", "Ground Floor", 3, "library"),
    ("Main Library", "First Floor", 3, "library"),
    ("Engineering Block A", "Lab Wing", 5, "lab"),
    ("Engineering Block B", "Corridor", 4, "academic"),
    ("Hostel Block 1", "Common Room", 4, "hostel"),
    ("Hostel Block 2", "Stairwell", 5, "hostel"),
    ("Canteen", "Main Hall", 3, "food_service"),
    ("Sports Complex", "Gym", 2, "sports"),
    ("Admin Building", "Reception", 3, "admin"),
    ("Science Block", "Chemistry Lab", 5, "lab"),
    ("Parking Lot", "North Entrance", 2, "transport"),
    ("Medical Centre", "Waiting Area", 4, "medical"),
]
locs = []
for building, zone, criticality, building_type in locations_data:
    loc = Location(building=building, zone=zone, criticality=criticality, building_type=building_type)
    db.add(loc)
    locs.append(loc)
db.commit()
print(f"Created {len(locs)} locations.")

# ── Users ─────────────────────────────────────────────────────────────────────
admin = User(
    name="Admin Singh", email="admin@university.edu",
    password_hash=hash_password("admin123"),
    role=UserRole.admin, department=None,
)
db.add(admin)

authorities = [
    User(name="Raj Electrical", email="raj.elec@university.edu",
         password_hash=hash_password("auth123"), role=UserRole.authority, department="Electrical"),
    User(name="Priya Civil", email="priya.civil@university.edu",
         password_hash=hash_password("auth123"), role=UserRole.authority, department="Civil"),
    User(name="Suresh Security", email="suresh.sec@university.edu",
         password_hash=hash_password("auth123"), role=UserRole.authority, department="Security"),
    User(name="Hostel Warden", email="warden@university.edu", password_hash=hash_password("auth123"), role=UserRole.authority, department="Hostel Warden"),
    User(name="Campus IT", email="it@university.edu", password_hash=hash_password("auth123"), role=UserRole.authority, department="IT"),
    User(name="Fire & Safety Officer", email="fire.safety@university.edu", password_hash=hash_password("auth123"), role=UserRole.authority, department="Fire & Safety"),
    User(name="Housekeeping Lead", email="housekeeping@university.edu", password_hash=hash_password("auth123"), role=UserRole.authority, department="Housekeeping"),
    User(name="HVAC Technician", email="hvac@university.edu", password_hash=hash_password("auth123"), role=UserRole.authority, department="HVAC"),
    User(name="Transport Coordinator", email="transport@university.edu", password_hash=hash_password("auth123"), role=UserRole.authority, department="Transport"),
    User(name="Student Services Officer", email="student.services@university.edu", password_hash=hash_password("auth123"), role=UserRole.authority, department="Student Services"),
    User(name="Medical Centre Lead", email="medical@university.edu", password_hash=hash_password("auth123"), role=UserRole.authority, department="Medical"),
    User(name="Librarian", email="library@university.edu", password_hash=hash_password("auth123"), role=UserRole.authority, department="Library"),
    User(name="Facilities Coordinator", email="facilities@university.edu", password_hash=hash_password("auth123"), role=UserRole.authority, department="Facilities"),
    User(name="Procurement Officer", email="procurement@university.edu", password_hash=hash_password("auth123"), role=UserRole.authority, department="Procurement"),
    User(name="Events Coordinator", email="events@university.edu", password_hash=hash_password("auth123"), role=UserRole.authority, department="Events"),
]
for a in authorities:
    db.add(a)

students = [
    User(name="Arjun Kumar", email="arjun@student.edu", password_hash=hash_password("student123"), role=UserRole.student),
    User(name="Sneha Reddy", email="sneha@student.edu", password_hash=hash_password("student123"), role=UserRole.student),
    User(name="Vikram Nair", email="vikram@student.edu", password_hash=hash_password("student123"), role=UserRole.student),
    User(name="Meera Sharma", email="meera@student.edu", password_hash=hash_password("student123"), role=UserRole.student),
    User(name="Dev Patel", email="dev@student.edu", password_hash=hash_password("student123"), role=UserRole.student),
]
for s in students:
    db.add(s)

db.commit()
db.refresh(admin)
for a in authorities:
    db.refresh(a)
for s in students:
    db.refresh(s)
print(f"Created 1 admin, {len(authorities)} authorities, {len(students)} students.")

# ── Reports ───────────────────────────────────────────────────────────────────
from app.models import HazardType, Category

reports_data = [
    # (title, description, building, zone, hazard_type, category, severity, is_critical, status, hype, recurrence)
    ("Exposed wiring near socket", "Electrical wire hanging loose near the lab entrance. Sparking when touched.", "Engineering Block A", "Lab Wing", "exposed_wiring", "electrical", 5, True, "assigned", 12, 0),
    ("Broken step on staircase", "Third step on the main staircase is cracked and wobbly.", "Hostel Block 2", "Stairwell", "broken_infrastructure", "civil", 4, False, "in_progress", 8, 1),
    ("Ceiling water leak", "Water dripping from ceiling near the server room entrance.", "Main Library", "First Floor", "water_leakage", "civil", 3, False, "reported", 5, 0),
    ("Street light not working", "The lamp post at north parking lot has been dark for 3 days.", "Parking Lot", "North Entrance", "broken_light", "civil", 2, False, "resolved", 3, 2),
    ("Suspicious person loitering", "Unidentified person near hostel block after midnight.", "Hostel Block 1", "Common Room", "suspicious_activity", "security", 4, True, "assigned", 7, 0),
    ("Gas smell in chemistry lab", "Strong gas odour near ventilation in chem lab. Possible leak.", "Science Block", "Chemistry Lab", "fire_risk", "civil", 5, True, "in_progress", 15, 0),
    ("Flooded corridor after rain", "Water pooling 5cm deep in Engineering Block B corridor.", "Engineering Block B", "Corridor", "water_leakage", "civil", 3, False, "in_progress", 6, 1),
    ("Broken glass door", "Main entry door glass shattered, sharp shards on floor.", "Admin Building", "Reception", "broken_infrastructure", "civil", 4, False, "pending_confirmation", 4, 0),
    ("Overflowing dustbin", "Garbage bin outside canteen overflowing since 2 days.", "Canteen", "Main Hall", "sanitation", "civil", 2, False, "resolved", 2, 3),
    ("CCTV camera not working", "Camera at hostel block 2 entrance showing black screen.", "Hostel Block 2", "Stairwell", "other", "security", 3, False, "assigned", 3, 0),
    ("Faulty gym equipment", "Treadmill motor making grinding noise, safety guard missing.", "Sports Complex", "Gym", "broken_infrastructure", "civil", 3, False, "reported", 5, 0),
    ("Pot hole near library gate", "Large pothole near the library gate causing bike damage.", "Main Library", "Ground Floor", "pothole", "civil", 2, False, "reported", 9, 2),
    ("Exposed switchboard", "Open switchboard with live wires in library first floor.", "Main Library", "First Floor", "exposed_wiring", "electrical", 4, True, "assigned", 11, 0),
    ("Broken railing on ramp", "Wheelchair ramp railing is loose and unsafe.", "Medical Centre", "Waiting Area", "broken_infrastructure", "civil", 3, False, "reported", 4, 0),
    ("Rodent infestation canteen", "Rats spotted in canteen kitchen area multiple times.", "Canteen", "Main Hall", "sanitation", "civil", 3, False, "in_progress", 13, 4),
    ("Elevator not working", "Lift in Hostel Block 1 stuck between floors, stuck 2 hours.", "Hostel Block 1", "Common Room", "broken_infrastructure", "civil", 4, False, "resolved", 6, 1),
    ("Water cooler broken", "Water cooler near library entrance leaking. Floor wet and slippery.", "Main Library", "Ground Floor", "water_leakage", "civil", 3, False, "reported", 4, 0),
    ("Graffiti on walls", "Offensive graffiti on engineering block wall.", "Engineering Block B", "Corridor", "other", "security", 1, False, "resolved", 1, 0),
    ("Fire alarm false trigger", "Fire alarm triggered without any fire — disrupted exams.", "Engineering Block A", "Lab Wing", "fire_risk", "civil", 3, False, "assigned", 7, 1),
    ("Parking lot flooding", "North parking lot floods every time it rains.", "Parking Lot", "North Entrance", "water_leakage", "civil", 2, False, "reported", 8, 3),
    ("AC unit sparking", "Air conditioner in chemistry lab sparking and smelling burnt.", "Science Block", "Chemistry Lab", "exposed_wiring", "electrical", 5, True, "in_progress", 14, 0),
    ("Broken window latch", "Window in engineering block B cannot be locked.", "Engineering Block B", "Corridor", "broken_infrastructure", "civil", 2, False, "resolved", 2, 0),
    ("Sewage smell near hostel", "Strong sewage smell near Hostel Block 2 entrance.", "Hostel Block 2", "Stairwell", "sanitation", "civil", 3, False, "reported", 6, 2),
    ("Missing manhole cover", "Open manhole near science block, no cover, no warning sign.", "Science Block", "Chemistry Lab", "unsafe_structure", "civil", 5, True, "assigned", 10, 0),
    ("Gym equipment electrical fault", "Gym treadmill making sparking sound from power outlet.", "Sports Complex", "Gym", "exposed_wiring", "electrical", 4, True, "reported", 8, 0),
]

# Department mapping
DEPT_MAP = {"electrical": "Electrical", "civil": "Civil", "security": "Security", "other": "Admin"}
AUTH_MAP = {a.department: a for a in authorities}
AUTH_MAP["Admin"] = admin
CATALOG_EXAMPLES = {
    "electrical": ("Electrical Services", "Lighting"),
    "civil": ("Civil & Plumbing Services", "Building Repairs"),
    "security": ("Security Services", "CCTV Monitoring"),
    "other": ("Facility Services", "General Maintenance"),
}
from app.services.catalog_classifier import load_catalog
catalog_entries = load_catalog()
catalog_by_group_subcategory = {(entry["group"], entry["subcategory"]): entry for entry in catalog_entries}

created_reports = []
base_time = datetime.utcnow() - timedelta(days=25)

for i, (title, desc, building, zone, htype, cat, sev, critical, status, hype, recurrence) in enumerate(reports_data):
    reporter = random.choice(students)
    dept = DEPT_MAP.get(cat, "Admin")
    authority = AUTH_MAP.get(dept, admin)
    group, subcategory = CATALOG_EXAMPLES[cat]
    catalog_entry = catalog_by_group_subcategory[(group, subcategory)]

    created_at = base_time + timedelta(days=i, hours=random.randint(0, 10))
    resolved_at = None
    if status == "resolved":
        resolved_at = created_at + timedelta(days=random.randint(1, 4))

    r = Report(
        reporter_id=reporter.id,
        title=title,
        description=desc,
        building=building,
        zone=zone,
        hazard_type=htype,
        category=cat,
        severity=sev,
        is_safety_critical=critical,
        ai_summary=title,
        ai_reasoning=f"AI detected {htype} with severity {sev}.",
        ai_confidence=round(random.uniform(0.75, 0.98), 2),
        intent="hazard",
        is_campus_related=True,
        service_group=group,
        service_subcategory=subcategory,
        catalog_id=catalog_entry["id"],
        intent_confidence=round(random.uniform(0.75, 0.98), 2),
        group_confidence=round(random.uniform(0.75, 0.98), 2),
        subcategory_confidence=round(random.uniform(0.75, 0.98), 2),
        prompt_version="v2",
        sla_hours=catalog_entry["sla_hours"],
        status=status,
        assigned_department=dept,
        assigned_to=authority.id if status != "reported" else None,
        hype_count=hype,
        recurrence_count=recurrence,
        is_anonymous=(i % 7 == 0),
        created_at=created_at,
        updated_at=created_at + timedelta(hours=2),
        resolved_at=resolved_at,
    )
    db.add(r)
    db.flush()

    # Priority score
    loc_criticality = next((l.criticality for l in locs if l.building == building), 3)
    breakdown = compute_priority(r, location_criticality=loc_criticality)
    r.priority_score = breakdown["final_score"]

    # Status log
    log = StatusLog(
        report_id=r.id,
        old_status=None,
        new_status="reported",
        changed_by=reporter.id,
        note="Report submitted",
        created_at=created_at,
    )
    db.add(log)
    if status != "reported":
        log2 = StatusLog(
            report_id=r.id,
            old_status="reported",
            new_status=status,
            changed_by=authority.id,
            note="Status updated by authority",
            created_at=created_at + timedelta(hours=3),
        )
        db.add(log2)

    # Add some hypes from students
    hype_users = random.sample(students, min(hype % 5, len(students)))
    for su in hype_users:
        if su.id != reporter.id:
            h = Hype(report_id=r.id, user_id=su.id, created_at=created_at + timedelta(hours=1))
            db.add(h)

    created_reports.append(r)

db.commit()
print(f"Created {len(created_reports)} reports with status logs, hypes, and priority scores.")

print("\n✅ Seed complete!")
print("\n── Demo credentials ────────────────────────────────")
print("Admin:      admin@university.edu      / admin123")
print("Electrical: raj.elec@university.edu   / auth123")
print("Civil:      priya.civil@university.edu / auth123")
print("Security:   suresh.sec@university.edu  / auth123")
print("Student 1:  arjun@student.edu          / student123")
print("Student 2:  sneha@student.edu          / student123")
print("─────────────────────────────────────────────────────")
