from pathlib import Path
from typing import Any

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
from pydantic import Field, JsonValue
from sqlalchemy import func, or_, select

from app.auth.dependencies import CurrentUser, DatabaseSession
from app.config.settings import PROJECT_ROOT
from app.models.research import (
    ModelAlias, ModelPromotionEvent, ModelRegistryEntry, ModelVersion,
    ResearchArtifact, ResearchExperiment, ResearchRun,
)
from app.schemas.base import ApiSchema
from app.services.research_service import ArtifactIntegrityError, ArtifactRecord, ArtifactStore, ResearchRunRecord, build_reproducibility_manifest
from app.services.deep_learning_contract import validate_external_artifact_contract

router = APIRouter(tags=['research'])
ARTIFACT_STORE = ArtifactStore(PROJECT_ROOT / 'data/artifacts')


class ExperimentCreate(ApiSchema):
    id: str = Field(pattern=r'^[a-z0-9][a-z0-9-]{1,63}$')
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default='', max_length=4000)


class RunCreate(ApiSchema):
    id: str = Field(pattern=r'^[a-z0-9][a-z0-9-]{1,63}$')
    experiment_id: str
    status: str
    execution_target: str
    code_revision: str
    node_versions: dict[str, str]
    environment: dict[str, JsonValue]
    random_seeds: dict[str, int]
    resources: dict[str, JsonValue]
    dataset_versions: dict[str, str]
    parameters: dict[str, JsonValue]
    metrics: dict[str, float]
    output_artifacts: dict[str, str]
    error: str | None = None


class ModelCreate(ApiSchema):
    name: str = Field(pattern=r'^[a-z0-9][a-z0-9-]{1,199}$')
    description: str = Field(default='', max_length=4000)


class ModelVersionCreate(ApiSchema):
    run_id: str
    artifact_id: int
    validation_evidence: dict[str, JsonValue]
    artifact_contract: dict[str, JsonValue] | None = None


class PromotionRequest(ApiSchema):
    version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=2000)


class RollbackRequest(ApiSchema):
    reason: str = Field(min_length=1, max_length=2000)


def _run_payload(run: ResearchRun) -> dict[str, Any]:
    return {
        'id': run.id, 'experimentId': run.experiment_id, 'status': run.status,
        'executionTarget': run.execution_target, 'codeRevision': run.code_revision,
        'nodeVersions': run.node_versions, 'environment': run.environment,
        'randomSeeds': run.random_seeds, 'resources': run.resources,
        'datasetVersions': run.dataset_versions, 'parameters': run.parameters,
        'metrics': run.metrics, 'outputArtifacts': run.output_artifacts, 'error': run.error,
        'createdAt': run.created_at,
    }


@router.post('/api/research/experiments', status_code=status.HTTP_201_CREATED)
def create_experiment(request: ExperimentCreate, user: CurrentUser, session: DatabaseSession) -> dict[str, Any]:
    if session.get(ResearchExperiment, request.id):
        raise HTTPException(409, 'Experiment already exists.')
    experiment = ResearchExperiment(id=request.id, name=request.name, description=request.description, created_by=user.id)
    session.add(experiment)
    session.commit()
    return {'id': experiment.id, 'name': experiment.name, 'description': experiment.description}


@router.post('/api/research/runs', status_code=status.HTTP_201_CREATED)
def create_run(request: RunCreate, user: CurrentUser, session: DatabaseSession) -> dict[str, Any]:
    if request.status not in {'queued', 'running', 'completed', 'failed', 'cancelled'}:
        raise HTTPException(422, 'Run status is invalid.')
    if request.execution_target not in {'local-cpu', 'local-gpu', 'remote-worker'}:
        raise HTTPException(422, 'Execution target is invalid.')
    if session.get(ResearchExperiment, request.experiment_id) is None:
        raise HTTPException(404, 'Experiment does not exist.')
    run = ResearchRun(
        id=request.id, experiment_id=request.experiment_id, status=request.status,
        execution_target=request.execution_target, code_revision=request.code_revision,
        node_versions=request.node_versions, environment=request.environment,
        random_seeds=request.random_seeds, resources=request.resources,
        dataset_versions=request.dataset_versions, parameters=request.parameters,
        metrics=request.metrics, output_artifacts=request.output_artifacts,
        error=request.error, created_by=user.id,
    )
    session.add(run)
    session.commit()
    return _run_payload(run)


