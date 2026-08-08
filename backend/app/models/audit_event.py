from datetime import datetime, timezone

from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class AuditEvent(Base):
    __tablename__ = 'audit_events'

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    action: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    method: Mapped[str] = mapped_column(String(8), nullable=False)
    path: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    request_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    before_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    after_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, 'postgresql'), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )