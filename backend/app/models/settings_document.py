from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class SettingsDocument(Base):
    __tablename__ = 'settings_documents'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    scope: Mapped[str] = mapped_column(String(32), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(256), nullable=False)
    document_key: Mapped[str] = mapped_column(String(128), nullable=False)
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=True)
    current_revision: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_version_id: Mapped[int | None] = mapped_column(
        ForeignKey('settings_versions.id', name='fk_settings_documents_current_version', use_alter=True), nullable=True,
    )
    active_version_id: Mapped[int | None] = mapped_column(
        ForeignKey('settings_versions.id', name='fk_settings_documents_active_version', use_alter=True), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)