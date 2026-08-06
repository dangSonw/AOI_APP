from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hardware.camera.app import create_app as create_hardware_camera_app
from hardware.mcu.app import create_app as create_hardware_motion_app
from simulator.camera.app import create_app as create_simulator_camera_app
from simulator.mcu.app import create_app as create_simulator_motion_app


AdapterFactory = Callable[[], FastAPI]


@pytest.mark.parametrize(
    ('factory', 'service', 'mode'),
    (
        (create_hardware_camera_app, 'camera', 'hardware'),
        (create_hardware_motion_app, 'motion', 'hardware'),
        (create_simulator_camera_app, 'camera', 'simulation'),
        (create_simulator_motion_app, 'motion', 'simulation'),
    ),
)
def test_adapters_expose_the_same_versioned_service_contract(
    factory: AdapterFactory,
    service: str,
    mode: str,
) -> None:
    client = TestClient(factory())

    health_response = client.get('/health')
    version_response = client.get('/version')
    capabilities_response = client.get('/capabilities')

    assert health_response.status_code == 200
    assert version_response.status_code == 200
    assert capabilities_response.status_code == 200
    assert health_response.json()['service'] == service
    assert health_response.json()['mode'] == mode
    assert health_response.json()['protocolVersion'] == '1.0'
    assert version_response.json() == {'protocolVersion': '1.0'}


@pytest.mark.parametrize(
    'factory',
    (create_hardware_camera_app, create_hardware_motion_app),
)
def test_hardware_adapters_report_unavailable_without_opening_devices(factory: AdapterFactory) -> None:
    response = TestClient(factory()).get('/health')

    assert response.json()['status'] == 'unavailable'
    assert response.json()['detail']


@pytest.mark.parametrize(
    'factory',
    (create_simulator_camera_app, create_simulator_motion_app),
)
def test_simulator_adapters_are_ready_without_hardware(factory: AdapterFactory) -> None:
    response = TestClient(factory()).get('/health')

    assert response.json()['status'] == 'ready'


@pytest.mark.parametrize(
    'factory',
    (create_hardware_camera_app, create_hardware_motion_app, create_simulator_camera_app, create_simulator_motion_app),
)
def test_all_adapters_expose_a_common_configuration_resource(factory: AdapterFactory) -> None:
    response = TestClient(factory()).get('/configuration')

    assert response.status_code == 200


@pytest.mark.parametrize(
    ('factory', 'payload'),
    (
        (create_hardware_camera_app, {'cameraId': 'top-camera', 'sensorMode': '3280x2464', 'exposureMicroseconds': 9000, 'analogGain': 2}),
        (create_simulator_camera_app, {'cameraId': 'top-camera', 'sensorMode': '3280x2464', 'exposureMicroseconds': 9000, 'analogGain': 2}),
        (create_hardware_motion_app, {'maximumVelocityMillimetersPerSecond': 30, 'maximumAccelerationMillimetersPerSecondSquared': 60, 'settleMilliseconds': 300}),
        (create_simulator_motion_app, {'maximumVelocityMillimetersPerSecond': 30, 'maximumAccelerationMillimetersPerSecondSquared': 60, 'settleMilliseconds': 300}),
    ),
)
def test_all_adapters_accept_the_same_writable_configuration_contract(
    factory: AdapterFactory,
    payload: dict[str, object],
) -> None:
    client = TestClient(factory())

    response = client.put('/configuration', json=payload)

    assert response.status_code == 200
    assert response.json() == payload