from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from core.devices.camera import CameraCapabilities, CameraConfiguration, CaptureRequest
from core.devices.models import DeviceMode, DeviceStatus, HealthResponse
from core.devices.motion import MotionCapabilities, MotionConfiguration, Position, MoveAbsoluteRequest


def test_health_response_serializes_the_shared_protocol_contract() -> None:
    response = HealthResponse(
        service='camera',
        implementation='replay-camera',
        mode=DeviceMode.SIMULATION,
        status=DeviceStatus.READY,
        protocol_version='1.0',
        checked_at=datetime(2026, 8, 6, tzinfo=timezone.utc),
    )

    payload = response.model_dump(mode='json', by_alias=True)

    assert payload['protocolVersion'] == '1.0'
    assert payload['mode'] == 'simulation'
    assert payload['status'] == 'ready'


def test_camera_contract_requires_a_bounded_positive_capture_configuration() -> None:
    capabilities = CameraCapabilities(
        camera_ids=('top-camera',),
        sensor_models=('imx219',),
        maximum_width=3280,
        maximum_height=2464,
        supports_raw=False,
        inspection_media_types=('image/png',),
    )

    request = CaptureRequest(
        request_id='capture-0001',
        camera_id='top-camera',
        recipe_id='rev-c-mainboard',
        expected_position=Position(x_millimeters=10, y_millimeters=20, z_millimeters=30),
        sensor_mode='3280x2464',
        exposure_microseconds=8000,
        analog_gain=1.0,
    )

    assert capabilities.maximum_width == 3280
    assert request.expected_position.z_millimeters == 30

    with pytest.raises(ValidationError):
        CaptureRequest(
            request_id='capture-0002',
            camera_id='top-camera',
            recipe_id='rev-c-mainboard',
            expected_position=Position(x_millimeters=0, y_millimeters=0, z_millimeters=0),
            sensor_mode='3280x2464',
            exposure_microseconds=0,
            analog_gain=1.0,
        )


def test_common_device_configuration_is_bounded_and_serializes_in_camel_case() -> None:
    camera = CameraConfiguration(
        camera_id='top-camera', sensor_mode='3280x2464',
        exposure_microseconds=8000, analog_gain=1.5,
    )
    motion = MotionConfiguration(
        maximum_velocity_millimeters_per_second=20,
        maximum_acceleration_millimeters_per_second_squared=40,
        settle_milliseconds=250,
    )

    assert camera.model_dump(by_alias=True)['exposureMicroseconds'] == 8000
    assert motion.model_dump(by_alias=True)['settleMilliseconds'] == 250

    with pytest.raises(ValidationError):
        CameraConfiguration(
            camera_id='top-camera', sensor_mode='3280x2464',
            exposure_microseconds=0, analog_gain=1,
        )


def test_motion_contract_rejects_unbounded_or_non_positive_commands() -> None:
    capabilities = MotionCapabilities(
        axes=('x', 'y', 'z'),
        minimum_position=Position(x_millimeters=0, y_millimeters=0, z_millimeters=0),
        maximum_position=Position(x_millimeters=300, y_millimeters=200, z_millimeters=150),
        supports_homing=True,
        supports_sse=True,
    )
    request = MoveAbsoluteRequest(
        command_id='move-0001',
        target=Position(x_millimeters=100, y_millimeters=50, z_millimeters=25),
        maximum_velocity_millimeters_per_second=20,
        maximum_acceleration_millimeters_per_second_squared=40,
        settle_milliseconds=250,
    )

    assert capabilities.axes == ('x', 'y', 'z')
    assert request.settle_milliseconds == 250

    with pytest.raises(ValidationError):
        MoveAbsoluteRequest(
            command_id='move-0002',
            target=Position(x_millimeters=0, y_millimeters=0, z_millimeters=0),
            maximum_velocity_millimeters_per_second=-1,
            maximum_acceleration_millimeters_per_second_squared=40,
            settle_milliseconds=0,
        )