from datetime import datetime, timezone

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InspectionRun(Base):
    __tablename__ = 'inspection_runs'

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    board_serial: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    lot: Mapped[str] = mapped_column(String(128), default='', nullable=False)
    recipe_id: Mapped[int] = mapped_column(ForeignKey('recipes.id', ondelete='RESTRICT'), index=True, nullable=False)
    operator_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True, nullable=False)
    result_id: Mapped[int | None] = mapped_column(ForeignKey('inspection_results.id', ondelete='RESTRICT'), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(24), index=True, nullable=False)
    current_step: Mapped[str] = mapped_column(String(64), nullable=False)
    progress_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    workflow_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    workflow_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_versions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    station_id: Mapped[str] = mapped_column(String(128), default='station-01', nullable=False)
    work_order_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    commissioning_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    input_artifact: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    decision: Mapped[str | None] = mapped_column(String(16), nullable=True)
    evidence_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    node_runs: Mapped[list['InspectionNodeRun']] = relationship(
        'InspectionNodeRun', back_populates='inspection_run', cascade='all, delete-orphan',
        order_by='InspectionNodeRun.sequence',
    )


class InspectionNodeRun(Base):
    __tablename__ = 'inspection_node_runs'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('inspection_runs.id', ondelete='CASCADE'), index=True, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    node_id: Mapped[str] = mapped_column(String(128), nullable=False)
    node_version: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_target: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSONB, nullable=False)
    inputs: Mapped[dict] = mapped_column(JSONB, nullable=False)
    outputs: Mapped[dict] = mapped_column(JSONB, nullable=False)
    resources: Mapped[dict] = mapped_column(JSONB, nullable=False)
    evidence_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    inspection_run: Mapped[InspectionRun] = relationship('InspectionRun', back_populates='node_runs')


class InspectionReviewEvent(Base):
    __tablename__ = 'inspection_review_events'

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey('inspection_results.id', ondelete='RESTRICT'), index=True, nullable=False)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), index=True, nullable=False)
    decision: Mapped[str] = mapped_column(String(10), nullable=False)
    reason: Mapped[str] = mapped_column(Text, default='', nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)