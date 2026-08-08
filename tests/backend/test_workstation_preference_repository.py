from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.database.session import SessionLocal
from app.models.settings_document import SettingsDocument
from app.models.user import User
from app.schemas.workstation_preferences import WorkstationPreferencesSchema
from app.services.workstation_preference_repository import (
    InvalidWorkstationId,
    StalePreferenceRevision,
    WorkstationPreferenceRepository,
)


def test_missing_preferences_return_user_scoped_defaults() -> None:
    with SessionLocal() as session:
        user_id = session.scalar(select(User.id).limit(1))
        assert user_id is not None
        preferences = WorkstationPreferenceRepository(session).read(user_id=user_id, workstation_id='station-01')

    assert preferences.user_id == user_id
    assert preferences.workstation_id == 'station-01'
    assert preferences.revision == 0
    assert preferences.locale.language == 'en-US'
    assert preferences.locale.measurement_system == 'metric'
    assert preferences.photometric.light_count == 4
    assert len(preferences.photometric.lights) == 4


def test_save_is_database_backed_and_revision_safe() -> None:
    with SessionLocal() as session:
        user_id = session.scalar(select(User.id).limit(1))
        assert user_id is not None
        station = f'repository-{uuid4().hex}'
        repository = WorkstationPreferenceRepository(session)
        submitted = repository.read(user_id, station)

        saved = repository.save(user_id, station, submitted, actor_id=user_id, request_id=f'save-{station}')
        session.commit()

        assert saved.revision == 1
        assert repository.read(user_id, station).revision == 1
        with pytest.raises(StalePreferenceRevision):
            repository.save(user_id, station, submitted, actor_id=user_id, request_id=f'stale-{station}')
        session.rollback()
        document = session.scalar(select(SettingsDocument).where(SettingsDocument.subject_id == station))
        assert document is not None
        session.execute(delete(SettingsDocument).where(SettingsDocument.id == document.id))
        session.commit()


@pytest.mark.parametrize('workstation_id', ('../station', 'Station-01', 'station_01', ''))
def test_workstation_id_rejects_unsafe_values(workstation_id: str) -> None:
    with SessionLocal() as session, pytest.raises(InvalidWorkstationId):
        WorkstationPreferenceRepository(session).read(1, workstation_id)


def test_photometric_schema_requires_one_image_configuration_per_light() -> None:
    payload = WorkstationPreferencesSchema.create_default(1, 'station-01').model_dump()
    payload['photometric']['light_count'] = 3

    with pytest.raises(ValueError, match='light count'):
        WorkstationPreferencesSchema.model_validate(payload)