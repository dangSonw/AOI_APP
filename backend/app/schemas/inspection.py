from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import ApiSchema


class DefectResponse(ApiSchema):
    id: int
    defect_type: str
    severity: str
    location_x: float | None = None
    location_y: float | None = None
    width: float | None = None
    height: float | None = None
    confidence: float | None = None
    description: str
    detected_at: datetime


class InspectionImageResponse(ApiSchema):
    id: int
    image_type: str
    relative_path: str
    file_size_bytes: int | None = None
    width_px: int | None = None
    height_px: int | None = None
    sha256_hash: str | None = None
    media_type: str
    defect_id: int | None = None
    captured_at: datetime


class InspectionListItem(ApiSchema):
    id: int
    board_serial: str
    lot: str
    recipe_name: str
    recipe_slug: str
    result: str
    defect_count: int
    score: float | None = None
    cycle_time_ms: int | None = None
    review_decision: str | None = None
    inspected_at: datetime
    operator_name: str


class InspectionDetailResponse(ApiSchema):
    id: int
    board_serial: str
    lot: str
    recipe_name: str
    recipe_slug: str
    result: str
    defect_count: int
    score: float | None = None
    cycle_time_ms: int | None = None
    camera_config: dict | None = None
    review_decision: str | None = None
    reviewed_at: datetime | None = None
    reviewer_name: str | None = None
    inspected_at: datetime
    operator_name: str
    defects: list[DefectResponse]
    images: list[InspectionImageResponse]


class InspectionMetricsResponse(ApiSchema):
    total_inspections: int
    pass_count: int
    fail_count: int
    review_count: int
    first_pass_yield: float
    total_defects: int
    pending_review: int


class InspectionListResponse(ApiSchema):
    items: list[InspectionListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class InspectionCreateRequest(ApiSchema):
    board_serial: str = Field(min_length=1, max_length=128)
    lot: str = Field(default='', max_length=128)
    recipe_id: int
    result: Literal['PASS', 'FAIL', 'REVIEW']
    defect_count: int = Field(default=0, ge=0)
    score: float | None = Field(default=None, ge=0.0, le=1.0)
    cycle_time_ms: int | None = Field(default=None, ge=0)
    camera_config: dict | None = None


class ReviewRequest(ApiSchema):
    decision: Literal['PASS', 'FAIL']
    reason: str = Field(default='', max_length=1000)
