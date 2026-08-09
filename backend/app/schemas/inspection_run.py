from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.base import ApiSchema
from core.devices.motion import Position


RunStatus = Literal['queued', 'precheck', 'capturing', 'executing', 'completed', 'faulted', 'cancelled']


class InspectionRunCreateRequest(ApiSchema):
    board_serial: str = Field(min_length=1, max_length=128)
    lot: str = Field(default='', max_length=128)
    recipe_id: int
    station_id: str = Field(default='station-01', pattern=r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')
    work_order_id: str | None = Field(default=None, min_length=1, max_length=128)
    threshold: float = Field(default=0.5, ge=0, le=1)
    camera_id: str = Field(default='top-camera', pattern=r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')
    sensor_mode: str = Field(default='3280x2464', min_length=1, max_length=128)
    exposure_microseconds: int = Field(default=8000, gt=0, le=10_000_000)
    analog_gain: float = Field(default=1, gt=0, le=256)
    expected_position: Position = Position(x_millimeters=0, y_millimeters=0, z_millimeters=0)


class InspectionNodeRunResponse(ApiSchema):
    sequence: int
    node_id: str
    node_version: str
    execution_target: str
    status: str
    parameters: dict
    inputs: dict
    outputs: dict
    resources: dict
    evidence_sha256: str | None
    error_code: str | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
    duration_ms: int | None


class InspectionRunResponse(ApiSchema):
    id: str
    board_serial: str
    lot: str
    recipe_id: int
    station_id: str
    work_order_id: str | None
    commissioning_snapshot: dict
    result_id: int | None
    status: RunStatus
    current_step: str
    progress_percent: int
    cancel_requested: bool
    workflow_sha256: str
    effective_versions: dict
    parameters: dict
    input_artifact: dict | None
    decision: str | None
    evidence_sha256: str | None
    error_code: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    node_runs: list[InspectionNodeRunResponse]


class InspectionReplayResponse(ApiSchema):
    run_id: str
    decision: str
    evidence_sha256: str
    matches_original: bool