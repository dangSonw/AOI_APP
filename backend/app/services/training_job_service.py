from __future__ import annotations

from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import math
import os
import platform
import subprocess
import sys
from pathlib import Path
from types import MappingProxyType
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recipe import Recipe
from app.models.research import ResearchExperiment, ResearchRun
from app.schemas.training import TrainingJobCreate
from app.services.training_dataset_resolver import ImmutableDatasetHandle, resolve_immutable_dataset
from app.services.workflow_repository import WorkflowRepository
from core.algorithms.models import ParameterDefinition, ParameterKind, is_json_parameter_value
from core.nodes.models import NodeManifest
from core.nodes.registry import get_node_manifest_registry
from core.pipeline.models import Workflow
from core.training.contracts import (
    DatasetBinding, TERMINAL_TRAINING_STATUSES, TrainingJobStatus, transition_training_status,
)


class TrainingJobError(RuntimeError):
    pass


class TrainingJobNotFound(TrainingJobError):
    pass


class TrainingJobValidationError(TrainingJobError):
    pass


class TrainingJobConflict(TrainingJobError):
    pass


@dataclass(frozen=True, slots=True)
class TrainingJobDispatch:
    run_id: str
    node_id: str
    node_instance_id: str
    action_name: str
    execution_target: str
    datasets: Mapping[str, ImmutableDatasetHandle]
    parameters: Mapping[str, Any]
    random_seeds: Mapping[str, int]
    actor_id: int

    def __post_init__(self) -> None:
        object.__setattr__(self, 'datasets', MappingProxyType(dict(self.datasets)))
        object.__setattr__(self, 'parameters', MappingProxyType(dict(self.parameters)))
        object.__setattr__(self, 'random_seeds', MappingProxyType(dict(self.random_seeds)))


ManifestRegistry = Callable[[], dict[str, NodeManifest]]
WorkflowReader = Callable[[str], Workflow]
DatasetResolver = Callable[[DatasetBinding], ImmutableDatasetHandle]
TrainingDispatcher = Callable[[TrainingJobDispatch], None]
CodeRevisionProvider = Callable[[], str]
_TRAINING_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix='aoi-training')


def _code_revision() -> str:
    configured = os.environ.get('AOI_CODE_REVISION', '').strip()
    if configured:
        return configured[:64]
    try:
        return subprocess.run(
            ['git', 'rev-parse', '--verify', 'HEAD'], check=True, capture_output=True,
            text=True, timeout=2,
        ).stdout.strip()[:64]
    except (OSError, subprocess.SubprocessError):
        return 'unknown'


def _server_environment() -> dict[str, Any]:
    return {
        'python': platform.python_version(),
        'implementation': platform.python_implementation(),
        'platform': sys.platform,
    }


def _parameter_value_is_valid(definition: ParameterDefinition, value: object) -> bool:
    kind = definition.kind
    if kind is ParameterKind.BOOLEAN:
        valid = isinstance(value, bool)
    elif kind is ParameterKind.INTEGER:
        valid = isinstance(value, int) and not isinstance(value, bool)
    elif kind is ParameterKind.NUMBER:
        valid = isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    elif kind in {ParameterKind.JSON, ParameterKind.REFERENCE}:
        valid = is_json_parameter_value(value)
    elif kind is ParameterKind.SELECT:
        valid = value in definition.options
    elif kind in {ParameterKind.TEXT, ParameterKind.MODEL_REFERENCE}:
        valid = isinstance(value, str) if kind is ParameterKind.TEXT else is_json_parameter_value(value)
    else:
        valid = False
    if valid and kind in {ParameterKind.INTEGER, ParameterKind.NUMBER}:
        numeric = float(value)  # type: ignore[arg-type]
        valid = (
            (definition.minimum is None or numeric >= definition.minimum)
            and (definition.maximum is None or numeric <= definition.maximum)
        )
    return valid


def _validate_parameters(manifest: NodeManifest, values: Mapping[str, Any]) -> None:
    definitions = {definition.key: definition for definition in manifest.definition.parameters}
    if set(values) != set(definitions):
        raise TrainingJobValidationError('Training parameter keys do not match the node manifest.')
    for key, definition in definitions.items():
        if not _parameter_value_is_valid(definition, values[key]):
            raise TrainingJobValidationError(f'Training parameter {key} is invalid.')


