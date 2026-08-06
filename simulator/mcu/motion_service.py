import json
from datetime import datetime, timezone
from typing import Literal

from pydantic import Field

from core.devices.models import ContractModel
from core.devices.motion import (
    ClearFaultRequest,
    CommandResult,
    HomeRequest,
    MotionCapabilities,
    MotionConfiguration,
    MotionState,
    MotionStateName,
    MoveAbsoluteRequest,
    Position,
    StopRequest,
)


AxisName = Literal['x', 'y', 'z']
InjectedMotionFault = Literal[
    'none',
    'axis-stuck',
    'homing-timeout',
    'position-stale',
    'limit-hit',
    'command-timeout',
]


class JogRequest(ContractModel):
    command_id: str = Field(min_length=1, max_length=128)
    axis: AxisName
    distance_millimeters: float = Field(ge=-1_000, le=1_000)
    maximum_velocity_millimeters_per_second: float = Field(gt=0, le=100_000)


class InterlockConfiguration(ContractModel):
    door_closed: bool = True
    emergency_stop: bool = False
    communication_connected: bool = True


class FaultConfiguration(ContractModel):
    fault: InjectedMotionFault = 'none'


class MotionConflictError(RuntimeError):
    pass


class MotionRangeError(RuntimeError):
    pass


