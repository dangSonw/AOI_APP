import pytest


def test_workstation_registry_normalizes_content_without_storage_metadata() -> None:
    from app.schemas.workstation_preferences import WorkstationPreferenceContentSchema
    from app.services.settings_schema_registry import validate_settings_payload

    payload = WorkstationPreferenceContentSchema.create_default().model_dump(mode='json', by_alias=True)
    validated = validate_settings_payload('workstation-preferences', 1, payload)

    assert validated['locale']['measurementSystem'] == 'metric'
    assert validated['photometric']['lightCount'] == 4
    assert 'revision' not in validated
    assert 'userId' not in validated


def test_unknown_settings_schema_is_rejected() -> None:
    from app.services.settings_schema_registry import UnknownSettingsSchema, validate_settings_payload

    with pytest.raises(UnknownSettingsSchema, match='not supported'):
        validate_settings_payload('adapter-command', 1, {})


def test_compatibility_envelope_uses_content_defaults() -> None:
    from app.schemas.workstation_preferences import WorkstationPreferencesSchema

    preferences = WorkstationPreferencesSchema.create_default(7, 'station-01')

    assert preferences.user_id == 7
    assert preferences.revision == 0
    assert preferences.photometric.light_count == 4


@pytest.mark.parametrize(('document_key', 'expected_field'), [
    ('workstation-profile', 'deploymentMode'),
    ('recipe-defaults', 'decisionPolicy'),
    ('system-policy', 'retention'),
])
def test_settings_registry_supports_workspace_documents(document_key: str, expected_field: str) -> None:
    from app.schemas.settings_documents import default_settings_payload
    from app.services.settings_schema_registry import validate_settings_payload

    payload = default_settings_payload(document_key)
    validated = validate_settings_payload(document_key, 1, payload)

    assert expected_field in validated


def test_workstation_profile_rejects_unsafe_or_invalid_operational_values() -> None:
    from pydantic import ValidationError

    from app.schemas.settings_documents import WorkstationProfileSchema

    with pytest.raises(ValidationError):
        WorkstationProfileSchema.model_validate({
            'stationDisplayName': 'AOI pilot',
            'deploymentMode': 'production',
            'camera': {
                'cameraId': 'top-camera', 'sensorMode': '3280x2464',
                'exposureMicroseconds': 0, 'analogGain': 1,
            },
            'motion': {
                'maximumVelocityMillimetersPerSecond': 20,
                'maximumAccelerationMillimetersPerSecondSquared': 40,
                'settleMilliseconds': 250,
            },
        })


def test_system_policy_never_accepts_plaintext_integration_secrets() -> None:
    from pydantic import ValidationError

    from app.schemas.settings_documents import SystemPolicySchema

    with pytest.raises(ValidationError):
        SystemPolicySchema.model_validate({
            'integrations': {'mesEnabled': True, 'mesEndpoint': 'https://mes.example', 'password': 'secret'},
        })