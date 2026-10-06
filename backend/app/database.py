from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False}  # SQLite specific
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def apply_sqlite_migrations() -> None:
    """Add catalog fields to existing demo databases without dropping data."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as connection:
        if "reports" in tables:
            columns = {column["name"] for column in inspector.get_columns("reports")}
            additions = {
                "intent": "VARCHAR(30) NOT NULL DEFAULT 'hazard'",
                "is_campus_related": "BOOLEAN NOT NULL DEFAULT 1",
                "service_group": "VARCHAR(150)",
                "service_subcategory": "VARCHAR(150)",
                "catalog_id": "VARCHAR(200)",
                "intent_confidence": "FLOAT",
                "group_confidence": "FLOAT",
                "subcategory_confidence": "FLOAT",
                "prompt_version": "VARCHAR(20)",
                "confirmation_candidates": "TEXT",
                "sla_hours": "INTEGER",
            }
            for name, column_type in additions.items():
                if name not in columns:
                    connection.execute(text(f"ALTER TABLE reports ADD COLUMN {name} {column_type}"))
        if "locations" in tables:
            columns = {column["name"] for column in inspector.get_columns("locations")}
            if "building_type" not in columns:
                connection.execute(text(
                    "ALTER TABLE locations ADD COLUMN building_type VARCHAR(40) NOT NULL DEFAULT 'campus_wide'"
                ))
            for label, building_pattern in (
                ("hostel", "%hostel%"), ("library", "%library%"),
                ("lab", "%science%"), ("lab", "%block a%"), ("academic", "%block b%"),
                ("sports", "%sports%"), ("admin", "%admin%"),
                ("transport", "%parking%"), ("medical", "%medical%"),
                ("food_service", "%canteen%"),
            ):
                connection.execute(text(
                    "UPDATE locations SET building_type = :label "
                    "WHERE building_type = 'campus_wide' AND lower(building) LIKE :pattern"
                ), {"label": label, "pattern": building_pattern})


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
