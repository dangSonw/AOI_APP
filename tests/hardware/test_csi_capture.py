import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from core.devices.camera import CameraConfiguration, CaptureRequest
from core.devices.motion import Position
from hardware.camera.csi_capture import CsiCaptureError, JetsonCsiCaptureService
from hardware.camera.app import create_app
from simulator.camera.capture_service import create_test_pattern_png


def request() -> CaptureRequest:
    return CaptureRequest(
        request_id='csi-capture-1', camera_id='top-camera', recipe_id='rev-c-mainboard',
        expected_position=Position(x_millimeters=1, y_millimeters=2, z_millimeters=3),
        sensor_mode='3280x2464', exposure_microseconds=8000, analog_gain=1,
    )


def test_csi_capture_uses_bounded_argv_and_publishes_verified_png_atomically(tmp_path: Path) -> None:
    calls: list[tuple[list[str], float]] = []

    def runner(argv: list[str], timeout_seconds: float) -> None:
        calls.append((argv, timeout_seconds))
        output = Path(argv[argv.index('filesink') + 1].removeprefix('location='))
        output.write_bytes(create_test_pattern_png())

    service = JetsonCsiCaptureService(tmp_path, runner=runner, pipeline_available=lambda: True)
    result = service.capture(request())
    artifact = service.artifact_path(result.capture_id)

    assert calls and calls[0][0][0] == 'gst-launch-1.0'
    assert all('\n' not in argument and '\x00' not in argument for argument in calls[0][0])
    assert result.media_type == 'image/png'
    assert artifact.name == 'csi-capture-1.png'
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() == result.sha256
    assert not list(tmp_path.glob('*.tmp'))


def test_csi_capture_fails_closed_without_pipeline_or_complete_artifact(tmp_path: Path) -> None:
    unavailable = JetsonCsiCaptureService(tmp_path, pipeline_available=lambda: False)
    with pytest.raises(CsiCaptureError, match='unavailable'):
        unavailable.capture(request())

    def incomplete(argv: list[str], _: float) -> None:
        output = Path(argv[argv.index('filesink') + 1].removeprefix('location='))
        output.write_bytes(b'partial-frame')

    service = JetsonCsiCaptureService(tmp_path, runner=incomplete, pipeline_available=lambda: True)
    with pytest.raises(CsiCaptureError, match='PNG'):
        service.capture(request())
    assert not (tmp_path / 'csi-capture-1.png').exists()


def test_csi_configuration_rejects_unbounded_sensor_modes(tmp_path: Path) -> None:
    service = JetsonCsiCaptureService(tmp_path, pipeline_available=lambda: True)

    with pytest.raises(CsiCaptureError, match='sensor mode'):
        service.configure(CameraConfiguration(
            camera_id='top-camera', sensor_mode='3280x2464 ! fakesink',
            exposure_microseconds=8000, analog_gain=1,
        ))


def test_hardware_camera_http_contract_uses_injected_verified_csi_service(tmp_path: Path) -> None:
    def runner(argv: list[str], _: float) -> None:
        Path(argv[argv.index('filesink') + 1].removeprefix('location=')).write_bytes(create_test_pattern_png())

    service = JetsonCsiCaptureService(tmp_path, runner=runner, pipeline_available=lambda: True)
    client = TestClient(create_app(service))
    response = client.post('/captures', json=request().model_dump(mode='json', by_alias=True))
    image = client.get(response.json()['inspectionImageUrl'])

    assert client.get('/health').json()['status'] == 'ready'
    assert response.status_code == 201
    assert image.content == create_test_pattern_png()