import hashlib
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from simulator.camera.app import create_app
from simulator.camera.capture_service import ReplayCaptureService, create_test_pattern_png


def test_replay_camera_creates_one_checksum_verified_lossless_artifact(tmp_path: Path) -> None:
    client = TestClient(create_app(capture_directory=tmp_path))
    payload = {
        'requestId': 'capture-1',
        'cameraId': 'top-camera',
        'recipeId': 'rev-c-mainboard',
        'expectedPosition': {'xMillimeters': 10, 'yMillimeters': 20, 'zMillimeters': 30},
        'sensorMode': '3280x2464',
        'exposureMicroseconds': 8000,
        'analogGain': 1.0,
    }

    first = client.post('/captures', json=payload)
    repeated = client.post('/captures', json=payload)
    image = client.get(first.json()['inspectionImageUrl'])

    assert first.status_code == 201
    assert repeated.json() == first.json()
    assert image.headers['content-type'] == 'image/png'
    assert hashlib.sha256(image.content).hexdigest() == first.json()['sha256']
    assert len(list(tmp_path.glob('*.png'))) == 1


def test_camera_console_can_upload_select_and_preview_a_lossless_source(tmp_path: Path) -> None:
    client = TestClient(create_app(capture_directory=tmp_path))
    image_bytes = create_test_pattern_png()

    upload = client.put(
        '/simulation/images/board-good',
        params={'filename': 'board-good.png'},
        content=image_bytes,
        headers={'content-type': 'image/png'},
    )
    configuration = client.put('/simulation/configuration', json={
        'sourceMode': 'uploaded',
        'selectedImageId': 'board-good',
        'frameDelayMilliseconds': 0,
        'fault': 'none',
    })
    preview = client.get('/simulation/preview')
    sources = client.get('/simulation/images')

    assert upload.status_code == 201
    assert upload.json()['filename'] == 'board-good.png'
    assert configuration.status_code == 200
    assert preview.content == image_bytes
    assert sources.json()[0]['imageId'] == 'board-good'


def test_camera_capture_uses_the_selected_uploaded_image(tmp_path: Path) -> None:
    client = TestClient(create_app(capture_directory=tmp_path))
    image_bytes = create_test_pattern_png()
    client.put(
        '/simulation/images/webcam-live',
        params={'filename': 'webcam-frame.png'},
        content=image_bytes,
        headers={'content-type': 'image/png'},
    )
    client.put('/simulation/configuration', json={
        'sourceMode': 'uploaded',
        'selectedImageId': 'webcam-live',
        'frameDelayMilliseconds': 0,
        'fault': 'none',
    })

    response = client.post('/captures', json={
        'requestId': 'webcam-capture-1',
        'cameraId': 'top-camera',
        'recipeId': 'rev-c-mainboard',
        'expectedPosition': {'xMillimeters': 0, 'yMillimeters': 0, 'zMillimeters': 0},
        'sensorMode': 'uploaded',
        'exposureMicroseconds': 8000,
        'analogGain': 1.0,
    })

    assert response.status_code == 201
    assert response.json()['sha256'] == hashlib.sha256(image_bytes).hexdigest()
    assert response.json()['width'] == 2
    assert response.json()['height'] == 2


def test_camera_fault_injection_returns_a_service_error_without_an_artifact(tmp_path: Path) -> None:
    client = TestClient(create_app(capture_directory=tmp_path))
    client.put('/simulation/configuration', json={
        'sourceMode': 'test-pattern',
        'selectedImageId': None,
        'frameDelayMilliseconds': 0,
        'fault': 'failed-frame',
    })

    response = client.post('/captures', json={
        'requestId': 'failed-capture-1',
        'cameraId': 'top-camera',
        'recipeId': 'rev-c-mainboard',
        'expectedPosition': {'xMillimeters': 0, 'yMillimeters': 0, 'zMillimeters': 0},
        'sensorMode': '3280x2464',
        'exposureMicroseconds': 8000,
        'analogGain': 1.0,
    })

    assert response.status_code == 503
    assert not list(tmp_path.glob('*'))


def test_camera_rejects_unsupported_or_oversized_uploads(tmp_path: Path) -> None:
    client = TestClient(create_app(capture_directory=tmp_path))

    unsupported = client.put(
        '/simulation/images/readme',
        params={'filename': 'readme.txt'},
        content=b'not an image',
        headers={'content-type': 'text/plain'},
    )
    oversized = client.put(
        '/simulation/images/too-large',
        params={'filename': 'large.png'},
        content=b'x' * (16 * 1024 * 1024 + 1),
        headers={'content-type': 'image/png'},
    )

    assert unsupported.status_code == 415
    assert oversized.status_code == 413


def test_camera_service_rejects_path_traversal_identifiers(tmp_path: Path) -> None:
    service = ReplayCaptureService(tmp_path)

    with pytest.raises(ValueError, match='image ID'):
        service.upload_source('../escape', 'source.png', 'image/png', create_test_pattern_png())

    client = TestClient(create_app(capture_directory=tmp_path))
    response = client.post('/captures', json={
        'requestId': '../escape',
        'cameraId': 'top-camera',
        'recipeId': 'rev-c-mainboard',
        'expectedPosition': {'xMillimeters': 0, 'yMillimeters': 0, 'zMillimeters': 0},
        'sensorMode': '3280x2464',
        'exposureMicroseconds': 8000,
        'analogGain': 1.0,
    })

    assert response.status_code == 422
    assert not (tmp_path.parent / 'escape.png').exists()


def test_common_camera_configuration_and_preview_reflect_simulator_state(tmp_path: Path) -> None:
    client = TestClient(create_app(capture_directory=tmp_path))

    updated = client.put('/configuration', json={
        'cameraId': 'top-camera',
        'sensorMode': '3280x2464',
        'exposureMicroseconds': 12000,
        'analogGain': 2.5,
    })
    current = client.get('/configuration')
    preview = client.get('/preview')

    assert updated.status_code == 200
    assert current.json()['exposureMicroseconds'] == 12000
    assert current.json()['analogGain'] == 2.5
    assert preview.status_code == 200
    assert preview.headers['content-type'] == 'image/png'
    assert preview.headers['cache-control'] == 'no-store'