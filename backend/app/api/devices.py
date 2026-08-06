from collections.abc import Generator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Response, status

from app.auth.dependencies import CurrentUser
from app.clients.camera_client import CameraClient
from app.clients.device_client import DeviceServiceError
from app.clients.motion_client import MotionClient
from app.config.settings import get_settings
from core.devices.camera import CameraCapabilities, CameraConfiguration, CaptureRequest, CaptureResult
from core.devices.models import ContractModel, HealthResponse
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


SAFE_IDENTIFIER_PATTERN = r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$'
router = APIRouter(prefix='/api', tags=['devices'])


class DeviceOverview(ContractModel):
    camera: HealthResponse
    motion: HealthResponse


def get_camera_client() -> Generator[CameraClient, None, None]:
    client = CameraClient(get_settings().camera_adapter_url)
    try:
        yield client
    finally:
        client.close()


def get_motion_client() -> Generator[MotionClient, None, None]:
    client = MotionClient(get_settings().motion_adapter_url)
    try:
        yield client
    finally:
        client.close()


CameraClientDependency = Annotated[CameraClient, Depends(get_camera_client)]
MotionClientDependency = Annotated[MotionClient, Depends(get_motion_client)]


def raise_device_error(error: DeviceServiceError) -> None:
    raise HTTPException(status_code=error.status_code, detail=str(error)) from error


@router.get('/devices', response_model=DeviceOverview)
def get_devices(
    _: CurrentUser,
    camera: CameraClientDependency,
    motion: MotionClientDependency,
) -> DeviceOverview:
    try:
        return DeviceOverview(camera=camera.health(), motion=motion.health())
    except DeviceServiceError as error:
        raise_device_error(error)


@router.get('/camera/health', response_model=HealthResponse)
def get_camera_health(_: CurrentUser, camera: CameraClientDependency) -> HealthResponse:
    try:
        return camera.health()
    except DeviceServiceError as error:
        raise_device_error(error)


@router.get('/camera/capabilities', response_model=CameraCapabilities)
def get_camera_capabilities(_: CurrentUser, camera: CameraClientDependency) -> CameraCapabilities:
    try:
        return camera.capabilities()
    except DeviceServiceError as error:
        raise_device_error(error)


@router.get('/camera/configuration', response_model=CameraConfiguration)
def get_camera_configuration(_: CurrentUser, camera: CameraClientDependency) -> CameraConfiguration:
    try:
        return camera.configuration()
    except DeviceServiceError as error:
        raise_device_error(error)


@router.put('/camera/configuration', response_model=CameraConfiguration)
def update_camera_configuration(
    configuration: CameraConfiguration,
    _: CurrentUser,
    camera: CameraClientDependency,
) -> CameraConfiguration:
    try:
        return camera.configure(configuration)
    except DeviceServiceError as error:
        raise_device_error(error)


@router.get('/camera/preview')
def get_camera_preview(_: CurrentUser, camera: CameraClientDependency) -> Response:
    try:
        image = camera.preview()
        return Response(
            image.content,
            media_type=image.media_type,
            headers={'X-Content-SHA256': image.sha256, 'Cache-Control': 'no-store'},
        )
    except DeviceServiceError as error:
        raise_device_error(error)


@router.post('/camera/captures', response_model=CaptureResult, status_code=status.HTTP_201_CREATED)
def create_camera_capture(
    request: CaptureRequest,
    _: CurrentUser,
    camera: CameraClientDependency,
) -> CaptureResult:
    try:
        return camera.capture(request)
    except DeviceServiceError as error:
        raise_device_error(error)


@router.get('/camera/captures/{capture_id}/inspection-image')
def get_camera_inspection_image(
    _: CurrentUser,
    camera: CameraClientDependency,
    capture_id: Annotated[str, Path(pattern=SAFE_IDENTIFIER_PATTERN)],
) -> Response:
    try:
        image = camera.inspection_image(capture_id)
        return Response(
            image.content,
            media_type=image.media_type,
            headers={'X-Content-SHA256': image.sha256},
        )
    except DeviceServiceError as error:
        raise_device_error(error)


@router.get('/motion/health', response_model=HealthResponse)
def get_motion_health(_: CurrentUser, motion: MotionClientDependency) -> HealthResponse:
    try:
        return motion.health()
    except DeviceServiceError as error:
        raise_device_error(error)


@router.get('/motion/capabilities', response_model=MotionCapabilities)
def get_motion_capabilities(_: CurrentUser, motion: MotionClientDependency) -> MotionCapabilities:
    try:
        return motion.capabilities()
    except DeviceServiceError as error:
        raise_device_error(error)


@router.get('/motion/configuration', response_model=MotionConfiguration)
def get_motion_configuration(_: CurrentUser, motion: MotionClientDependency) -> MotionConfiguration:
    try:
        return motion.configuration()
    except DeviceServiceError as error:
        raise_device_error(error)


@router.put('/motion/configuration', response_model=MotionConfiguration)
def update_motion_configuration(
    configuration: MotionConfiguration,
    _: CurrentUser,
    motion: MotionClientDependency,
) -> MotionConfiguration:
    try:
        return motion.configure(configuration)
    except DeviceServiceError as error:
        raise_device_error(error)


@router.get('/motion/state', response_model=MotionState)
def get_motion_state(_: CurrentUser, motion: MotionClientDependency) -> MotionState:
    try:
        return motion.state()
    except DeviceServiceError as error:
        raise_device_error(error)


@router.post('/motion/commands/home', response_model=CommandResult)
def home_motion(
    request: HomeRequest,
    _: CurrentUser,
    motion: MotionClientDependency,
) -> CommandResult:
    try:
        return motion.home(request)
    except DeviceServiceError as error:
        raise_device_error(error)


@router.post('/motion/commands/move-absolute', response_model=CommandResult)
def move_motion_absolute(
    request: MoveAbsoluteRequest,
    _: CurrentUser,
    motion: MotionClientDependency,
) -> CommandResult:
    try:
        return motion.move_absolute(request)
    except DeviceServiceError as error:
        raise_device_error(error)


@router.post('/motion/commands/stop', response_model=CommandResult)
def stop_motion(
    request: StopRequest,
    _: CurrentUser,
    motion: MotionClientDependency,
) -> CommandResult:
    try:
        return motion.stop(request)
    except DeviceServiceError as error:
        raise_device_error(error)


@router.post('/motion/commands/clear-fault', response_model=CommandResult)
def clear_motion_fault(
    request: ClearFaultRequest,
    _: CurrentUser,
    motion: MotionClientDependency,
) -> CommandResult:
    try:
        return motion.clear_fault(request)
    except DeviceServiceError as error:
        raise_device_error(error)