@router.get('/api/research/runs')
def search_runs(_: CurrentUser, session: DatabaseSession, query: str = Query(default='', max_length=200)) -> list[dict[str, Any]]:
    statement = select(ResearchRun).join(ResearchExperiment).order_by(ResearchRun.created_at.desc()).limit(200)
    if query.strip():
        term = f'%{query.strip()}%'
        statement = statement.where(or_(ResearchRun.id.ilike(term), ResearchExperiment.name.ilike(term)))
    return [_run_payload(run) for run in session.scalars(statement)]


@router.get('/api/research/runs/{run_id}/reproducibility-manifest')
def reproducibility_manifest(run_id: str, _: CurrentUser, session: DatabaseSession) -> dict[str, Any]:
    run = session.get(ResearchRun, run_id)
    if run is None:
        raise HTTPException(404, 'Research run does not exist.')
    return build_reproducibility_manifest(ResearchRunRecord(
        run_id=run.id, experiment_id=run.experiment_id, code_revision=run.code_revision,
        node_versions=run.node_versions, environment=run.environment, random_seeds=run.random_seeds,
        resources=run.resources, dataset_versions=run.dataset_versions, parameters=run.parameters,
        metrics=run.metrics, output_artifacts=run.output_artifacts, status=run.status, error=run.error,
    ))


@router.post('/api/research/runs/{run_id}/artifacts', status_code=status.HTTP_201_CREATED)
async def create_artifact(run_id: str, _: CurrentUser, session: DatabaseSession, file: UploadFile = File()) -> dict[str, Any]:
    if session.get(ResearchRun, run_id) is None:
        raise HTTPException(404, 'Research run does not exist.')
    content = await file.read(512 * 1024 * 1024 + 1)
    if len(content) > 512 * 1024 * 1024:
        raise HTTPException(413, 'Research artifact exceeds 512 MiB.')
    stored = ARTIFACT_STORE.put_bytes(content, media_type=file.content_type or 'application/octet-stream')
    artifact = ResearchArtifact(
        run_id=run_id, name=file.filename or stored.sha256, sha256=stored.sha256,
        media_type=stored.media_type, byte_length=stored.byte_length, storage_uri=stored.storage_uri,
    )
    session.add(artifact)
    session.commit()
    session.refresh(artifact)
    return {'id': artifact.id, 'runId': run_id, 'name': artifact.name, 'sha256': artifact.sha256, 'mediaType': artifact.media_type, 'byteLength': artifact.byte_length}


@router.post('/api/models', status_code=status.HTTP_201_CREATED)
def create_model(request: ModelCreate, user: CurrentUser, session: DatabaseSession) -> dict[str, Any]:
    if session.scalar(select(ModelRegistryEntry).where(ModelRegistryEntry.name == request.name)):
        raise HTTPException(409, 'Model already exists.')
    model = ModelRegistryEntry(name=request.name, description=request.description, created_by=user.id)
    session.add(model)
    session.commit()
    session.refresh(model)
    return {'id': model.id, 'name': model.name, 'description': model.description}


def _model(session: DatabaseSession, name: str) -> ModelRegistryEntry:
    model = session.scalar(select(ModelRegistryEntry).where(ModelRegistryEntry.name == name))
    if model is None:
        raise HTTPException(404, 'Model does not exist.')
    return model


def _artifact_record(artifact: ResearchArtifact) -> ArtifactRecord:
    return ArtifactRecord(artifact.sha256, artifact.media_type, artifact.byte_length, artifact.storage_uri)


def _artifact_is_verified(artifact: ResearchArtifact) -> bool:
    try:
        ARTIFACT_STORE.read_verified(_artifact_record(artifact))
    except (ArtifactIntegrityError, FileNotFoundError, OSError):
        return False
    return True


