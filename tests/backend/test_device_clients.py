import httpx
import pytest

from app.clients.camera_client import CameraClient
from app.clients.device_client import DeviceClient, DeviceServiceError
from app.clients.motion_client import MotionClient
from core.devices.camera import CaptureRequest
from core.devices.motion import HomeRequest, MoveAbsoluteRequest, Position


def test_device_client_accepts_a_compatible_ready_adapter() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={
        'service': 'camera', 'implementation': 'replay-camera', 'mode': 'simulation',
        'status': 'ready', 'protocolVersion': '1.0', 'checkedAt': '2026-08-06T00:00:00Z',
    }))

    health = DeviceClient('http://camera', transport=transport).health()

    assert health.service == 'camera'
    assert health.status == 'ready'


def test_device_client_rejects_an_incompatible_protocol() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={
        'service': 'motion', 'implementation': 'virtual-motion', 'mode': 'simulation',
        'status': 'ready', 'protocolVersion': '2.0', 'checkedAt': '2026-08-06T00:00:00Z',
    }))

    with pytest.raises(DeviceServiceError, match='protocol'):
        DeviceClient('http://motion', transport=transport).health()


def test_device_client_can_report_unavailable_health_but_rejects_readiness_check() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json={
        'service': 'camera', 'implementation': 'hardware-camera', 'mode': 'hardware',
        'status': 'unavailable', 'protocolVersion': '1.0', 'checkedAt': '2026-08-06T00:00:00Z',
        'detail': 'The CSI camera is not connected.',
    }))
    client = DeviceClient('http://camera', transport=transport)

    assert client.health().status == 'unavailable'
    with pytest.raises(DeviceServiceError, match='not ready'):
        client.require_ready()


