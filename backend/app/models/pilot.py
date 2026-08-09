from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.inspection_run import utc_now


class CalibrationRecord(Base):
    __tablename__ = 'calibration_records'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    station_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    camera_id: Mapped[str] = mapped_column(String(128), nullable=False)
    calibration_type: Mapped[str] = mapped_column(String(32), nullable=False)
    artifact_relative_path: Mapped[str] = mapped_column(Text, nullable=False)
    artifact_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    valid_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommissioningProfile(Base):
    __tablename__ = 'commissioning_profiles'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    station_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    deployment_mode: Mapped[str] = mapped_column(String(32), nullable=False)
    calibration_id: Mapped[str | None] = mapped_column(ForeignKey('calibration_records.id', ondelete='RESTRICT'))
    signal_mapping: Mapped[dict] = mapped_column(JSONB, nullable=False)
    integration_policy: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CommissioningActivationEvent(Base):
    __tablename__ = 'commissioning_activation_events'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    station_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    profile_id: Mapped[str] = mapped_column(ForeignKey('commissioning_profiles.id', ondelete='RESTRICT'), nullable=False)
    previous_profile_id: Mapped[str | None] = mapped_column(ForeignKey('commissioning_profiles.id', ondelete='RESTRICT'))
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IntegrationOutboxEvent(Base):
    __tablename__ = 'integration_outbox_events'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    run_id: Mapped[str] = mapped_column(ForeignKey('inspection_runs.id', ondelete='RESTRICT'), index=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default='pending', nullable=False)
    attempt_count: Mapped[int] = mapped_column(default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)