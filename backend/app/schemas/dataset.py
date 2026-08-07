from datetime import datetime

from pydantic import Field, field_validator

from app.schemas.base import ApiSchema

_NAME_PATTERN = r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$'
_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif'}


def _validate_safe_filename(value: str) -> str:
    if '..' in value or '/' in value or '\\' in value or '\x00' in value:
        raise ValueError('Filename contains unsafe characters.')
    if value.startswith('.'):
        raise ValueError('Hidden filenames are not allowed.')
    parts = value.rsplit('.', 1)
    if len(parts) != 2 or parts[1].lower() not in _ALLOWED_EXTENSIONS:
        raise ValueError(
            f'Unsupported file extension. Allowed: {", ".join(sorted(_ALLOWED_EXTENSIONS))}',
        )
    return value


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class DatasetCreateRequest(ApiSchema):
    name: str = Field(min_length=1, max_length=64, pattern=_NAME_PATTERN)
    description: str = Field(default='', max_length=512)


class DatasetUpdateRequest(ApiSchema):
    new_name: str | None = Field(default=None, min_length=1, max_length=64, pattern=_NAME_PATTERN)
    description: str | None = Field(default=None, max_length=512)


class CategoryCreateRequest(ApiSchema):
    name: str = Field(min_length=1, max_length=64, pattern=_NAME_PATTERN)


class CategoryRenameRequest(ApiSchema):
    new_name: str = Field(min_length=1, max_length=64, pattern=_NAME_PATTERN)


class ImageRenameRequest(ApiSchema):
    new_filename: str = Field(max_length=128)

    @field_validator('new_filename')
    @classmethod
    def validate_new_filename(cls, value: str) -> str:
        return _validate_safe_filename(value)


class ImageMoveRequest(ApiSchema):
    target_category: str = Field(min_length=1, max_length=64, pattern=_NAME_PATTERN)


class ImportCapturesRequest(ApiSchema):
    filenames: list[str] = Field(min_length=1, max_length=100)
    target_category: str = Field(min_length=1, max_length=64, pattern=_NAME_PATTERN)


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class CategorySummary(ApiSchema):
    name: str
    image_count: int
    total_size_bytes: int


class DatasetSummary(ApiSchema):
    name: str
    description: str
    total_images: int
    total_size_bytes: int
    category_count: int
    created_at: datetime
    updated_at: datetime


class DatasetDetail(DatasetSummary):
    categories: list[CategorySummary]


class ImageInfo(ApiSchema):
    filename: str
    size_bytes: int
    media_type: str
    width_px: int | None = None
    height_px: int | None = None
    created_at: datetime


class ImageListResponse(ApiSchema):
    images: list[ImageInfo]


class DatasetListResponse(ApiSchema):
    datasets: list[DatasetSummary]


class CaptureFile(ApiSchema):
    relative_path: str
    filename: str
    size_bytes: int


class CaptureListResponse(ApiSchema):
    files: list[CaptureFile]