def _require_verified_artifact(artifact: ResearchArtifact) -> None:
    if not _artifact_is_verified(artifact):
        raise HTTPException(422, 'Model artifact is missing or fails integrity verification.')


def _compatibility(evidence: dict[str, Any]) -> dict[str, str]:
    raw = evidence.get('compatibility', {})
    if not isinstance(raw, dict):
        return {}
    return {
        key: value for key, value in raw.items()
        if key in {'task', 'inputSchema', 'outputSchema', 'framework', 'status'} and isinstance(value, str) and value
    }


def _model_payload(model: ModelRegistryEntry, session: DatabaseSession) -> dict[str, Any]:
    versions = list(session.scalars(select(ModelVersion).where(ModelVersion.model_id == model.id).order_by(ModelVersion.version.desc())))
    aliases = {
        assignment.alias: version.version
        for assignment in session.scalars(select(ModelAlias).where(ModelAlias.model_id == model.id))
        if (version := session.get(ModelVersion, assignment.model_version_id)) is not None
    }
    return {
        'name': model.name,
        'description': model.description,
        'aliases': aliases,
        'versions': [{
            'version': version.version,
            'runId': version.run_id,
            'artifactSha256': artifact.sha256,
            'artifactVerified': _artifact_is_verified(artifact),
            'validationEvidence': version.validation_evidence,
            'compatibility': _compatibility(version.validation_evidence),
            'deepLearningContract': version.validation_evidence.get('deepLearningContract'),
        } for version in versions if (artifact := session.get(ResearchArtifact, version.artifact_id)) is not None],
    }


@router.get('/api/models')
def list_models(_: CurrentUser, session: DatabaseSession) -> list[dict[str, Any]]:
    return [_model_payload(model, session) for model in session.scalars(select(ModelRegistryEntry).order_by(ModelRegistryEntry.name))]


@router.get('/api/models/{model_name}')
def get_model(model_name: str, _: CurrentUser, session: DatabaseSession) -> dict[str, Any]:
    return _model_payload(_model(session, model_name), session)


@router.post('/api/models/{model_name}/versions', status_code=status.HTTP_201_CREATED)
def create_model_version(model_name: str, request: ModelVersionCreate, user: CurrentUser, session: DatabaseSession) -> dict[str, Any]:
    model = _model(session, model_name)
    artifact = session.get(ResearchArtifact, request.artifact_id)
    if artifact is None or artifact.run_id != request.run_id:
        raise HTTPException(422, 'Model artifact lineage does not match research run.')
    _require_verified_artifact(artifact)
    validation_evidence = dict(request.validation_evidence)
    if request.artifact_contract is not None:
        try:
            validation_evidence['deepLearningContract'] = validate_external_artifact_contract(request.artifact_contract)
        except ValueError as error:
            raise HTTPException(422, f'Deep-learning artifact contract is invalid: {error}') from error
    version_number = (session.scalar(select(func.max(ModelVersion.version)).where(ModelVersion.model_id == model.id)) or 0) + 1
    version = ModelVersion(
        model_id=model.id, version=version_number, run_id=request.run_id,
        artifact_id=artifact.id, validation_evidence=validation_evidence, created_by=user.id,
    )
    session.add(version)
    session.commit()
    session.refresh(version)
    return {'id': version.id, 'modelName': model.name, 'version': version.version, 'runId': version.run_id, 'artifactId': version.artifact_id, 'artifactSha256': artifact.sha256, 'validationEvidence': version.validation_evidence, 'deepLearningContract': version.validation_evidence.get('deepLearningContract')}


def _event_payload(event: ModelPromotionEvent, session: DatabaseSession) -> dict[str, Any]:
    previous = session.get(ModelVersion, event.previous_version_id) if event.previous_version_id else None
    next_version = session.get(ModelVersion, event.next_version_id)
    return {'id': event.id, 'action': event.action, 'alias': event.alias, 'previousVersion': previous.version if previous else None, 'nextVersion': next_version.version, 'reason': event.reason}


