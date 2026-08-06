from datetime import datetime, timezone

from fastapi import FastAPI

from core.devices.models import DeviceMode, DeviceStatus, HealthResponse, PROTOCOL_VERSION, VersionResponse
from core.devices.motion import MotionCapabilities, MotionConfiguration, Position


def create_app() -> FastAPI:
    app = FastAPI(title='AOI Hardware Motion Adapter')
    motion_configuration = MotionConfiguration(
        maximum_velocity_millimeters_per_second=20,
        maximum_acceleration_millimeters_per_second_squared=40,
        settle_milliseconds=250,
    )

    @app.get('/health', response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            service='motion',
            implementation='uart-motion-controller',
            mode=DeviceMode.HARDWARE,
            status=DeviceStatus.UNAVAILABLE,
            protocol_version=PROTOCOL_VERSION,
            checked_at=datetime.now(timezone.utc),
            detail='The MCU UART transport has not been opened.',
        )

    @app.get('/version', response_model=VersionResponse)
    def version() -> VersionResponse:
        return VersionResponse()

    @app.get('/capabilities', response_model=MotionCapabilities)
    def capabilities() -> MotionCapabilities:
        return MotionCapabilities(
            axes=('x', 'y', 'z'),
            minimum_position=Position(x_millimeters=0, y_millimeters=0, z_millimeters=0),
            maximum_position=Position(x_millimeters=300, y_millimeters=200, z_millimeters=150),
            supports_homing=True,
            supports_sse=True,
        )

    @app.get('/configuration', response_model=MotionConfiguration)
    def configuration() -> MotionConfiguration:
        return motion_configuration

    @app.put('/configuration', response_model=MotionConfiguration)
    def update_configuration(configuration: MotionConfiguration) -> MotionConfiguration:
        nonlocal motion_configuration
        motion_configuration = configuration
        return motion_configuration

    return app


app = create_app()