from datetime import datetime, timezone

from fastapi import FastAPI

from core.devices.camera import CameraCapabilities, CameraConfiguration
from core.devices.models import (
    DeviceMode,
    DeviceStatus,
    HealthResponse,
    PROTOCOL_VERSION,
    VersionResponse,
)


def create_app() -> FastAPI:
    app = FastAPI(title='AOI Hardware Camera Adapter')
    camera_configuration = CameraConfiguration(
        camera_id='top-camera',
        sensor_mode='3280x2464',
        exposure_microseconds=8000,
        analog_gain=1,
    )

    @app.get('/health', response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            service='camera',
            implementation='jetson-csi-camera',
            mode=DeviceMode.HARDWARE,
            status=DeviceStatus.UNAVAILABLE,
            protocol_version=PROTOCOL_VERSION,
            checked_at=datetime.now(timezone.utc),
            detail='The Jetson CSI camera has not been opened.',
        )

    @app.get('/version', response_model=VersionResponse)
    def version() -> VersionResponse:
        return VersionResponse()

    @app.get('/capabilities', response_model=CameraCapabilities)
    def capabilities() -> CameraCapabilities:
        return CameraCapabilities(
            camera_ids=('top-camera',),
            sensor_models=('unknown-csi-sensor',),
            maximum_width=3280,
            maximum_height=2464,
            supports_raw=False,
            inspection_media_types=('image/png', 'image/tiff'),
        )

    @app.get('/configuration', response_model=CameraConfiguration)
    def configuration() -> CameraConfiguration:
        return camera_configuration

    @app.put('/configuration', response_model=CameraConfiguration)
    def update_configuration(configuration: CameraConfiguration) -> CameraConfiguration:
        nonlocal camera_configuration
        camera_configuration = configuration
        return camera_configuration

    return app


app = create_app()