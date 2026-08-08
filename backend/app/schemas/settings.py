from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.schemas.base import ApiSchema


SettingsScope = Literal['user', 'workstation', 'recipe', 'system']


class SettingsVersionCreate(ApiSchema):
    document_key: str = Field(min_length=1, max_length=128)
    expected_revision: int = Field(ge=0)
    schema_version: int = Field(default=1, ge=1)
    payload: dict[str, Any]
    reason: str = Field(default='', max_length=2000)


class SettingsValidationRequest(ApiSchema):
    document_key: str = Field(min_length=1, max_length=128)
    schema_version: int = Field(default=1, ge=1)
    payload: dict[str, Any]


class SettingsRollbackRequest(ApiSchema):
    document_key: str = Field(min_length=1, max_length=128)
    expected_revision: int = Field(ge=0)
    target_revision: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=2000)


class SettingsActivationRequest(ApiSchema):
    document_key: str = Field(min_length=1, max_length=128)
    revision: int = Field(ge=1)
    reason: str = Field(default='', max_length=2000)


class SettingsVersionResponse(ApiSchema):
    id: int
    revision: int
    schema_version: int
    payload: dict[str, Any]
    checksum: str
    created_by: int
    reason: str
    source_version_id: int | None
    created_at: datetime


class SettingsDocumentResponse(ApiSchema):
    scope: SettingsScope
    subject_id: str
    document_key: str
    owner_user_id: int | None
    current_revision: int
    current: SettingsVersionResponse | None
    active_revision: int | None


class SettingsHistoryResponse(ApiSchema):
    versions: list[SettingsVersionResponse]
    total: int


class SettingsExportEnvelope(ApiSchema):
    format_version: Literal[1] = 1
    scope: SettingsScope
    subject_id: str
    document_key: str
    owner_user_id: int | None
    revision: int = Field(ge=1)
    schema_version: int = Field(ge=1)
    payload: dict[str, Any]
    payload_checksum: str = Field(pattern=r'^[a-f0-9]{64}$')