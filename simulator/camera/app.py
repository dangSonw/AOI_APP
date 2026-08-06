from datetime import datetime, timezone
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from core.devices.camera import CameraCapabilities, CameraConfiguration, CaptureRequest, CaptureResult
from core.devices.models import DeviceMode, DeviceStatus, HealthResponse, PROTOCOL_VERSION, VersionResponse
from simulator.camera.capture_service import (
    CameraSimulationConfiguration,
    CameraSimulationError,
    ReplayCaptureService,
    SourceImage,
)


def create_app(capture_directory: Path | None = None) -> FastAPI:
    app = FastAPI(title='AOI Simulated Camera Adapter')
    app.add_middleware(
        CORSMiddleware,
        allow_origins=['http://127.0.0.1:9200', 'http://localhost:9200'],
        allow_methods=['GET', 'POST', 'PUT', 'DELETE'],
        allow_headers=['Content-Type'],
    )
    service = ReplayCaptureService(capture_directory or Path('data/captures/simulator'))

    @app.get('/health', response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(
            service='camera',
            implementation='replay-camera',
            mode=DeviceMode.SIMULATION,
            status=DeviceStatus.READY,
            protocol_version=PROTOCOL_VERSION,
            checked_at=datetime.now(timezone.utc),
            detail='The replay camera is ready.',
        )

    @app.get('/version', response_model=VersionResponse)
    def version() -> VersionResponse:
        return VersionResponse()

    @app.get('/capabilities', response_model=CameraCapabilities)
    def capabilities() -> CameraCapabilities:
        return CameraCapabilities(
            camera_ids=('top-camera',),
            sensor_models=('simulated-imx219',),
            maximum_width=3280,
            maximum_height=2464,
            supports_raw=False,
            inspection_media_types=('image/png', 'image/tiff'),
        )

    @app.get('/configuration', response_model=CameraConfiguration)
    def configuration() -> CameraConfiguration:
        return service.camera_configuration

    @app.put('/configuration', response_model=CameraConfiguration)
    def update_configuration(configuration: CameraConfiguration) -> CameraConfiguration:
        return service.configure_camera(configuration)

    @app.get('/preview', response_class=Response)
    def preview() -> Response:
        try:
            return Response(
                service.preview_bytes(),
                media_type='image/png',
                headers={'Cache-Control': 'no-store'},
            )
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post('/captures', response_model=CaptureResult, status_code=status.HTTP_201_CREATED)
    def capture(request: CaptureRequest) -> CaptureResult:
        try:
            return service.capture(request)
        except CameraSimulationError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @app.get('/captures/{capture_id}/inspection-image', response_class=FileResponse)
    def inspection_image(capture_id: str) -> FileResponse:
        artifact_path = service.artifact_path(capture_id)
        if not artifact_path.is_file():
            raise HTTPException(status_code=404, detail='The capture artifact does not exist.')
        return FileResponse(artifact_path, media_type='image/png')

    @app.get('/simulation/configuration', response_model=CameraSimulationConfiguration)
    def simulation_configuration() -> CameraSimulationConfiguration:
        return service.configuration

    @app.put('/simulation/configuration', response_model=CameraSimulationConfiguration)
    def update_simulation_configuration(
        configuration: CameraSimulationConfiguration,
    ) -> CameraSimulationConfiguration:
        try:
            return service.configure(configuration)
        except (FileNotFoundError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get('/simulation/images', response_model=list[SourceImage])
    def source_images() -> list[SourceImage]:
        return service.list_sources()

    @app.put('/simulation/images/{image_id}', response_model=SourceImage, status_code=201)
    def upload_source_image(
        image_id: str,
        image_bytes: bytes = Body(media_type='image/png'),
        filename: str = Query(min_length=1, max_length=255),
    ) -> SourceImage:
        if not image_id.replace('-', '').replace('_', '').replace('.', '').isalnum():
            raise HTTPException(status_code=422, detail='The image ID contains unsupported characters.')
        try:
            return service.upload_source(image_id, filename, 'image/png', image_bytes)
        except TypeError as error:
            raise HTTPException(status_code=415, detail=str(error)) from error
        except OverflowError as error:
            raise HTTPException(status_code=413, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get('/simulation/preview', response_class=Response)
    def simulation_preview() -> Response:
        try:
            return Response(
                service.preview_bytes(),
                media_type='image/png',
                headers={'Cache-Control': 'no-store'},
            )
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    return app


app = create_app()