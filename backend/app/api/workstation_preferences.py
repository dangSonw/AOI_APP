from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import CurrentUser, DatabaseSession
from app.schemas.workstation_preferences import WorkstationPreferencesSchema
from app.services.workstation_preference_repository import (
    InvalidWorkstationId,
    PreferenceStorageError,
    StalePreferenceRevision,
    WorkstationPreferenceRepository,
)


router = APIRouter(prefix='/api/workstation-preferences', tags=['workstation-preferences'])


def get_preference_repository(session: DatabaseSession) -> WorkstationPreferenceRepository:
    return WorkstationPreferenceRepository(session)


PreferenceRepositoryDependency = Annotated[WorkstationPreferenceRepository, Depends(get_preference_repository)]


@router.get('/{workstation_id}', response_model=WorkstationPreferencesSchema)
def get_preferences(
    workstation_id: str,
    current_user: CurrentUser,
    repository: PreferenceRepositoryDependency,
) -> WorkstationPreferencesSchema:
    try:
        return repository.read(current_user.id, workstation_id)
    except InvalidWorkstationId as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except PreferenceStorageError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.put('/{workstation_id}', response_model=WorkstationPreferencesSchema)
def update_preferences(
    workstation_id: str,
    preferences: WorkstationPreferencesSchema,
    request: Request,
    current_user: CurrentUser,
    repository: PreferenceRepositoryDependency,
) -> WorkstationPreferencesSchema:
    try:
        updated = repository.save(
            current_user.id, workstation_id, preferences,
            actor_id=current_user.id, request_id=request.state.request_id,
        )
        repository.session.commit()
        request.state.audit_recorded = True
        return updated
    except InvalidWorkstationId as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except StalePreferenceRevision as error:
        repository.session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except PreferenceStorageError as error:
        repository.session.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error