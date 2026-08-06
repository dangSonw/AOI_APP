from datetime import datetime

from pydantic import Field

from app.schemas.base import ApiSchema


class RecipeResponse(ApiSchema):
    id: int
    slug: str
    name: str
    description: str
    is_active: bool


class RecipeCreateRequest(ApiSchema):
    slug: str = Field(min_length=1, max_length=128, pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    name: str = Field(min_length=1, max_length=255)
    description: str = Field(default='', max_length=2000)
