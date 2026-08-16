from datetime import datetime

from fastapi.testclient import TestClient

from simulator.mcu.app import create_app


def test_motion_simulator_homes_and_executes_idempotent_absolute_move() -> None:
    client = TestClient(create_app())

    home = client.post('/commands/home', json={'commandId': 'home-1'})
    move_payload = {
        'commandId': 'move-1',
        'target': {'xMillimeters': 100, 'yMillimeters': 50, 'zMillimeters': 25},
        'maximumVelocityMillimetersPerSecond': 20,
        'maximumAccelerationMillimetersPerSecondSquared': 40,
        'settleMilliseconds': 0,
    }
    first_move = client.post('/commands/move-absolute', json=move_payload)
    repeated_move = client.post('/commands/move-absolute', json=move_payload)
    state = client.get('/state')

    assert home.status_code == 200
    assert first_move.status_code == 200
    assert repeated_move.json() == first_move.json()
    assert state.json()['isHomed'] is True
    assert state.json()['isInPosition'] is True
    assert state.json()['position'] == move_payload['target']


def test_motion_state_read_refreshes_observation_time_without_changing_revision() -> None:
    client = TestClient(create_app())
    client.post('/commands/home', json={'commandId': 'home-freshness'})
    first = client.get('/state').json()
    second = client.get('/state').json()

    assert second['revision'] == first['revision']
    assert datetime.fromisoformat(second['updatedAt']) >= datetime.fromisoformat(first['updatedAt'])


def test_motion_simulator_rejects_move_before_homing_and_outside_workspace() -> None:
    client = TestClient(create_app())
    payload = {
        'commandId': 'move-1',
        'target': {'xMillimeters': 301, 'yMillimeters': 0, 'zMillimeters': 0},
        'maximumVelocityMillimetersPerSecond': 20,
        'maximumAccelerationMillimetersPerSecondSquared': 40,
        'settleMilliseconds': 0,
    }

    assert client.post('/commands/move-absolute', json=payload).status_code == 409
    client.post('/commands/home', json={'commandId': 'home-1'})
    assert client.post('/commands/move-absolute', json=payload).status_code == 422


def test_motion_events_are_exposed_as_sse() -> None:
    client = TestClient(create_app())
    client.post('/commands/home', json={'commandId': 'home-1'})

    response = client.get('/events?afterRevision=0')

    assert response.headers['content-type'].startswith('text/event-stream')
    assert 'event: state' in response.text
    assert 'homing-complete' in response.text


def test_motion_console_can_jog_each_axis_after_homing() -> None:
    client = TestClient(create_app())
    client.post('/commands/home', json={'commandId': 'home-console'})

    response = client.post('/commands/jog', json={
        'commandId': 'jog-x-1',
        'axis': 'x',
        'distanceMillimeters': 10,
        'maximumVelocityMillimetersPerSecond': 5,
    })
    state = client.get('/state').json()

    assert response.status_code == 200
    assert state['position']['xMillimeters'] == 10
    assert state['position']['yMillimeters'] == 0
    assert state['isInPosition'] is True


def test_emergency_stop_latches_a_fault_and_blocks_motion_until_cleared() -> None:
    client = TestClient(create_app())
    client.post('/commands/home', json={'commandId': 'home-estop'})

    activated = client.put('/simulation/interlocks', json={
        'doorClosed': True,
        'emergencyStop': True,
        'communicationConnected': True,
    })
    blocked = client.post('/commands/move-absolute', json={
        'commandId': 'blocked-move',
        'target': {'xMillimeters': 1, 'yMillimeters': 1, 'zMillimeters': 1},
        'maximumVelocityMillimetersPerSecond': 20,
        'maximumAccelerationMillimetersPerSecondSquared': 40,
        'settleMilliseconds': 0,
    })
    clear_while_active = client.post('/commands/clear-fault', json={'commandId': 'clear-1'})
    client.put('/simulation/interlocks', json={
        'doorClosed': True,
        'emergencyStop': False,
        'communicationConnected': True,
    })
    cleared = client.post('/commands/clear-fault', json={'commandId': 'clear-2'})

    assert activated.json()['state'] == 'emergency-stop'
    assert blocked.status_code == 409
    assert clear_while_active.status_code == 409
    assert cleared.status_code == 200
    assert client.get('/state').json()['state'] == 'idle'


def test_door_interlock_and_injected_axis_fault_are_visible_in_state() -> None:
    client = TestClient(create_app())
    client.post('/commands/home', json={'commandId': 'home-fault'})
    door = client.put('/simulation/interlocks', json={
        'doorClosed': False,
        'emergencyStop': False,
        'communicationConnected': True,
    })
    client.put('/simulation/interlocks', json={
        'doorClosed': True,
        'emergencyStop': False,
        'communicationConnected': True,
    })
    fault = client.put('/simulation/fault', json={'fault': 'axis-stuck'})

    assert door.json()['state'] == 'fault'
    assert 'door' in door.json()['fault'].lower()
    assert fault.json()['state'] == 'fault'
    assert fault.json()['fault'] == 'axis-stuck'


def test_motion_console_can_reset_to_a_safe_not_homed_state() -> None:
    client = TestClient(create_app())
    client.post('/commands/home', json={'commandId': 'home-reset'})
    client.post('/commands/jog', json={
        'commandId': 'jog-reset',
        'axis': 'z',
        'distanceMillimeters': 12,
        'maximumVelocityMillimetersPerSecond': 5,
    })

    response = client.post('/simulation/reset')

    assert response.status_code == 200
    assert response.json()['state'] == 'not-homed'
    assert response.json()['isHomed'] is False
    assert response.json()['position'] == {
        'xMillimeters': 0.0,
        'yMillimeters': 0.0,
        'zMillimeters': 0.0,
    }


def test_common_motion_configuration_is_shared_by_all_clients() -> None:
    client = TestClient(create_app())

    updated = client.put('/configuration', json={
        'maximumVelocityMillimetersPerSecond': 35,
        'maximumAccelerationMillimetersPerSecondSquared': 70,
        'settleMilliseconds': 300,
    })
    current = client.get('/configuration')

    assert updated.status_code == 200
    assert current.json() == updated.json()
    assert current.json()['maximumVelocityMillimetersPerSecond'] == 35