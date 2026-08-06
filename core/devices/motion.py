from datetime import datetime
from enum import StrEnum

from pydantic import Field

from .models import ContractModel


class Position(ContractModel):
    x_millimeters: float = Field(ge=-1_000_000, le=1_000_000)
    y_millimeters: float = Field(ge=-1_000_000, le=1_000_000)
    z_millimeters: float = Field(ge=-1_000_000, le=1_000_000)


class MotionCapabilities(ContractModel):
    axes: tuple[str, ...] = Field(min_length=1, max_length=8)
    minimum_position: Position
    maximum_position: Position
    supports_homing: bool
    supports_sse: bool


class MotionConfiguration(ContractModel):
    maximum_velocity_millimeters_per_second: float = Field(gt=0, le=100_000)
    maximum_acceleration_millimeters_per_second_squared: float = Field(gt=0, le=1_000_000)
    settle_milliseconds: int = Field(ge=0, le=600_000)


class MoveAbsoluteRequest(ContractModel):
    command_id: str = Field(min_length=1, max_length=128)
    target: Position
    maximum_velocity_millimeters_per_second: float = Field(gt=0, le=100_000)
    maximum_acceleration_millimeters_per_second_squared: float = Field(gt=0, le=1_000_000)
    settle_milliseconds: int = Field(ge=0, le=600_000)


class HomeRequest(ContractModel):
    command_id: str = Field(min_length=1, max_length=128)


class StopRequest(ContractModel):
    command_id: str = Field(min_length=1, max_length=128)


class ClearFaultRequest(ContractModel):
    command_id: str = Field(min_length=1, max_length=128)


class MotionStateName(StrEnum):
    BOOT = 'boot'
    NOT_HOMED = 'not-homed'
    HOMING = 'homing'
    IDLE = 'idle'
    MOVING = 'moving'
    STOPPING = 'stopping'
    FAULT = 'fault'
    EMERGENCY_STOP = 'emergency-stop'


class MotionState(ContractModel):
    revision: int = Field(ge=0)
    state: MotionStateName
    is_homed: bool
    is_in_position: bool
    position: Position
    active_command_id: str | None = None
    emergency_stop: bool = False
    door_closed: bool = True
    communication_connected: bool = True
    fault: str | None = None
    updated_at: datetime


class CommandResult(ContractModel):
    command_id: str
    status: str
    state_revision: int = Field(ge=0)