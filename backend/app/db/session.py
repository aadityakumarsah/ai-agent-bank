from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

database_url = settings.resolved_database_url

# Create database engine
engine = create_engine(
    database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if "sqlite" in database_url else {},
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create all tables if they don't exist. For development convenience only;
    production should use Alembic migrations."""
    from app.db.base import Base
    from app.db import models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    # Seed the demo service directory (no-op if already populated) and, in
    # DEMO_MODE, the demo user + agent history (both idempotent).
    try:
        db = SessionLocal()
        try:
            from app.services.seed_services import seed_service_directory
            from app.services.seed_demo import seed_demo_data

            seed_service_directory(db)
            seed_demo_data(db)
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
