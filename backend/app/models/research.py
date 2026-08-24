from datetime import datetime, timezone
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class ResearchExperiment(Base):
    __tablename__ = 'research_experiments'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default='', nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ResearchRun(Base):
    __tablename__ = 'research_runs'
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    experiment_id: Mapped[str] = mapped_column(ForeignKey('research_experiments.id', ondelete='RESTRICT'), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    execution_target: Mapped[str] = mapped_column(String(32), nullable=False)
    code_revision: Mapped[str] = mapped_column(String(64), nullable=False)
    node_versions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    environment: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    random_seeds: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    resources: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    dataset_versions: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    parameters: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output_artifacts: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    parent_run_id: Mapped[str | None] = mapped_column(ForeignKey('research_runs.id', ondelete='RESTRICT'), nullable=True)
    action_name: Mapped[str] = mapped_column(String(64), default='legacy-run', nullable=False)
    node_id: Mapped[str] = mapped_column(String(128), default='legacy', nullable=False)
    node_instance_id: Mapped[str] = mapped_column(String(128), default='legacy', nullable=False)
    node_package_version: Mapped[str] = mapped_column(String(64), default='legacy', nullable=False)
    workflow_revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    progress: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResearchArtifact(Base):
    __tablename__ = 'research_artifacts'
    __table_args__ = (UniqueConstraint('run_id', 'name'),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    run_id: Mapped[str] = mapped_column(ForeignKey('research_runs.id', ondelete='RESTRICT'), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    media_type: Mapped[str] = mapped_column(String(200), nullable=False)
    byte_length: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_uri: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ModelRegistryEntry(Base):
    __tablename__ = 'model_registry_entries'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default='', nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ModelVersion(Base):
    __tablename__ = 'model_versions'
    __table_args__ = (UniqueConstraint('model_id', 'version'),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey('model_registry_entries.id', ondelete='RESTRICT'), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    run_id: Mapped[str] = mapped_column(ForeignKey('research_runs.id', ondelete='RESTRICT'), nullable=False)
    artifact_id: Mapped[int] = mapped_column(ForeignKey('research_artifacts.id', ondelete='RESTRICT'), nullable=False)
    validation_evidence: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ModelAlias(Base):
    __tablename__ = 'model_aliases'
    __table_args__ = (UniqueConstraint('model_id', 'alias'),)
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey('model_registry_entries.id', ondelete='RESTRICT'), nullable=False)
    alias: Mapped[str] = mapped_column(String(32), nullable=False)
    model_version_id: Mapped[int] = mapped_column(ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)


class ModelPromotionEvent(Base):
    __tablename__ = 'model_promotion_events'
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    model_id: Mapped[int] = mapped_column(ForeignKey('model_registry_entries.id', ondelete='RESTRICT'), nullable=False)
    alias: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    previous_version_id: Mapped[int | None] = mapped_column(ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=True)
    next_version_id: Mapped[int] = mapped_column(ForeignKey('model_versions.id', ondelete='RESTRICT'), nullable=False)
    actor_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
