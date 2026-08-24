from datetime import datetime, timezone

from app.database import bootstrap as _database_bootstrap  # noqa: F401
from app.models.research import ResearchExperiment, ResearchRun
from app.services.training_execution_service import ORPHANED_TRAINING_REASON, recover_orphaned_training_jobs


class FakeSession:
    def __init__(self, runs): self.runs = runs
    def scalars(self, statement): return iter(self.runs)
    def commit(self): pass


def run(status: str) -> ResearchRun:
    return ResearchRun(
        id=f'run-{status}', experiment_id='experiment', status=status, execution_target='local-cpu',
        code_revision='revision', node_versions={}, environment={}, random_seeds={}, resources={},
        dataset_versions={}, parameters={}, metrics={}, output_artifacts={}, created_by=1,
        action_name='train', node_id='fake', node_instance_id='node', node_package_version='1',
        workflow_revision=1,
    )


def test_recovery_fails_only_orphaned_active_training_jobs() -> None:
    active = [run('preparing-dataset'), run('training'), run('cancelling')]
    completed = run('completed')
    session = FakeSession([*active, completed])

    assert recover_orphaned_training_jobs(session) == 3
    assert all(item.status == 'failed' and item.error == ORPHANED_TRAINING_REASON for item in active)
    assert all(item.completed_at is not None for item in active)
    assert completed.status == 'completed'