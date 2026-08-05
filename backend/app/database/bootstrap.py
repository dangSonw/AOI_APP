from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.database.base import Base
from app.database.session import SessionLocal, engine
from app.models.user import User  # noqa: F401
from app.services.auth_service import create_user, get_user_by_email


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    settings = get_settings()

    with SessionLocal() as session:
        seed_default_operator(session)


def seed_default_operator(session: Session) -> None:
    settings = get_settings()
    if get_user_by_email(session, settings.seed_admin_email) is None:
        create_user(
            session,
            settings.seed_admin_email,
            settings.seed_admin_full_name,
            settings.seed_admin_password,
        )