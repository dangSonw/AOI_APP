from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class InspectionImage(Base):
    __tablename__ = 'inspection_images'

    id: Mapped[int] = mapped_column(primary_key=True)
    result_id: Mapped[int] = mapped_column(ForeignKey('inspection_results.id', ondelete='CASCADE'), index=True, nullable=False)
    defect_id: Mapped[int | None] = mapped_column(ForeignKey('defects.id', ondelete='SET NULL'), index=True, nullable=True)
    image_type: Mapped[str] = mapped_column(String(32), nullable=False)
    relative_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    width_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height_px: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    media_type: Mapped[str] = mapped_column(String(64), default='image/png', nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    inspection_result: Mapped['InspectionResult'] = relationship('InspectionResult', back_populates='images')
    defect: Mapped['Defect | None'] = relationship('Defect')
