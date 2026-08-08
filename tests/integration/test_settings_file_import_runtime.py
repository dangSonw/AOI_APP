import json
from uuid import uuid4

from sqlalchemy import delete, select

from app.database.session import SessionLocal
from app.models.settings_document import SettingsDocument
from app.models.user import User
from app.schemas.workstation_preferences import WorkstationPreferencesSchema


def test_file_migration_dry_run_apply_and_rerun(tmp_path) -> None:
    from app.services.settings_file_migration import migrate_preference_files

    with SessionLocal() as session:
        user_id = session.scalar(select(User.id).limit(1))
        assert user_id is not None
        station = f'migration-{uuid4().hex}'
        source = tmp_path / 'users' / str(user_id) / f'{station}.json'
        source.parent.mkdir(parents=True)
        source.write_text(json.dumps(
            WorkstationPreferencesSchema.create_default(user_id, station).model_dump(mode='json', by_alias=True)
        ), encoding='utf-8')

        dry_run = migrate_preference_files(session, tmp_path, actor_id=user_id, apply=False)
        assert dry_run.imported == 1
        assert session.scalar(select(SettingsDocument).where(SettingsDocument.subject_id == station)) is None

        applied = migrate_preference_files(session, tmp_path, actor_id=user_id, apply=True)
        session.commit()
        rerun = migrate_preference_files(session, tmp_path, actor_id=user_id, apply=True)
        session.commit()

        assert applied.imported == 1
        assert rerun.unchanged == 1
        document = session.scalar(select(SettingsDocument).where(SettingsDocument.subject_id == station))
        assert document is not None and document.owner_user_id == user_id and document.current_revision == 1
        session.execute(delete(SettingsDocument).where(SettingsDocument.id == document.id))
        session.commit()