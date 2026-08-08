from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.models.user import User  # noqa: F401
from app.models.recipe import Recipe  # noqa: F401
from app.models.inspection_result import InspectionResult  # noqa: F401
from app.models.defect import Defect  # noqa: F401
from app.models.inspection_image import InspectionImage  # noqa: F401
from app.models.audit_event import AuditEvent  # noqa: F401
from app.services.auth_service import create_user, get_user_by_email


DEFAULT_RECIPES = [
    ('rev-c-mainboard', 'Rev C · Mainboard', 'Main controller board revision C inspection recipe'),
    ('rev-b-power', 'Rev B · Power', 'Power supply board revision B inspection recipe'),
    ('rev-a-sensor', 'Rev A · Sensor', 'Sensor interface board revision A inspection recipe'),
]


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    settings = get_settings()

    with SessionLocal() as session:
        seed_default_operator(session)
        seed_default_recipes(session)


def seed_default_operator(session: Session) -> None:
    settings = get_settings()
    if get_user_by_email(session, settings.seed_admin_email) is None:
        create_user(
            session,
            settings.seed_admin_email,
            settings.seed_admin_full_name,
            settings.seed_admin_password,
        )


def seed_default_recipes(session: Session) -> None:
    for slug, name, description in DEFAULT_RECIPES:
        existing = session.scalar(select(Recipe).where(Recipe.slug == slug))
        if existing is None:
            session.add(Recipe(slug=slug, name=name, description=description))
    session.commit()