import httpx

from core.devices.motion import (
    ClearFaultRequest,
    CommandResult,
    HomeRequest,
    MotionCapabilities,
    MotionConfiguration,
    MotionState,
    MoveAbsoluteRequest,
    StopRequest,
)

from .device_client import DeviceClient, DeviceServiceError


class MotionClient(DeviceClient):
    def health(self):
        health = super().health()
        if health.service != 'motion':
            raise DeviceServiceError('The configured adapter is not a motion service.', 502)
        return health

    def capabilities(self) -> MotionCapabilities:
        self.require_ready()
        return self.get_model('/capabilities', MotionCapabilities)

    def configuration(self) -> MotionConfiguration:
        self.require_ready()
        return self.get_model('/configuration', MotionConfiguration)

    def configure(self, configuration: MotionConfiguration) -> MotionConfiguration:
        self.require_ready()
        return self.put_model('/configuration', configuration, MotionConfiguration)

    def state(self) -> MotionState:
        self.require_ready()
        return self.get_model('/state', MotionState)

    def home(self, request: HomeRequest) -> CommandResult:
        self.require_ready()
        return self.post_model('/commands/home', request, CommandResult)

    def move_absolute(self, request: MoveAbsoluteRequest) -> CommandResult:
        self.require_ready()
        return self.post_model('/commands/move-absolute', request, CommandResult)

    def stop(self, request: StopRequest | HomeRequest) -> CommandResult:
        self.require_ready()
        return self.post_model('/commands/stop', request, CommandResult)

    def clear_fault(self, request: ClearFaultRequest | HomeRequest) -> CommandResult:
        self.require_ready()
        return self.post_model('/commands/clear-fault', request, CommandResult)