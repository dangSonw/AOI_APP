from datetime import datetime, timezone
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class SettingsActivation(Base):
    __tablename__ = 'settings_activations'
    __table_args__ = (UniqueConstraint('document_id', 'idempotency_key'),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('settings_documents.id', ondelete='CASCADE'), nullable=False)
    requested_version_id: Mapped[int] = mapped_column(ForeignKey('settings_versions.id', ondelete='RESTRICT'), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    observed_target_revision: Mapped[str | None] = mapped_column(String(128), nullable=True)
    diagnostics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    requested_by: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default='', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)