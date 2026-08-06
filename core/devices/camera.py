from datetime import datetime

from pydantic import Field

from .models import ContractModel
from .motion import Position


class CameraCapabilities(ContractModel):
    camera_ids: tuple[str, ...] = Field(min_length=1)
    sensor_models: tuple[str, ...] = Field(min_length=1)
    maximum_width: int = Field(gt=0, le=100_000)
    maximum_height: int = Field(gt=0, le=100_000)
    supports_raw: bool
    inspection_media_types: tuple[str, ...] = Field(min_length=1)


class CameraConfiguration(ContractModel):
    camera_id: str = Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')
    sensor_mode: str = Field(min_length=1, max_length=128)
    exposure_microseconds: int = Field(gt=0, le=10_000_000)
    analog_gain: float = Field(gt=0, le=256)


class CaptureRequest(ContractModel):
    request_id: str = Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')
    camera_id: str = Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')
    recipe_id: str = Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')
    expected_position: Position
    sensor_mode: str = Field(min_length=1, max_length=128)
    exposure_microseconds: int = Field(gt=0, le=10_000_000)
    analog_gain: float = Field(gt=0, le=256)


class CaptureResult(ContractModel):
    capture_id: str = Field(min_length=1, max_length=128)
    request_id: str = Field(min_length=1, max_length=128)
    status: str = Field(pattern='^ready$')
    camera_id: str
    sensor_model: str
    captured_at: datetime
    monotonic_timestamp_nanoseconds: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    pixel_format: str
    position: Position
    exposure_microseconds: int = Field(gt=0)
    analog_gain: float = Field(gt=0)
    media_type: str
    byte_length: int = Field(gt=0)
    sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    inspection_image_url: str