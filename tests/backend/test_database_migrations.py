from pathlib import Path

from alembic.script import ScriptDirectory


def test_alembic_config_uses_repository_migration_directory() -> None:
    from app.database.migrations import build_alembic_config

    config = build_alembic_config('postgresql+psycopg://user:password@127.0.0.1/database')

    assert Path(config.config_file_name or '').name == 'alembic.ini'
    assert Path(config.get_main_option('script_location')).is_absolute()
    assert Path(config.get_main_option('script_location')).name == 'migrations'
    assert config.get_main_option('sqlalchemy.url').endswith('/database')


def test_alembic_script_location_is_independent_of_process_working_directory(monkeypatch) -> None:
    from app.config.settings import PROJECT_ROOT
    from app.database.migrations import build_alembic_config

    monkeypatch.chdir(PROJECT_ROOT / 'backend')
    scripts = ScriptDirectory.from_config(build_alembic_config('postgresql+psycopg://localhost/aoi_app'))

    assert scripts.get_current_head() == '0004_create_inspection_runtime'


def test_baseline_inventory_rejects_missing_columns() -> None:
    from app.database.migrations import BaselineSchemaMismatch, verify_baseline_inventory

    try:
        verify_baseline_inventory({'users': {'id', 'email'}})
    except BaselineSchemaMismatch as error:
        assert 'users' in str(error)
    else:
        raise AssertionError('Incomplete baseline inventory was accepted.')