import argparse
from collections.abc import Mapping, Set
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, create_engine, inspect

from app.config.settings import PROJECT_ROOT, get_settings


BASELINE_REVISION = '0001_existing_schema_baseline'
BASELINE_COLUMNS: dict[str, frozenset[str]] = {
    'users': frozenset({'id', 'email', 'full_name', 'hashed_password', 'is_active', 'created_at'}),
    'recipes': frozenset({'id', 'slug', 'name', 'description', 'is_active', 'created_at', 'updated_at'}),
    'inspection_results': frozenset({
        'id', 'board_serial', 'lot', 'recipe_id', 'recipe_name', 'operator_id', 'result',
        'defect_count', 'score', 'cycle_time_ms', 'camera_config', 'review_decision',
        'reviewed_by', 'reviewed_at', 'inspected_at',
    }),
    'defects': frozenset({
        'id', 'result_id', 'defect_type', 'severity', 'location_x', 'location_y',
        'width', 'height', 'confidence', 'description', 'detected_at',
    }),
    'inspection_images': frozenset({
        'id', 'result_id', 'defect_id', 'image_type', 'relative_path', 'file_size_bytes',
        'width_px', 'height_px', 'sha256_hash', 'media_type', 'captured_at',
    }),
    'audit_events': frozenset({
        'id', 'actor_id', 'action', 'method', 'path', 'resource_type', 'resource_id',
        'request_id', 'status_code', 'result', 'created_at',
    }),
}


class BaselineSchemaMismatch(RuntimeError):
    pass


def build_alembic_config(database_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / 'alembic.ini'))
    config.set_main_option('script_location', str(PROJECT_ROOT / 'database/migrations'))
    config.set_main_option('sqlalchemy.url', database_url.replace('%', '%%'))
    return config


def upgrade_database(database_url: str) -> None:
    command.upgrade(build_alembic_config(database_url), 'head')


def verify_database_revision(connection: Connection) -> None:
    config = build_alembic_config(connection.engine.url.render_as_string(hide_password=False))
    current = MigrationContext.configure(connection).get_current_revision()
    head = ScriptDirectory.from_config(config).get_current_head()
    if current != head:
        raise RuntimeError(
            f'Database revision {current or "unversioned"} does not match required revision {head}.'
        )


def verify_baseline_inventory(inventory: Mapping[str, Set[str]]) -> None:
    differences: list[str] = []
    for table_name, required_columns in BASELINE_COLUMNS.items():
        actual_columns = frozenset(inventory.get(table_name, set()))
        if actual_columns != required_columns:
            missing = sorted(required_columns - actual_columns)
            extra = sorted(actual_columns - required_columns)
            differences.append(f'{table_name}: missing={missing}, extra={extra}')
    if differences:
        raise BaselineSchemaMismatch('Existing database does not match baseline: ' + '; '.join(differences))


def baseline_existing_database(database_url: str) -> None:
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        inventory = {
            table_name: {column['name'] for column in inspector.get_columns(table_name)}
            for table_name in BASELINE_COLUMNS
            if inspector.has_table(table_name)
        }
        verify_baseline_inventory(inventory)
        command.stamp(build_alembic_config(database_url), BASELINE_REVISION)
        upgrade_database(database_url)
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description='Manage AOI Studio database revisions.')
    parser.add_argument('operation', choices=('upgrade', 'baseline-existing', 'current', 'check'))
    args = parser.parse_args()
    database_url = get_settings().database_url
    if args.operation == 'upgrade':
        upgrade_database(database_url)
        return
    if args.operation == 'baseline-existing':
        baseline_existing_database(database_url)
        return
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            if args.operation == 'check':
                verify_database_revision(connection)
            else:
                revision = MigrationContext.configure(connection).get_current_revision()
                print(revision or 'unversioned')
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()