@router.post('/api/models/{model_name}/aliases/{alias}/promotions', status_code=status.HTTP_201_CREATED)
def promote_model(model_name: str, alias: str, request: PromotionRequest, user: CurrentUser, session: DatabaseSession) -> dict[str, Any]:
    if alias not in {'candidate', 'champion', 'rollback'}:
        raise HTTPException(422, 'Model alias is unsupported.')
    model = _model(session, model_name)
    version = session.scalar(select(ModelVersion).where(ModelVersion.model_id == model.id, ModelVersion.version == request.version))
    if version is None:
        raise HTTPException(404, 'Model version does not exist.')
    if version.validation_evidence.get('passed') is not True:
        raise HTTPException(422, 'Model promotion requires passing validation evidence.')
    artifact = session.get(ResearchArtifact, version.artifact_id)
    if artifact is None:
        raise HTTPException(422, 'Model version artifact is missing.')
    _require_verified_artifact(artifact)
    assignment = session.scalar(select(ModelAlias).where(ModelAlias.model_id == model.id, ModelAlias.alias == alias).with_for_update())
    previous_id = assignment.model_version_id if assignment else None
    if assignment is None:
        assignment = ModelAlias(model_id=model.id, alias=alias, model_version_id=version.id)
        session.add(assignment)
    else:
        assignment.model_version_id = version.id
    event = ModelPromotionEvent(model_id=model.id, alias=alias, action='promote', previous_version_id=previous_id, next_version_id=version.id, actor_id=user.id, reason=request.reason)
    session.add(event)
    session.commit()
    session.refresh(event)
    return _event_payload(event, session)


@router.post('/api/models/{model_name}/aliases/{alias}/rollback', status_code=status.HTTP_201_CREATED)
def rollback_model(model_name: str, alias: str, request: RollbackRequest, user: CurrentUser, session: DatabaseSession) -> dict[str, Any]:
    model = _model(session, model_name)
    assignment = session.scalar(select(ModelAlias).where(ModelAlias.model_id == model.id, ModelAlias.alias == alias).with_for_update())
    if assignment is None:
        raise HTTPException(409, 'Model alias is not assigned.')
    last = session.scalar(select(ModelPromotionEvent).where(ModelPromotionEvent.model_id == model.id, ModelPromotionEvent.alias == alias, ModelPromotionEvent.previous_version_id.is_not(None)).order_by(ModelPromotionEvent.id.desc()).limit(1))
    if last is None or last.previous_version_id is None:
        raise HTTPException(409, 'Model alias has no prior version to restore.')
    current_id = assignment.model_version_id
    assignment.model_version_id = last.previous_version_id
    event = ModelPromotionEvent(model_id=model.id, alias=alias, action='rollback', previous_version_id=current_id, next_version_id=last.previous_version_id, actor_id=user.id, reason=request.reason)
    session.add(event)
    session.commit()
    session.refresh(event)
    return _event_payload(event, session)


def _resolve_database_bindings(value: Any, session: DatabaseSession) -> Any:
    if isinstance(value, list):
        return [_resolve_database_bindings(item, session) for item in value]
    if isinstance(value, dict):
        if set(value) == {'modelName', 'alias'}:
            model = _model(session, str(value['modelName']))
            assignment = session.scalar(select(ModelAlias).where(
                ModelAlias.model_id == model.id, ModelAlias.alias == str(value['alias']),
            ))
            if assignment is None:
                raise HTTPException(422, 'Production model alias is not assigned.')
            version = session.get(ModelVersion, assignment.model_version_id)
            if version is None:
                raise HTTPException(422, 'Production model alias resolves to a missing version.')
            artifact = session.get(ResearchArtifact, version.artifact_id)
            if artifact is None:
                raise HTTPException(422, 'Production model artifact is missing.')
            _require_verified_artifact(artifact)
            return {'modelName': model.name, 'modelVersion': version.version, 'artifactSha256': artifact.sha256}
        return {key: _resolve_database_bindings(item, session) for key, item in value.items()}
    return value


@router.post('/api/models/resolve-production-bindings')
def resolve_database_production_bindings(payload: dict[str, JsonValue], _: CurrentUser, session: DatabaseSession) -> dict[str, Any]:
    return _resolve_database_bindings(payload, session)
