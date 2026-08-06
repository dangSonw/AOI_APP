from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from core.devices.models import DeviceMode, DeviceStatus, HealthResponse, PROTOCOL_VERSION, VersionResponse
from core.devices.motion import HomeRequest, MotionCapabilities, MotionConfiguration, MotionState, MoveAbsoluteRequest, Position
from simulator.mcu.motion_service import (
    ClearFaultRequest,
    FaultConfiguration,
    InterlockConfiguration,
    JogRequest,
    MotionConflictError,
    MotionRangeError,
    StopRequest,
    VirtualMotionService,
)


def create_app() -> FastAPI:
    app = FastAPI(title='AOI Simulated Motion Adapter')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://127.0.0.1:9200', 'http://localhost:9200'],
        allow_methods=['GET', 'POST', 'PUT'],
        allow_headers=['Content-Type'],
    )
    motion_capabilities = MotionCapabilities(
        axes=('x', 'y', 'z'),
        minimum_position=Position(x_millimeters=0, y_millimeters=0, z_millimeters=0),
        maximum_position=Position(x_millimeters=300, y_millimeters=200, z_millimeters=150),
        supports_homing=True,
        supports_sse=True,
    )
    service = VirtualMotionService(motion_capabilities)

    @app.get('/health', response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            service='motion',
            implementation='virtual-motion-controller',
            mode=DeviceMode.SIMULATION,
            status=DeviceStatus.READY,
            protocol_version=PROTOCOL_VERSION,
            checked_at=datetime.now(timezone.utc),
            detail='The virtual motion controller is ready.',
        )

    @app.get('/version', response_model=VersionResponse)
    def version() -> VersionResponse:
        return VersionResponse()

    @app.get('/capabilities', response_model=MotionCapabilities)
    def capabilities() -> MotionCapabilities:
        return motion_capabilities

    @app.get('/configuration', response_model=MotionConfiguration)
    def configuration() -> MotionConfiguration:
        return service.configuration

    @app.put('/configuration', response_model=MotionConfiguration)
    def update_configuration(configuration: MotionConfiguration) -> MotionConfiguration:
        return service.configure(configuration)

    @app.get('/state', response_model=MotionState)
    def state() -> MotionState:
        return service.state

    @app.post('/commands/home')
    def home(request: HomeRequest):
        try:
            return service.home(request)
        except MotionConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.post('/commands/move-absolute')
    def move_absolute(request: MoveAbsoluteRequest):
        try:
            return service.move_absolute(request)
        except MotionConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except MotionRangeError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post('/commands/jog')
    def jog(request: JogRequest):
        try:
            return service.jog(request)
        except MotionConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except MotionRangeError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post('/commands/stop')
    def stop(request: StopRequest):
        return service.stop(request)

    @app.post('/commands/clear-fault')
    def clear_fault(request: ClearFaultRequest):
        try:
            return service.clear_fault(request)
        except MotionConflictError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @app.put('/simulation/interlocks', response_model=MotionState)
    def configure_interlocks(configuration: InterlockConfiguration) -> MotionState:
        return service.configure_interlocks(configuration)

    @app.put('/simulation/fault', response_model=MotionState)
    def inject_fault(configuration: FaultConfiguration) -> MotionState:
        return service.inject_fault(configuration)

    @app.post('/simulation/reset', response_model=MotionState)
    def reset() -> MotionState:
        return service.reset()

    @app.get('/events')
    def events(after_revision: int = 0) -> Response:
        return Response(service.events_after(after_revision), media_type='text/event-stream')

    return app


app = create_app()