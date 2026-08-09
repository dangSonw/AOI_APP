import json

import pytest

from app.services.pilot_acceptance import PilotAcceptanceError, verify_pilot_acceptance


def report() -> dict:
    return {
        'schemaVersion': 1,
        'stationId': 'station-pilot',
        'targetHardware': 'Jetson + production PCB fixture',
        'measurements': {
            'cycleTimeP95Ms': 850,
            'falseCallRatePercent': 1.2,
            'escapeRatePercent': 0.1,
            'uptimePercent': 99.5,
            'recoveryTimeSeconds': 30,
            'inspectedBoardCount': 1000,
        },
        'hardwareInterlocksAuthoritative': True,
        'calibrationLineageVerified': True,
        'integrationOutagePolicyVerified': True,
        'backupRestoreDryRunVerified': True,
        'status': 'passed',
    }


def test_pilot_acceptance_requires_measured_target_hardware_gates(tmp_path) -> None:
    path = tmp_path / 'pilot.json'
    path.write_text(json.dumps(report()), encoding='utf-8')
    assert verify_pilot_acceptance(path).measurements.inspected_board_count == 1000

    failed = report()
    failed['backupRestoreDryRunVerified'] = False
    path.write_text(json.dumps(failed), encoding='utf-8')
    with pytest.raises(PilotAcceptanceError, match='incomplete'):
        verify_pilot_acceptance(path)


def test_pilot_acceptance_rejects_fake_pass_without_measurements(tmp_path) -> None:
    path = tmp_path / 'fake.json'
    path.write_text('{"status":"passed"}', encoding='utf-8')
    with pytest.raises(PilotAcceptanceError, match='invalid'):
        verify_pilot_acceptance(path)