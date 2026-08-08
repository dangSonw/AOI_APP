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