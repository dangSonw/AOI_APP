from alembic import command
from sqlalchemy import create_engine, inspect, text

from app.database.migrations import build_alembic_config, upgrade_database
from test_database_migration_runtime import isolated_database_url


TRAINING_COLUMNS = {
    'parent_run_id', 'action_name', 'node_id', 'node_instance_id',
    'node_package_version', 'workflow_revision', 'progress',
}


def test_training_migration_upgrades_and_downgrades_research_runs() -> None:
    with isolated_database_url() as database_url:
        upgrade_database(database_url)
        engine = create_engine(database_url)
        try:
            columns = {column['name'] for column in inspect(engine).get_columns('research_runs')}
            assert TRAINING_COLUMNS <= columns
            foreign_keys = inspect(engine).get_foreign_keys('research_runs')
            assert any(key['constrained_columns'] == ['parent_run_id'] for key in foreign_keys)

            with engine.begin() as connection:
                connection.execute(text(
                    "INSERT INTO users (email, full_name, hashed_password) "
                    "VALUES ('migration@example.com', 'Migration', 'hash')",
                ))
                user_id = connection.execute(text(
                    "SELECT id FROM users WHERE email = 'migration@example.com'",
                )).scalar_one()
                connection.execute(text(
                    "INSERT INTO research_experiments (id, name, created_by) "
                    "VALUES ('migration-check', 'Migration check', :user_id)",
                ), {'user_id': user_id})
                connection.execute(text(
                    "INSERT INTO research_runs "
                    "(id, experiment_id, status, execution_target, code_revision, node_versions, "
                    "environment, random_seeds, resources, dataset_versions, parameters, metrics, "
                    "output_artifacts, created_by) VALUES "
                    "('legacy-running', 'migration-check', 'running', 'local', 'revision', '{}', "
                    "'{}', '{}', '{}', '{}', '{}', '{}', '{}', :user_id), "
                    "('v2-training', 'migration-check', 'training', 'local-cpu', 'revision', '{}', "
                    "'{}', '{}', '{}', '{}', '{}', '{}', '{}', :user_id)",
                ), {'user_id': user_id})

            command.downgrade(build_alembic_config(database_url), '0006_add_workflow_runtime_events')
            downgraded_columns = {column['name'] for column in inspect(engine).get_columns('research_runs')}
            assert not (TRAINING_COLUMNS & downgraded_columns)
            with engine.connect() as connection:
                assert connection.execute(text(
                    "SELECT status FROM research_runs WHERE id = 'v2-training'",
                )).scalar_one() == 'failed'
        finally:
            engine.dispose()