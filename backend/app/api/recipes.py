from fastapi import APIRouter, HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.auth.dependencies import CurrentUser, DatabaseSession
from app.schemas.recipe import RecipeCreateRequest, RecipeResponse
from app.services.inspection_service import create_recipe, get_recipes


router = APIRouter(prefix='/api/recipes', tags=['recipes'])


@router.get('', response_model=list[RecipeResponse])
def list_recipes(
    _: CurrentUser,
    session: DatabaseSession,
) -> list[RecipeResponse]:
    recipes = get_recipes(session)
    return [RecipeResponse.model_validate(recipe) for recipe in recipes]


@router.post(
    '',
    response_model=RecipeResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_recipe(
    request: RecipeCreateRequest,
    _: CurrentUser,
    session: DatabaseSession,
) -> RecipeResponse:
    try:
        recipe = create_recipe(session, request.slug, request.name, request.description)
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='A recipe with this slug already exists.',
        ) from error
    return RecipeResponse.model_validate(recipe)
