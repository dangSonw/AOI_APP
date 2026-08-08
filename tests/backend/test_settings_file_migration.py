import json

import pytest


def test_discovery_is_sorted_and_rejects_unsafe_layout(tmp_path) -> None:
    from app.services.settings_file_migration import discover_preference_files

    for relative in ('users/2/station-b.json', 'users/1/station-a.json'):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{}', encoding='utf-8')
    unsafe = tmp_path / 'users' / '1' / 'Station_A.json'
    unsafe.write_text('{}', encoding='utf-8')

    candidates = discover_preference_files(tmp_path)

    assert [(item.user_id, item.workstation_id) for item in candidates] == [(1, 'station-a'), (2, 'station-b')]


def test_discovery_reports_embedded_identity_mismatch(tmp_path) -> None:
    from app.schemas.workstation_preferences import WorkstationPreferencesSchema
    from app.services.settings_file_migration import InvalidPreferenceMigration, load_preference_candidate

    path = tmp_path / 'users' / '1' / 'station-01.json'
    path.parent.mkdir(parents=True)
    payload = WorkstationPreferencesSchema.create_default(2, 'station-01').model_dump(mode='json', by_alias=True)
    path.write_text(json.dumps(payload), encoding='utf-8')

    with pytest.raises(InvalidPreferenceMigration, match='identity'):
        load_preference_candidate(path, tmp_path, user_id=1, workstation_id='station-01')