class TrainingPlatform:
    def __init__(
        self,
        *,
        manifest_registry: ManifestRegistry,
        workflow_reader: WorkflowReader,
        dataset_resolver: DatasetResolver,
        dispatcher: TrainingDispatcher,
        code_revision: CodeRevisionProvider = _code_revision,
    ) -> None:
        self._manifest_registry = manifest_registry
        self._workflow_reader = workflow_reader
        self._dataset_resolver = dataset_resolver
        self._dispatcher = dispatcher
        self._code_revision = code_revision

    def create(self, session: Session, request: TrainingJobCreate, *, actor_id: int) -> ResearchRun:
        if session.get(ResearchExperiment, request.experiment_id) is None:
            raise TrainingJobNotFound('Training experiment does not exist.')
        recipe = session.scalar(select(Recipe).where(Recipe.slug == request.recipe_slug))
        if recipe is None:
            raise TrainingJobNotFound('Training recipe does not exist.')
        try:
            workflow = self._workflow_reader(request.recipe_slug)
        except (FileNotFoundError, ValueError, RuntimeError) as error:
            raise TrainingJobNotFound('Training recipe workflow does not exist.') from error
        if workflow.revision != request.workflow_revision:
            raise TrainingJobValidationError('Training workflow revision is stale or unknown.')
        node = next((item for item in workflow.nodes if item.id == request.node_instance_id), None)
        if node is None:
            raise TrainingJobNotFound('Training node instance does not exist in the workflow revision.')
        if node.algorithm_id != request.node_id:
            raise TrainingJobValidationError('Training node identity does not match its workflow instance.')

        manifest = self._manifest_registry().get(request.node_id)
        if manifest is None:
            raise TrainingJobNotFound('Training node does not exist.')
        if manifest.manifest_version != 2:
            raise TrainingJobValidationError('Training actions require a manifest-v2 node.')
        action = manifest.actions.get(request.action_name)
        if action is None:
            raise TrainingJobValidationError('Training action is not declared by the node manifest.')
        if request.action_name != 'train':
            raise TrainingJobValidationError('Requested node action is not a training action.')
        if manifest.package_version != request.node_package_version:
            raise TrainingJobValidationError('Training node package version does not match the manifest.')
        if request.execution_target not in action.execution_targets:
            raise TrainingJobValidationError('Training execution target is not supported by the action.')
        if set(request.dataset_bindings) != set(action.dataset_inputs):
            raise TrainingJobValidationError('Training dataset bindings do not match the action contract.')
        _validate_parameters(manifest, request.parameters)

        resolved_datasets: dict[str, ImmutableDatasetHandle] = {}
        for key, binding in request.dataset_bindings.items():
            try:
                resolved_datasets[key] = self._dataset_resolver(DatasetBinding(
                    dataset_id=binding.dataset_id, version=binding.version,
                ))
            except (FileNotFoundError, ValueError) as error:
                raise TrainingJobValidationError(f'Training dataset {key} could not be resolved: {error}') from error

        parent: ResearchRun | None = None
        if request.parent_run_id is not None:
            parent = session.get(ResearchRun, request.parent_run_id)
            if parent is None:
                raise TrainingJobNotFound('Parent training run does not exist.')
            if parent.experiment_id != request.experiment_id:
                raise TrainingJobValidationError('Parent training run belongs to another experiment.')

        run = ResearchRun(
            id=f'train-{uuid4().hex}', experiment_id=request.experiment_id,
            status=TrainingJobStatus.QUEUED.value, execution_target=request.execution_target,
            code_revision=self._code_revision(), node_versions={request.node_id: request.node_package_version},
            environment=_server_environment(), random_seeds=request.random_seeds,
            resources={'executionTarget': request.execution_target},
            dataset_versions={key: value.model_dump(mode='json', by_alias=True) for key, value in request.dataset_bindings.items()},
            parameters=request.parameters, metrics={}, output_artifacts={}, error=None,
            created_by=actor_id, parent_run_id=parent.id if parent is not None else None,
            action_name=request.action_name, node_id=request.node_id,
            node_instance_id=request.node_instance_id, node_package_version=request.node_package_version,
            workflow_revision=request.workflow_revision,
            progress={'stage': TrainingJobStatus.QUEUED.value, 'processedUnits': 0, 'totalUnits': None, 'fraction': None, 'message': 'Queued'},
        )
        session.add(run)
        session.commit()
        session.refresh(run)
        self._dispatcher(TrainingJobDispatch(
            run_id=run.id, node_id=request.node_id, node_instance_id=request.node_instance_id,
            action_name=request.action_name, execution_target=request.execution_target,
            datasets=resolved_datasets, parameters=request.parameters,
            random_seeds=request.random_seeds, actor_id=actor_id,
        ))
        return run

    def read(self, session: Session, run_id: str) -> ResearchRun:
        run = session.get(ResearchRun, run_id)
        if run is None or run.action_name == 'legacy-run':
            raise TrainingJobNotFound('Training job does not exist.')
        return run

    def cancel(self, session: Session, run_id: str) -> ResearchRun:
        run = self.read(session, run_id)
        current = TrainingJobStatus(run.status)
        if current in TERMINAL_TRAINING_STATUSES:
            raise TrainingJobConflict(f'Training status {current} is terminal and cannot be cancelled.')
        next_status = (
            TrainingJobStatus.CANCELLED
            if current is TrainingJobStatus.QUEUED
            else TrainingJobStatus.CANCELLING
        )
        try:
            run.status = transition_training_status(current, next_status).value
        except ValueError as error:
            raise TrainingJobConflict(str(error)) from error
        if next_status is TrainingJobStatus.CANCELLED:
            from datetime import datetime, timezone
            run.completed_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(run)
        return run


def create_training_dispatcher(
    session_factory,
    projects_root,
    *,
    orchestrator=None,
    submit=None,
) -> TrainingDispatcher:
    from app.services.research_service import ArtifactStore
    from app.services.training_execution_service import (
        TrainingOrchestrator, execute_training_dispatch,
    )

    worker = orchestrator or TrainingOrchestrator(
        ArtifactStore(Path(projects_root) / 'research-artifacts'),
    )

    def dispatch_training_job(dispatch: TrainingJobDispatch) -> None:
        def run() -> None:
            with session_factory() as session:
                worker.execute(session, dispatch, execute_training_dispatch)

        (submit or _TRAINING_EXECUTOR.submit)(run)

    return dispatch_training_job

def create_default_training_platform(projects_root) -> TrainingPlatform:
    from app.database.session import SessionLocal

    return TrainingPlatform(
        manifest_registry=get_node_manifest_registry,
        workflow_reader=WorkflowRepository(projects_root).read,
        dataset_resolver=resolve_immutable_dataset,
        dispatcher=create_training_dispatcher(SessionLocal, projects_root),
    )