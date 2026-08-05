from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import CurrentUser
from app.config.settings import get_settings
from app.schemas.workflow import AlgorithmDefinitionSchema, ValidationIssueSchema, WorkflowSchema
from app.services.workflow_repository import (
    InvalidRecipeSlug,
    StaleWorkflowRevision,
    WorkflowRepository,
    WorkflowStorageError,
    WorkflowValidationError,
)
from core.algorithms import get_algorithm_catalog


router = APIRouter(prefix='/api', tags=['workflows'])


def get_workflow_repository() -> WorkflowRepository:
    return WorkflowRepository(get_settings().projects_data_path)


WorkflowRepositoryDependency = Annotated[WorkflowRepository, Depends(get_workflow_repository)]


@router.get('/algorithms', response_model=list[AlgorithmDefinitionSchema])
def get_algorithms(_: CurrentUser) -> list[AlgorithmDefinitionSchema]:
    return [AlgorithmDefinitionSchema.from_core(definition) for definition in get_algorithm_catalog()]


@router.get('/recipes/{recipe_slug}/workflow', response_model=WorkflowSchema)
def get_workflow(
    recipe_slug: str,
    _: CurrentUser,
    repository: WorkflowRepositoryDependency,
) -> WorkflowSchema:
    try:
        return WorkflowSchema.from_core(repository.read(recipe_slug))
    except InvalidRecipeSlug as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except WorkflowStorageError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.put('/recipes/{recipe_slug}/workflow', response_model=WorkflowSchema)
def update_workflow(
    recipe_slug: str,
    workflow: WorkflowSchema,
    _: CurrentUser,
    repository: WorkflowRepositoryDependency,
) -> WorkflowSchema:
    try:
        saved = repository.save(recipe_slug, workflow.to_core())
        return WorkflowSchema.from_core(saved)
    except InvalidRecipeSlug as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except WorkflowValidationError as error:
        detail = [
            ValidationIssueSchema.from_core(issue).model_dump(mode='json', by_alias=True, exclude_none=True)
            for issue in error.validation_issues
        ]
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail) from error
    except StaleWorkflowRevision as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except WorkflowStorageError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error