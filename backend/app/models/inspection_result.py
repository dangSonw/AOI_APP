from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, REAL, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class InspectionResult(Base):
    __tablename__ = 'inspection_results'

    id: Mapped[int] = mapped_column(primary_key=True)
    board_serial: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    lot: Mapped[str] = mapped_column(String(128), default='', nullable=False)
    recipe_id: Mapped[int] = mapped_column(ForeignKey('recipes.id'), index=True, nullable=False)
    recipe_name: Mapped[str] = mapped_column(String(255), nullable=False)
    operator_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True, nullable=False)
    result: Mapped[str] = mapped_column(String(10), index=True, nullable=False)
    defect_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    score: Mapped[float | None] = mapped_column(REAL, nullable=True)
    cycle_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    camera_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    review_decision: Mapped[str | None] = mapped_column(String(10), nullable=True)
    reviewed_by: Mapped[int | None] = mapped_column(ForeignKey('users.id'), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inspected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    recipe: Mapped['Recipe'] = relationship('Recipe', back_populates='inspection_results')
    operator: Mapped['User'] = relationship('User', foreign_keys=[operator_id])
    reviewer: Mapped['User | None'] = relationship('User', foreign_keys=[reviewed_by])
    defects: Mapped[list['Defect']] = relationship(
        'Defect', back_populates='inspection_result', cascade='all, delete-orphan',
    )
    images: Mapped[list['InspectionImage']] = relationship(
        'InspectionImage', back_populates='inspection_result', cascade='all, delete-orphan',
    )
