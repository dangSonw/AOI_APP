from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.models.user import User


password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash('dummy-password-for-timing-protection')


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == normalize_email(email)))


def authenticate_user(session: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(session, email)
    if user is None:
        password_hash.verify(password, DUMMY_PASSWORD_HASH)
        return None
    if not password_hash.verify(password, user.hashed_password):
        return None
    return user


def create_user(session: Session, email: str, full_name: str, password: str) -> User:
    user = User(
        email=normalize_email(email),
        full_name=full_name.strip(),
        hashed_password=password_hash.hash(password),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def create_access_token(user: User) -> str:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes,
    )
    return jwt.encode(
        {'sub': str(user.id), 'email': user.email, 'exp': expires_at},
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )