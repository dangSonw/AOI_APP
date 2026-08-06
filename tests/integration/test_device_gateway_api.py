from types import SimpleNamespace

import hashlib
import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.devices import get_camera_client, get_motion_client
from app.auth.dependencies import get_current_user
from app.clients.camera_client import CameraClient
from app.clients.motion_client import MotionClient
from app.main import app


IMAGE_BYTES = b'gateway-camera-image'


def adapter_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == '/health':
        service = 'camera' if request.url.host == 'camera' else 'motion'
        return httpx.Response(200, json={
            'service': service, 'implementation': f'test-{service}', 'mode': 'simulation',
            'status': 'ready', 'protocolVersion': '1.0', 'checkedAt': '2026-08-06T00:00:00Z',
        })
    if path == '/capabilities' and request.url.host == 'camera':
        return httpx.Response(200, json={
            'cameraIds': ['top-camera'], 'sensorModels': ['simulated-camera'],
            'maximumWidth': 3280, 'maximumHeight': 2464, 'supportsRaw': False,
            'inspectionMediaTypes': ['image/png'],
        })
    if path == '/configuration' and request.url.host == 'camera':
        return httpx.Response(200, json={
            'cameraId': 'top-camera', 'sensorMode': '3280x2464',
            'exposureMicroseconds': 8000, 'analogGain': 1,
        })
    if path == '/configuration':
        return httpx.Response(200, json={
            'maximumVelocityMillimetersPerSecond': 20,
            'maximumAccelerationMillimetersPerSecondSquared': 40,
            'settleMilliseconds': 250,
        })
    if path == '/preview':
        return httpx.Response(200, content=IMAGE_BYTES, headers={'content-type': 'image/png'})
    if path == '/capabilities':
        return httpx.Response(200, json={
            'axes': ['x', 'y', 'z'],
            'minimumPosition': {'xMillimeters': 0, 'yMillimeters': 0, 'zMillimeters': 0},
            'maximumPosition': {'xMillimeters': 300, 'yMillimeters': 200, 'zMillimeters': 150},
            'supportsHoming': True, 'supportsSse': True,
        })
    if path == '/state':
        return httpx.Response(200, json={
            'revision': 0, 'state': 'not-homed', 'isHomed': False, 'isInPosition': False,
            'position': {'xMillimeters': 0, 'yMillimeters': 0, 'zMillimeters': 0},
            'emergencyStop': False, 'doorClosed': True, 'communicationConnected': True,
            'updatedAt': '2026-08-06T00:00:00Z',
        })
    if path == '/captures':
        return httpx.Response(201, json={
            'captureId': 'capture-gateway', 'requestId': 'capture-gateway', 'status': 'ready',
            'cameraId': 'top-camera', 'sensorModel': 'simulated-camera',
            'capturedAt': '2026-08-06T00:00:00Z', 'monotonicTimestampNanoseconds': 1,
            'width': 2, 'height': 2, 'pixelFormat': 'rgb8',
            'position': {'xMillimeters': 0, 'yMillimeters': 0, 'zMillimeters': 0},
            'exposureMicroseconds': 8000, 'analogGain': 1, 'mediaType': 'image/png',
            'byteLength': len(IMAGE_BYTES), 'sha256': hashlib.sha256(IMAGE_BYTES).hexdigest(),
            'inspectionImageUrl': '/captures/capture-gateway/inspection-image',
        })
    if path == '/captures/capture-gateway/inspection-image':
        return httpx.Response(200, content=IMAGE_BYTES, headers={'content-type': 'image/png'})
    if path.startswith('/commands/'):
        return httpx.Response(200, json={
            'commandId': 'gateway-command', 'status': 'completed', 'stateRevision': 1,
        })
    return httpx.Response(404)


@pytest.fixture
def client():
    transport = httpx.MockTransport(adapter_handler)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, is_active=True)
    app.dependency_overrides[get_camera_client] = lambda: CameraClient('http://camera', transport=transport)
    app.dependency_overrides[get_motion_client] = lambda: MotionClient('http://motion', transport=transport)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_device_gateway_requires_authentication() -> None:
    with TestClient(app) as anonymous:
        assert anonymous.get('/api/camera/health').status_code == 401
        assert anonymous.get('/api/motion/state').status_code == 401


def test_device_gateway_reads_camera_and_motion_signals(client: TestClient) -> None:
    devices = client.get('/api/devices')
    camera = client.get('/api/camera/capabilities')
    motion = client.get('/api/motion/state')

    assert devices.status_code == 200
    assert devices.json()['camera']['status'] == 'ready'
    assert devices.json()['motion']['status'] == 'ready'
    assert camera.json()['cameraIds'] == ['top-camera']
    assert motion.json()['state'] == 'not-homed'


def test_device_gateway_captures_and_proxies_verified_inspection_image(client: TestClient) -> None:
    capture = client.post('/api/camera/captures', json={
        'requestId': 'capture-gateway', 'cameraId': 'top-camera', 'recipeId': 'recipe-1',
        'expectedPosition': {'xMillimeters': 0, 'yMillimeters': 0, 'zMillimeters': 0},
        'sensorMode': 'test', 'exposureMicroseconds': 8000, 'analogGain': 1,
    })
    image = client.get('/api/camera/captures/capture-gateway/inspection-image')

    assert capture.status_code == 201
    assert capture.json()['sha256'] == hashlib.sha256(IMAGE_BYTES).hexdigest()
    assert image.status_code == 200
    assert image.content == IMAGE_BYTES
    assert image.headers['content-type'] == 'image/png'


def test_device_gateway_sends_motion_commands(client: TestClient) -> None:
    home = client.post('/api/motion/commands/home', json={'commandId': 'home-1'})
    move = client.post('/api/motion/commands/move-absolute', json={
        'commandId': 'move-1',
        'target': {'xMillimeters': 10, 'yMillimeters': 20, 'zMillimeters': 30},
        'maximumVelocityMillimetersPerSecond': 20,
        'maximumAccelerationMillimetersPerSecondSquared': 40,
        'settleMilliseconds': 100,
    })
    stop = client.post('/api/motion/commands/stop', json={'commandId': 'stop-1'})

    assert home.status_code == 200
    assert move.status_code == 200
    assert stop.status_code == 200


def test_device_gateway_reads_and_updates_shared_hardware_configuration(client: TestClient) -> None:
    camera = client.put('/api/camera/configuration', json={
        'cameraId': 'top-camera', 'sensorMode': '3280x2464',
        'exposureMicroseconds': 12000, 'analogGain': 2,
    })
    motion = client.put('/api/motion/configuration', json={
        'maximumVelocityMillimetersPerSecond': 35,
        'maximumAccelerationMillimetersPerSecondSquared': 70,
        'settleMilliseconds': 300,
    })
    preview = client.get('/api/camera/preview')

    assert camera.status_code == 200
    assert motion.status_code == 200
    assert preview.content == IMAGE_BYTES
    assert preview.headers['cache-control'] == 'no-store'