from datetime import datetime, timezone

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import FileResponse

from core.devices.camera import CameraCapabilities, CameraConfiguration, CaptureRequest, CaptureResult
from core.devices.models import (
    DeviceMode,
    DeviceStatus,
    HealthResponse,
    PROTOCOL_VERSION,
    VersionResponse,
)
from hardware.camera.csi_capture import CsiCaptureError, JetsonCsiCaptureService


def create_app(capture_service: JetsonCsiCaptureService | None = None) -> FastAPI:
    app = FastAPI(title='AOI Hardware Camera Adapter')
    service = capture_service or JetsonCsiCaptureService(Path('data/captures/hardware'))

    @app.get('/health', response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            service='camera',
            implementation='jetson-csi-camera',
            mode=DeviceMode.HARDWARE,
            status=DeviceStatus.READY if service.is_available else DeviceStatus.UNAVAILABLE,
            protocol_version=PROTOCOL_VERSION,
            checked_at=datetime.now(timezone.utc),
            detail='Jetson CSI pipeline is available.' if service.is_available else 'The Jetson CSI camera pipeline is unavailable.',
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
        return service.configuration

    @app.put('/configuration', response_model=CameraConfiguration)
    def update_configuration(configuration: CameraConfiguration) -> CameraConfiguration:
        try:
            return service.configure(configuration)
        except CsiCaptureError as error:
            raise HTTPException(422, str(error)) from error

    @app.post('/captures', response_model=CaptureResult, status_code=status.HTTP_201_CREATED)
    def capture(request: CaptureRequest) -> CaptureResult:
        try:
            return service.capture(request)
        except CsiCaptureError as error:
            raise HTTPException(503, str(error)) from error

    @app.get('/captures/{capture_id}/inspection-image', response_class=FileResponse)
    def inspection_image(capture_id: str) -> FileResponse:
        path = service.artifact_path(capture_id)
        if not path.is_file():
            raise HTTPException(404, 'Capture artifact does not exist.')
        return FileResponse(path, media_type='image/png')

    return app


app = create_app()