def test_device_client_normalizes_connection_failures() -> None:
    def fail(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError('offline')

    with pytest.raises(DeviceServiceError, match='unavailable'):
        DeviceClient('http://camera', transport=httpx.MockTransport(fail)).health()


def test_device_client_releases_its_http_connection_pool() -> None:
    client = DeviceClient('http://camera', transport=httpx.MockTransport(lambda _: httpx.Response(200)))

    client.close()

    assert client.is_closed is True


def test_device_client_normalizes_timeouts_without_leaking_transport_details() -> None:
    def timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout('socket 10.0.0.5 timed out')

    with pytest.raises(DeviceServiceError, match='timed out') as raised:
        DeviceClient('http://camera', transport=httpx.MockTransport(timeout)).health()

    assert '10.0.0.5' not in str(raised.value)


def test_camera_client_validates_capture_artifact_integrity() -> None:
    image_bytes = b'camera-image'
    import hashlib

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == '/health':
            return httpx.Response(200, json={
                'service': 'camera', 'implementation': 'test-camera', 'mode': 'simulation',
                'status': 'ready', 'protocolVersion': '1.0', 'checkedAt': '2026-08-06T00:00:00Z',
            })
        if request.url.path == '/captures':
            return httpx.Response(201, json={
                'captureId': 'capture-1', 'requestId': 'capture-1', 'status': 'ready',
                'cameraId': 'top-camera', 'sensorModel': 'simulated-camera',
                'capturedAt': '2026-08-06T00:00:00Z', 'monotonicTimestampNanoseconds': 1,
                'width': 2, 'height': 2, 'pixelFormat': 'rgb8',
                'position': {'xMillimeters': 0, 'yMillimeters': 0, 'zMillimeters': 0},
                'exposureMicroseconds': 8000, 'analogGain': 1.0, 'mediaType': 'image/png',
                'byteLength': len(image_bytes), 'sha256': hashlib.sha256(image_bytes).hexdigest(),
                'inspectionImageUrl': '/captures/capture-1/inspection-image',
            })
        return httpx.Response(200, content=image_bytes, headers={'content-type': 'image/png'})

    client = CameraClient('http://camera', transport=httpx.MockTransport(handler))
    result = client.capture(CaptureRequest(
        request_id='capture-1', camera_id='top-camera', recipe_id='recipe-1',
        expected_position=Position(x_millimeters=0, y_millimeters=0, z_millimeters=0),
        sensor_mode='test', exposure_microseconds=8000, analog_gain=1,
    ))

    assert result.capture_id == 'capture-1'
    assert client.inspection_image('capture-1').content == image_bytes


def test_camera_client_rejects_checksum_mismatch_and_external_artifact_urls() -> None:
    def checksum_mismatch(request: httpx.Request) -> httpx.Response:
        if request.url.path == '/health':
            return httpx.Response(200, json={
                'service': 'camera', 'implementation': 'test-camera', 'mode': 'simulation',
                'status': 'ready', 'protocolVersion': '1.0', 'checkedAt': '2026-08-06T00:00:00Z',
            })
        if request.url.path == '/captures':
            return httpx.Response(201, json={
                'captureId': 'capture-2', 'requestId': 'capture-2', 'status': 'ready',
                'cameraId': 'top-camera', 'sensorModel': 'simulated-camera',
                'capturedAt': '2026-08-06T00:00:00Z', 'monotonicTimestampNanoseconds': 1,
                'width': 2, 'height': 2, 'pixelFormat': 'rgb8',
                'position': {'xMillimeters': 0, 'yMillimeters': 0, 'zMillimeters': 0},
                'exposureMicroseconds': 8000, 'analogGain': 1.0, 'mediaType': 'image/png',
                'byteLength': 3, 'sha256': '0' * 64,
                'inspectionImageUrl': '/captures/capture-2/inspection-image',
            })
        return httpx.Response(200, content=b'bad', headers={'content-type': 'image/png'})

    client = CameraClient('http://camera', transport=httpx.MockTransport(checksum_mismatch))
    request = CaptureRequest(
        request_id='capture-2', camera_id='top-camera', recipe_id='recipe-1',
        expected_position=Position(x_millimeters=0, y_millimeters=0, z_millimeters=0),
        sensor_mode='test', exposure_microseconds=8000, analog_gain=1,
    )

    with pytest.raises(DeviceServiceError, match='checksum'):
        client.capture(request)


def test_motion_client_reads_state_and_sends_versioned_commands() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == '/health':
            return httpx.Response(200, json={
                'service': 'motion', 'implementation': 'test-motion', 'mode': 'simulation',
                'status': 'ready', 'protocolVersion': '1.0', 'checkedAt': '2026-08-06T00:00:00Z',
            })
        if request.url.path == '/state':
            return httpx.Response(200, json={
                'revision': 2, 'state': 'idle', 'isHomed': True, 'isInPosition': True,
                'position': {'xMillimeters': 10, 'yMillimeters': 20, 'zMillimeters': 30},
                'emergencyStop': False, 'doorClosed': True, 'communicationConnected': True,
                'updatedAt': '2026-08-06T00:00:00Z',
            })
        return httpx.Response(200, json={
            'commandId': request.url.path.rsplit('/', 1)[-1], 'status': 'completed', 'stateRevision': 3,
        })

    client = MotionClient('http://motion', transport=httpx.MockTransport(handler))
    state = client.state()
    client.home(HomeRequest(command_id='home-1'))
    client.move_absolute(MoveAbsoluteRequest(
        command_id='move-1', target=Position(x_millimeters=1, y_millimeters=2, z_millimeters=3),
        maximum_velocity_millimeters_per_second=20,
        maximum_acceleration_millimeters_per_second_squared=40,
        settle_milliseconds=100,
    ))
    client.stop(HomeRequest(command_id='stop-1'))
    client.clear_fault(HomeRequest(command_id='clear-1'))

    assert state.position.y_millimeters == 20
    assert [request.url.path for request in requests] == [
        '/health', '/state',
        '/health', '/commands/home',
        '/health', '/commands/move-absolute',
        '/health', '/commands/stop',
        '/health', '/commands/clear-fault',
    ]