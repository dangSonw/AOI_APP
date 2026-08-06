from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import CurrentUser
from app.config.settings import get_settings
from app.schemas.workstation_preferences import WorkstationPreferencesSchema
from app.services.workstation_preference_repository import (
    InvalidWorkstationId,
    PreferenceStorageError,
    StalePreferenceRevision,
    WorkstationPreferenceRepository,
)


router = APIRouter(prefix='/api/workstation-preferences', tags=['workstation-preferences'])


def get_preference_repository() -> WorkstationPreferenceRepository:
    return WorkstationPreferenceRepository(get_settings().preferences_data_path)


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
    current_user: CurrentUser,
    repository: PreferenceRepositoryDependency,
) -> WorkstationPreferencesSchema:
    try:
        return repository.save(current_user.id, workstation_id, preferences)
    except InvalidWorkstationId as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except StalePreferenceRevision as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except PreferenceStorageError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error