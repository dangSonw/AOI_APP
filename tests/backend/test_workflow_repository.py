import json
from dataclasses import replace
from pathlib import Path

import pytest

from app.services.workflow_repository import (
    InvalidRecipeSlug,
    StaleWorkflowRevision,
    WorkflowRepository,
    WorkflowStorageError,
)
from core.pipeline import create_default_workflow


def test_missing_workflow_returns_unpersisted_default(tmp_path: Path) -> None:
    repository = WorkflowRepository(tmp_path)

    workflow = repository.read('rev-c-mainboard')

    assert workflow.revision == 0
    assert workflow.recipe_slug == 'rev-c-mainboard'
    assert not (tmp_path / 'rev-c-mainboard' / 'workflow.json').exists()


def test_save_is_atomic_increments_revision_and_round_trips(tmp_path: Path) -> None:
    repository = WorkflowRepository(tmp_path)

    saved = repository.save('rev-c-mainboard', create_default_workflow())
    restored = repository.read('rev-c-mainboard')
    workflow_path = tmp_path / 'rev-c-mainboard' / 'workflow.json'

    assert saved.revision == 1
    assert restored == saved
    assert json.loads(workflow_path.read_text(encoding='utf-8'))['revision'] == 1
    assert not list(workflow_path.parent.glob('*.tmp'))


def test_stale_save_does_not_overwrite_newer_workflow(tmp_path: Path) -> None:
    repository = WorkflowRepository(tmp_path)
    stale = create_default_workflow()
    saved = repository.save('rev-c-mainboard', stale)

    with pytest.raises(StaleWorkflowRevision):
        repository.save('rev-c-mainboard', stale)

    assert repository.read('rev-c-mainboard') == saved


@pytest.mark.parametrize('slug', ('../secret', 'Rev-C', 'a/b', '', 'trailing-'))
def test_recipe_slug_rejects_traversal_and_noncanonical_values(slug: str, tmp_path: Path) -> None:
    with pytest.raises(InvalidRecipeSlug):
        WorkflowRepository(tmp_path).read(slug)


def test_invalid_json_and_invalid_persisted_graph_raise_storage_error(tmp_path: Path) -> None:
    workflow_path = tmp_path / 'rev-c-mainboard' / 'workflow.json'
    workflow_path.parent.mkdir(parents=True)
    workflow_path.write_text('{broken', encoding='utf-8')
    repository = WorkflowRepository(tmp_path)

    with pytest.raises(WorkflowStorageError, match='invalid persisted workflow'):
        repository.read('rev-c-mainboard')

    workflow_path.write_text(
        json.dumps(
            {
                **repository.serialize(create_default_workflow()),
                'executionOrder': [],
            }
        ),
        encoding='utf-8',
    )
    with pytest.raises(WorkflowStorageError, match='invalid persisted workflow'):
        repository.read('rev-c-mainboard')


def test_invalid_submitted_graph_is_rejected_before_write(tmp_path: Path) -> None:
    repository = WorkflowRepository(tmp_path)
    invalid = replace(create_default_workflow(), execution_order=())

    with pytest.raises(WorkflowStorageError) as error:
        repository.save('rev-c-mainboard', invalid)

    assert error.value.validation_issues
    assert not (tmp_path / 'rev-c-mainboard' / 'workflow.json').exists()