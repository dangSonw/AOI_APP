from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, REAL, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Defect(Base):
    __tablename__ = 'defects'

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey('inspection_results.id', ondelete='CASCADE'), index=True, nullable=False)
    defect_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default='medium', nullable=False)
    location_x: Mapped[float | None] = mapped_column(REAL, nullable=True)
    location_y: Mapped[float | None] = mapped_column(REAL, nullable=True)
    width: Mapped[float | None] = mapped_column(REAL, nullable=True)
    height: Mapped[float | None] = mapped_column(REAL, nullable=True)
    confidence: Mapped[float | None] = mapped_column(REAL, nullable=True)
    description: Mapped[str] = mapped_column(Text, default='', nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    inspection_result: Mapped['InspectionResult'] = relationship('InspectionResult', back_populates='defects')
