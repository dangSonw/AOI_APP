from sqlalchemy import create_engine, inspect

from app.database.migrations import upgrade_database
from test_database_migration_runtime import isolated_database_url


def test_settings_migration_creates_version_platform_and_audit_metadata() -> None:
    with isolated_database_url() as database_url:
        upgrade_database(database_url)
        engine = create_engine(database_url)
        try:
            inspector = inspect(engine)
            assert {'settings_documents', 'settings_versions', 'settings_activations'} <= set(inspector.get_table_names())
            version_columns = {column['name']: column for column in inspector.get_columns('settings_versions')}
            assert version_columns['payload']['type'].__class__.__name__ == 'JSONB'
            assert {'before_checksum', 'after_checksum', 'reason', 'client_metadata'} <= {
                column['name'] for column in inspector.get_columns('audit_events')
            }
            assert {'document_id', 'revision'} in [
                set(constraint['column_names'])
                for constraint in inspector.get_unique_constraints('settings_versions')
            ]
        finally:
            engine.dispose()