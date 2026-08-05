from datetime import datetime

from pydantic import Field

from app.schemas.base import ApiSchema


SignalValue = bool | int | float | str


class MachineInputState(ApiSchema):
    emergency_stop: bool
    inspection_trigger: bool
    door_closed: bool


class PhysicalInputState(ApiSchema):
    revision: int = Field(ge=0)
    updated_at: datetime
    machine: MachineInputState
    sensors: dict[str, SignalValue]


class PhysicalOutputState(ApiSchema):
    revision: int = Field(ge=0)
    updated_at: datetime
    signals: dict[str, SignalValue]


class PhysicalOutputUpdate(ApiSchema):
    signals: dict[str, SignalValue]