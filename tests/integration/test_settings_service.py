from uuid import uuid4

import pytest
from sqlalchemy import delete, select

from app.config.settings import get_settings
from app.database.session import SessionLocal
from app.models.settings_document import SettingsDocument
from app.models.settings_version import SettingsVersion
from app.models.user import User
from app.schemas.workstation_preferences import WorkstationPreferenceContentSchema


def identity_for(user_id: int):
    from app.services.settings_service import SettingsIdentity

    return SettingsIdentity('workstation', f'test-{uuid4().hex}', 'workstation-preferences', user_id)


def payload(language: str = 'en-US') -> dict:
    content = WorkstationPreferenceContentSchema.create_default()
    return content.model_copy(update={
        'locale': content.locale.model_copy(update={'language': language}),
    }).model_dump(mode='json', by_alias=True)


def test_versions_are_immutable_and_stale_revision_is_rejected() -> None:
    from app.services.settings_service import SettingsRevisionConflict, create_settings_version

    with SessionLocal() as session:
        user_id = session.scalar(select(User.id).limit(1))
        assert user_id is not None
        identity = identity_for(user_id)
        first = create_settings_version(session, identity, 0, 1, payload(), user_id, 'Initial')
        session.commit()
        first_checksum = first.checksum
        second = create_settings_version(session, identity, 1, 1, payload('en-GB'), user_id, 'Language')
        session.commit()

        assert (first.revision, second.revision) == (1, 2)
        assert session.get(SettingsVersion, first.id).checksum == first_checksum
        with pytest.raises(SettingsRevisionConflict) as conflict:
            create_settings_version(session, identity, 1, 1, payload(), user_id, 'Stale')
        assert conflict.value.current_revision == 2
        session.rollback()
        session.execute(delete(SettingsDocument).where(SettingsDocument.id == second.document_id))
        session.commit()


def test_rollback_creates_source_linked_new_version() -> None:
    from app.services.settings_service import create_settings_version, rollback_settings

    with SessionLocal() as session:
        user_id = session.scalar(select(User.id).limit(1))
        assert user_id is not None
        identity = identity_for(user_id)
        first = create_settings_version(session, identity, 0, 1, payload(), user_id, 'Initial')
        session.commit()
        second = create_settings_version(session, identity, 1, 1, payload('en-GB'), user_id, 'Language')
        session.commit()
        rolled_back = rollback_settings(session, identity, 2, 1, user_id, 'Restore')
        session.commit()

        assert rolled_back.revision == 3
        assert rolled_back.source_version_id == first.id
        assert rolled_back.payload == first.payload
        session.execute(delete(SettingsDocument).where(SettingsDocument.id == second.document_id))
        session.commit()