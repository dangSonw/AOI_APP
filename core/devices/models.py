from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


PROTOCOL_VERSION = '1.0'


class ContractModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class DeviceMode(StrEnum):
    HARDWARE = 'hardware'
    SIMULATION = 'simulation'


class DeviceStatus(StrEnum):
    READY = 'ready'
    DEGRADED = 'degraded'
    UNAVAILABLE = 'unavailable'


class HealthResponse(ContractModel):
    service: str = Field(min_length=1, max_length=64)
    implementation: str = Field(min_length=1, max_length=128)
    mode: DeviceMode
    status: DeviceStatus
    protocol_version: str = Field(pattern=r'^\d+\.\d+$')
    checked_at: datetime
    detail: str | None = Field(default=None, max_length=500)


class VersionResponse(ContractModel):
    protocol_version: str = PROTOCOL_VERSION