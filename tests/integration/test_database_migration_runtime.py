from collections.abc import Iterator
from contextlib import contextmanager
from uuid import uuid4

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from app.config.settings import get_settings


@contextmanager
def isolated_database_url() -> Iterator[str]:
    base_url = make_url(get_settings().database_url)
    schema = f'test_migration_{uuid4().hex}'
    admin_engine = create_engine(base_url)
    with admin_engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    try:
        query = dict(base_url.query)
        query['options'] = f'-csearch_path={schema}'
        yield base_url.set(query=query).render_as_string(hide_password=False)
    finally:
        with admin_engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        admin_engine.dispose()


def test_upgrade_from_empty_schema_creates_baseline_tables() -> None:
    from app.database.migrations import upgrade_database

    with isolated_database_url() as database_url:
        upgrade_database(database_url)
        engine = create_engine(database_url)
        try:
            assert {
                'alembic_version',
                'users',
                'recipes',
                'inspection_results',
                'defects',
                'inspection_images',
                'audit_events',
                'research_experiments',
                'research_runs',
                'research_artifacts',
                'model_registry_entries',
                'model_versions',
                'model_aliases',
                'model_promotion_events',
            } <= set(inspect(engine).get_table_names())
        finally:
            engine.dispose()


def test_database_revision_verification_accepts_head() -> None:
    from app.database.migrations import upgrade_database, verify_database_revision

    with isolated_database_url() as database_url:
        upgrade_database(database_url)
        engine = create_engine(database_url)
        try:
            with engine.connect() as connection:
                verify_database_revision(connection)
        finally:
            engine.dispose()