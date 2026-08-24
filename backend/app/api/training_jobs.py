from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select

from app.auth.dependencies import CurrentUser, DatabaseSession
from app.config.settings import get_settings
from app.models.research import ResearchArtifact, ResearchRun
from app.schemas.training import TrainingArtifactSchema, TrainingJobCreate, TrainingJobResponse
from app.services.training_job_service import (
    TrainingJobConflict, TrainingJobNotFound, TrainingJobValidationError,
    TrainingPlatform, create_default_training_platform,
)
from app.services.research_service import ArtifactIntegrityError, ArtifactRecord, ArtifactStore


router = APIRouter(prefix='/api/v1/research/training-jobs', tags=['research-training'])
artifact_router = APIRouter(prefix='/api/v1/research/artifacts', tags=['research-artifacts'])


def get_training_platform() -> TrainingPlatform:
    return create_default_training_platform(get_settings().projects_data_path)


def get_training_artifact_store() -> ArtifactStore:
    return ArtifactStore(get_settings().projects_data_path / 'research-artifacts')


TrainingArtifactStoreDependency = Annotated[ArtifactStore, Depends(get_training_artifact_store)]


TrainingPlatformDependency = Annotated[TrainingPlatform, Depends(get_training_platform)]


def _response(session: DatabaseSession, run: ResearchRun) -> TrainingJobResponse:
    artifacts = list(session.scalars(
        select(ResearchArtifact).where(ResearchArtifact.run_id == run.id).order_by(ResearchArtifact.id),
    ))
    return TrainingJobResponse(
        id=run.id, experiment_id=run.experiment_id, status=run.status,
        execution_target=run.execution_target, code_revision=run.code_revision,
        node_id=run.node_id, node_instance_id=run.node_instance_id,
        node_package_version=run.node_package_version, action_name=run.action_name,
        workflow_revision=run.workflow_revision, dataset_bindings=run.dataset_versions,
        parameters=run.parameters, random_seeds=run.random_seeds, environment=run.environment,
        progress=run.progress, metrics=run.metrics,
        output_artifacts=[TrainingArtifactSchema(
            id=item.id, name=item.name, sha256=item.sha256, media_type=item.media_type,
            byte_length=item.byte_length,
        ) for item in artifacts],
        error=run.error, parent_run_id=run.parent_run_id,
        created_at=run.created_at, completed_at=run.completed_at,
    )


def _raise(error: Exception) -> None:
    if isinstance(error, TrainingJobNotFound):
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    if isinstance(error, TrainingJobValidationError):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
    if isinstance(error, TrainingJobConflict):
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    raise error


@router.post('', response_model=TrainingJobResponse, status_code=status.HTTP_201_CREATED)
def create_training_job(
    request: TrainingJobCreate,
    user: CurrentUser,
    session: DatabaseSession,
    platform: TrainingPlatformDependency,
) -> TrainingJobResponse:
    try:
        return _response(session, platform.create(session, request, actor_id=user.id))
    except (TrainingJobNotFound, TrainingJobValidationError, TrainingJobConflict) as error:
        _raise(error)
        raise error


@router.get('/{run_id}', response_model=TrainingJobResponse)
def read_training_job(
    run_id: str, _: CurrentUser, session: DatabaseSession, platform: TrainingPlatformDependency,
) -> TrainingJobResponse:
    try:
        return _response(session, platform.read(session, run_id))
    except (TrainingJobNotFound, TrainingJobValidationError, TrainingJobConflict) as error:
        _raise(error)
        raise error


@router.post('/{run_id}/cancellations', response_model=TrainingJobResponse)
def cancel_training_job(
    run_id: str, _: CurrentUser, session: DatabaseSession, platform: TrainingPlatformDependency,
) -> TrainingJobResponse:
    try:
        return _response(session, platform.cancel(session, run_id))
    except (TrainingJobNotFound, TrainingJobValidationError, TrainingJobConflict) as error:
        _raise(error)
        raise error


@artifact_router.get('/{artifact_id}')
def read_training_artifact(
    artifact_id: int,
    _: CurrentUser,
    session: DatabaseSession,
    store: TrainingArtifactStoreDependency,
) -> Response:
    artifact = session.get(ResearchArtifact, artifact_id)
    if artifact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, 'Research artifact does not exist.')
    try:
        content = store.read_verified(ArtifactRecord(
            artifact.sha256, artifact.media_type, artifact.byte_length, artifact.storage_uri,
        ))
    except (ArtifactIntegrityError, OSError) as error:
        raise HTTPException(status.HTTP_409_CONFLICT, 'Artifact checksum or byte length verification failed.') from error
    return Response(
        content=content,
        media_type=artifact.media_type,
        headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'},
    )