from pathlib import Path

import pytest

from app.schemas.workstation_preferences import WorkstationPreferencesSchema
from app.services.workstation_preference_repository import (
    InvalidWorkstationId,
    StalePreferenceRevision,
    WorkstationPreferenceRepository,
)


def test_missing_preferences_return_user_scoped_defaults(tmp_path: Path) -> None:
    preferences = WorkstationPreferenceRepository(tmp_path).read(user_id=7, workstation_id='station-01')

    assert preferences.user_id == 7
    assert preferences.workstation_id == 'station-01'
    assert preferences.revision == 0
    assert preferences.photometric.light_count == 4
    assert len(preferences.photometric.lights) == 4


def test_save_is_atomic_and_revision_safe(tmp_path: Path) -> None:
    repository = WorkstationPreferenceRepository(tmp_path)
    submitted = repository.read(7, 'station-01')

    saved = repository.save(7, 'station-01', submitted)

    assert saved.revision == 1
    payload = WorkstationPreferencesSchema.model_validate_json(
        (tmp_path / 'users' / '7' / 'station-01.json').read_text(encoding='utf-8')
    )
    assert payload.revision == 1
    assert not (tmp_path / 'users' / '7' / 'station-01.json.tmp').exists()
    with pytest.raises(StalePreferenceRevision):
        repository.save(7, 'station-01', submitted)


@pytest.mark.parametrize('workstation_id', ('../station', 'Station-01', 'station_01', ''))
def test_workstation_id_rejects_unsafe_values(tmp_path: Path, workstation_id: str) -> None:
    with pytest.raises(InvalidWorkstationId):
        WorkstationPreferenceRepository(tmp_path).read(1, workstation_id)


def test_photometric_schema_requires_one_image_configuration_per_light() -> None:
    payload = WorkstationPreferencesSchema.create_default(1, 'station-01').model_dump()
    payload['photometric']['light_count'] = 3

    with pytest.raises(ValueError, match='light count'):
        WorkstationPreferencesSchema.model_validate(payload)