class VirtualMotionService:
    def __init__(self, capabilities: MotionCapabilities) -> None:
        self.capabilities = capabilities
        self.state = MotionState(
            revision=0,
            state=MotionStateName.NOT_HOMED,
            is_homed=False,
            is_in_position=False,
            position=capabilities.minimum_position,
            updated_at=datetime.now(timezone.utc),
        )
        self._commands: dict[str, CommandResult] = {}
        self._events: list[tuple[int, str, dict[str, object]]] = []
        self.configuration = MotionConfiguration(
            maximum_velocity_millimeters_per_second=20,
            maximum_acceleration_millimeters_per_second_squared=40,
            settle_milliseconds=250,
        )

    def configure(self, configuration: MotionConfiguration) -> MotionConfiguration:
        self.configuration = configuration
        return configuration

    def reset(self) -> MotionState:
        self._commands.clear()
        self._events.clear()
        self.state = MotionState(
            revision=self.state.revision + 1,
            state=MotionStateName.NOT_HOMED,
            is_homed=False,
            is_in_position=False,
            position=self.capabilities.minimum_position,
            emergency_stop=False,
            door_closed=True,
            communication_connected=True,
            updated_at=datetime.now(timezone.utc),
        )
        self._record_event('state', {'reason': 'simulation-reset', **self._state_payload()})
        return self.state

    def home(self, request: HomeRequest) -> CommandResult:
        existing = self._commands.get(request.command_id)
        if existing is not None:
            return existing
        self._require_motion_allowed()
        self.state = self.state.model_copy(update={
            'revision': self.state.revision + 1,
            'state': MotionStateName.IDLE,
            'is_homed': True,
            'is_in_position': True,
            'position': self.capabilities.minimum_position,
            'updated_at': datetime.now(timezone.utc),
        })
        result = CommandResult(command_id=request.command_id, status='completed', state_revision=self.state.revision)
        self._commands[request.command_id] = result
        self._record_event('state', {'reason': 'homing-complete', **self.state.model_dump(mode='json', by_alias=True)})
        return result

    def move_absolute(self, request: MoveAbsoluteRequest) -> CommandResult:
        existing = self._commands.get(request.command_id)
        if existing is not None:
            return existing
        self._require_motion_allowed()
        if not self.state.is_homed:
            raise MotionConflictError('The motion system must be homed before moving.')
        if not self._is_inside_workspace(request.target):
            raise MotionRangeError('The target is outside the configured motion workspace.')
        self.state = self.state.model_copy(update={
            'revision': self.state.revision + 1,
            'state': MotionStateName.IDLE,
            'is_in_position': True,
            'position': request.target,
            'active_command_id': None,
            'updated_at': datetime.now(timezone.utc),
        })
        result = CommandResult(command_id=request.command_id, status='completed', state_revision=self.state.revision)
        self._commands[request.command_id] = result
        self._record_event('state', {'reason': 'in-position', **self.state.model_dump(mode='json', by_alias=True)})
        return result

    def jog(self, request: JogRequest) -> CommandResult:
        existing = self._commands.get(request.command_id)
        if existing is not None:
            return existing
        self._require_motion_allowed()
        if not self.state.is_homed:
            raise MotionConflictError('The motion system must be homed before jogging.')
        coordinates = self.state.position.model_dump()
        coordinate_key = f'{request.axis}_millimeters'
        coordinates[coordinate_key] += request.distance_millimeters
        target = Position(**coordinates)
        move_request = MoveAbsoluteRequest(
            command_id=request.command_id,
            target=target,
            maximum_velocity_millimeters_per_second=request.maximum_velocity_millimeters_per_second,
            maximum_acceleration_millimeters_per_second_squared=100,
            settle_milliseconds=0,
        )
        return self.move_absolute(move_request)

    def stop(self, request: StopRequest) -> CommandResult:
        existing = self._commands.get(request.command_id)
        if existing is not None:
            return existing
        self.state = self.state.model_copy(update={
            'revision': self.state.revision + 1,
            'state': MotionStateName.IDLE if self.state.is_homed else MotionStateName.NOT_HOMED,
            'is_in_position': False,
            'active_command_id': None,
            'updated_at': datetime.now(timezone.utc),
        })
        result = CommandResult(command_id=request.command_id, status='completed', state_revision=self.state.revision)
        self._commands[request.command_id] = result
        self._record_event('state', {'reason': 'stopped', **self._state_payload()})
        return result

    def configure_interlocks(self, configuration: InterlockConfiguration) -> MotionState:
        fault: str | None = self.state.fault
        state = self.state.state
        if configuration.emergency_stop:
            fault = 'Emergency stop is active.'
            state = MotionStateName.EMERGENCY_STOP
        elif not configuration.communication_connected:
            fault = 'MCU communication is disconnected.'
            state = MotionStateName.FAULT
        elif not configuration.door_closed:
            fault = 'The safety door is open.'
            state = MotionStateName.FAULT
        self.state = self.state.model_copy(update={
            'revision': self.state.revision + 1,
            'state': state,
            'is_in_position': False if fault else self.state.is_in_position,
            'emergency_stop': configuration.emergency_stop,
            'door_closed': configuration.door_closed,
            'communication_connected': configuration.communication_connected,
            'fault': fault,
            'updated_at': datetime.now(timezone.utc),
        })
        self._record_event('state', {'reason': 'interlock-changed', **self._state_payload()})
        return self.state

    def inject_fault(self, configuration: FaultConfiguration) -> MotionState:
        if configuration.fault == 'none':
            return self.state
        self.state = self.state.model_copy(update={
            'revision': self.state.revision + 1,
            'state': MotionStateName.FAULT,
            'is_in_position': False,
            'fault': configuration.fault,
            'updated_at': datetime.now(timezone.utc),
        })
        self._record_event('fault', {'reason': 'fault-injected', **self._state_payload()})
        return self.state

    def clear_fault(self, request: ClearFaultRequest) -> CommandResult:
        existing = self._commands.get(request.command_id)
        if existing is not None:
            return existing
        if self.state.emergency_stop:
            raise MotionConflictError('Release emergency stop before clearing the fault.')
        if not self.state.door_closed:
            raise MotionConflictError('Close the safety door before clearing the fault.')
        if not self.state.communication_connected:
            raise MotionConflictError('Restore MCU communication before clearing the fault.')
        self.state = self.state.model_copy(update={
            'revision': self.state.revision + 1,
            'state': MotionStateName.IDLE if self.state.is_homed else MotionStateName.NOT_HOMED,
            'fault': None,
            'updated_at': datetime.now(timezone.utc),
        })
        result = CommandResult(command_id=request.command_id, status='completed', state_revision=self.state.revision)
        self._commands[request.command_id] = result
        self._record_event('state', {'reason': 'fault-cleared', **self._state_payload()})
        return result

    def events_after(self, revision: int) -> str:
        chunks = []
        for event_revision, event_name, data in self._events:
            if event_revision > revision:
                chunks.append(
                    f'id: {event_revision}\nevent: {event_name}\ndata: '
                    f'{json.dumps(data, separators=(",", ":"))}\n\n'
                )
        return ''.join(chunks)

    def _record_event(self, event_name: str, data: dict[str, object]) -> None:
        self._events.append((self.state.revision, event_name, data))

    def _state_payload(self) -> dict[str, object]:
        return self.state.model_dump(mode='json', by_alias=True)

    def _require_motion_allowed(self) -> None:
        if self.state.emergency_stop:
            raise MotionConflictError('Emergency stop is active.')
        if not self.state.door_closed:
            raise MotionConflictError('The safety door is open.')
        if not self.state.communication_connected:
            raise MotionConflictError('MCU communication is disconnected.')
        if self.state.fault:
            raise MotionConflictError('Clear the active motion fault before moving.')

    def _is_inside_workspace(self, position: Position) -> bool:
        minimum = self.capabilities.minimum_position
        maximum = self.capabilities.maximum_position
        return (
            minimum.x_millimeters <= position.x_millimeters <= maximum.x_millimeters
            and minimum.y_millimeters <= position.y_millimeters <= maximum.y_millimeters
            and minimum.z_millimeters <= position.z_millimeters <= maximum.z_millimeters
        )