from dataclasses import replace
from datetime import datetime, timezone
from types import MappingProxyType, SimpleNamespace

import pytest

from app.database import bootstrap as _database_bootstrap  # noqa: F401
from app.schemas.training import TrainingJobCreate
from app.services.training_job_service import (
    TrainingJobConflict, TrainingJobDispatch, TrainingJobNotFound, TrainingJobValidationError,
    TrainingPlatform, create_training_dispatcher,
)
from core.algorithms.models import (
    AlgorithmActionDefinition, AlgorithmDefinition, ParameterDefinition, ParameterKind,
)
from core.nodes.models import NodeManifest, NodeUse
from core.pipeline.models import Point, Workflow, WorkflowNode


class FakeSession:
    def __init__(self) -> None:
        self.experiment = SimpleNamespace(id='experiment-01')
        self.recipe = SimpleNamespace(slug='recipe-01')
        self.runs: dict[str, object] = {}

    def get(self, model, identity):
        if model.__name__ == 'ResearchExperiment':
            return self.experiment if identity == self.experiment.id else None
        return self.runs.get(identity)

    def scalar(self, statement):
        criteria = str(statement.whereclause.compile(compile_kwargs={'literal_binds': True}))
        return self.recipe if "recipes.slug = 'recipe-01'" in criteria else None

    def add(self, value) -> None:
        self.runs[value.id] = value

    def commit(self) -> None: pass
    def refresh(self, value) -> None: pass


def manifest() -> NodeManifest:
    action = AlgorithmActionDefinition(dataset_inputs=('training-dataset',), execution_targets=('local-cpu',), cancellable=True)
    definition = AlgorithmDefinition(
        id='fake-trainer', name='Fake', description='', category='Research', documentation_group='research',
        inputs=(), outputs=(), manifest_version=2, package_version='1.2.0', capabilities=('train',),
        actions=MappingProxyType({'train': action}), parameters=(
            ParameterDefinition('epochs', 'Epochs', ParameterKind.INTEGER, 2, minimum=1, maximum=5),
            ParameterDefinition('kernel', 'Kernel', ParameterKind.SELECT, 'linear', options=('linear', 'rbf')),
        ),
    )
    return NodeManifest(
        manifest_version=2, catalog_order=1, package_version='1.2.0', id='fake-trainer', use=NodeUse.RELEASE,
        execution_target='local-cpu', capabilities=('train',), resource_hints={}, artifact_contracts={},
        parameter_migration_hooks=(), inspector_kind='generic', custom_inspector_key=None,
        definition=definition, actions=MappingProxyType({'train': action}),
    )


def workflow() -> Workflow:
    return Workflow(
        recipe_slug='recipe-01', recipe_name='Recipe', version=2, revision=4,
        updated_at=datetime.now(timezone.utc), connections=(), execution_order=('node-01',),
        nodes=(WorkflowNode('node-01', 'fake-trainer', 'Trainer', Point(0, 0), {'epochs': 2, 'kernel': 'linear'}, ()),),
    )


def request(**updates) -> TrainingJobCreate:
    payload = {
        'experimentId': 'experiment-01', 'recipeSlug': 'recipe-01', 'workflowRevision': 4,
        'nodeInstanceId': 'node-01', 'nodeId': 'fake-trainer', 'nodePackageVersion': '1.2.0',
        'actionName': 'train', 'executionTarget': 'local-cpu',
        'datasetBindings': {'training-dataset': {'datasetId': 'images', 'version': 'sha256:' + 'a' * 64}},
        'parameters': {'epochs': 2, 'kernel': 'linear'}, 'randomSeeds': {'python': 42},
    }
    payload.update(updates)
    return TrainingJobCreate.model_validate(payload)


def platform(dispatched: list[TrainingJobDispatch]) -> TrainingPlatform:
    return TrainingPlatform(
        manifest_registry=lambda: {'fake-trainer': manifest()},
        workflow_reader=lambda slug: workflow() if slug == 'recipe-01' else (_ for _ in ()).throw(FileNotFoundError()),
        dataset_resolver=lambda binding: SimpleNamespace(dataset_id=binding.dataset_id, version=binding.version, items=()),
        dispatcher=dispatched.append,
        code_revision=lambda: 'server-revision',
    )


def test_create_persists_server_metadata_and_dispatches_typed_job() -> None:
    dispatched: list[TrainingJobDispatch] = []
    session = FakeSession()
    run = platform(dispatched).create(session, request(), actor_id=7)

    assert run.status == 'queued'
    assert run.code_revision == 'server-revision'
    assert run.environment['python']
    assert run.metrics == {} and run.output_artifacts == {}
    assert isinstance(dispatched[0], TrainingJobDispatch)
    assert dispatched[0].actor_id == 7
    assert dispatched[0].datasets['training-dataset'].dataset_id == 'images'


@pytest.mark.parametrize(('change', 'message'), [
    ({'experimentId': 'missing'}, 'experiment'),
    ({'recipeSlug': 'missing'}, 'recipe'),
    ({'nodeInstanceId': 'missing'}, 'node instance'),
    ({'nodeId': 'missing'}, 'node'),
    ({'actionName': 'evaluate'}, 'action'),
    ({'executionTarget': 'local-gpu'}, 'execution target'),
    ({'nodePackageVersion': '9.0.0'}, 'package version'),
    ({'workflowRevision': 3}, 'workflow revision'),
    ({'parameters': {'epochs': 99, 'kernel': 'linear'}}, 'parameter'),
    ({'parameters': {'epochs': 2, 'kernel': 'linear', 'extra': True}}, 'parameter'),
    ({'datasetBindings': {'wrong': {'datasetId': 'images', 'version': 'sha256:' + 'a' * 64}}}, 'dataset'),
])
def test_create_rejects_invalid_resolved_intent(change: dict, message: str) -> None:
    with pytest.raises((TrainingJobNotFound, TrainingJobValidationError), match=message):
        platform([]).create(FakeSession(), request(**change), actor_id=7)


def test_retry_parent_and_cancel_transitions_are_enforced() -> None:
    session = FakeSession()
    service = platform([])
    parent = service.create(session, request(), actor_id=7)
    child = service.create(session, request(parentRunId=parent.id), actor_id=7)
    assert child.parent_run_id == parent.id

    cancelled = service.cancel(session, child.id)
    assert cancelled.status == 'cancelled'
    with pytest.raises(TrainingJobConflict, match='terminal'):
        service.cancel(session, child.id)

    parent.status = 'training'
    assert service.cancel(session, parent.id).status == 'cancelling'


def test_training_dispatcher_opens_worker_session_and_executes_generic_adapter(tmp_path) -> None:
    calls = []
    submitted = []
    worker_session = object()
    class SessionContext:
        def __enter__(self): return worker_session
        def __exit__(self, *_): return None
    orchestrator = SimpleNamespace(execute=lambda session, dispatch, action: calls.append((session, dispatch, action)))
    dispatcher = create_training_dispatcher(
        lambda: SessionContext(), tmp_path, orchestrator=orchestrator,
        submit=lambda task: submitted.append(task),
    )
    job = SimpleNamespace(run_id='run-01')
    dispatcher(job)
    assert calls == []
    submitted[0]()
    assert calls[0][0] is worker_session and calls[0][1] is job
    assert calls[0][2].__name__ == 'execute_training_dispatch'