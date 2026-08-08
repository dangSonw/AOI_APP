from pathlib import Path


def test_alembic_config_uses_repository_migration_directory() -> None:
    from app.database.migrations import build_alembic_config

    config = build_alembic_config('postgresql+psycopg://user:password@127.0.0.1/database')

    assert Path(config.config_file_name or '').name == 'alembic.ini'
    assert config.get_main_option('script_location') == 'database/migrations'
    assert config.get_main_option('sqlalchemy.url').endswith('/database')


def test_baseline_inventory_rejects_missing_columns() -> None:
    from app.database.migrations import BaselineSchemaMismatch, verify_baseline_inventory

    try:
        verify_baseline_inventory({'users': {'id', 'email'}})
    except BaselineSchemaMismatch as error:
        assert 'users' in str(error)
    else:
        raise AssertionError('Incomplete baseline inventory was accepted.')