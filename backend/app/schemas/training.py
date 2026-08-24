from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field, JsonValue, field_validator

from app.schemas.base import ApiSchema
from core.training.contracts import DatasetBinding, TrainingJobStatus


_IDENTIFIER_PATTERN = r'^[a-z0-9][a-z0-9-]{0,127}$'


class StrictApiSchema(ApiSchema):
    model_config = ConfigDict(
        alias_generator=ApiSchema.model_config['alias_generator'],
        populate_by_name=True,
        from_attributes=True,
        extra='forbid',
    )


class DatasetBindingSchema(StrictApiSchema):
    dataset_id: str = Field(min_length=1, max_length=128, pattern=_IDENTIFIER_PATTERN)
    version: str

    @field_validator('version')
    @classmethod
    def validate_immutable_version(cls, value: str) -> str:
        DatasetBinding(dataset_id='validation', version=value)
        return value


class TrainingJobCreate(StrictApiSchema):
    experiment_id: str = Field(min_length=1, max_length=64, pattern=_IDENTIFIER_PATTERN)
    recipe_slug: str = Field(min_length=1, max_length=128, pattern=_IDENTIFIER_PATTERN)
    workflow_revision: int = Field(ge=1)
    node_instance_id: str = Field(min_length=1, max_length=128)
    node_id: str = Field(min_length=1, max_length=128, pattern=_IDENTIFIER_PATTERN)
    node_package_version: str = Field(min_length=1, max_length=64)
    action_name: str = Field(default='train', min_length=1, max_length=64)
    execution_target: str = Field(min_length=1, max_length=32)
    dataset_bindings: dict[str, DatasetBindingSchema] = Field(min_length=1, max_length=16)
    parameters: dict[str, JsonValue] = Field(default_factory=dict)
    random_seeds: dict[str, int] = Field(default_factory=dict)
    parent_run_id: str | None = Field(default=None, min_length=1, max_length=64)


class TrainingProgressSchema(ApiSchema):
    stage: TrainingJobStatus
    processed_units: int = Field(ge=0)
    total_units: int | None = Field(default=None, ge=1)
    fraction: float | None = Field(default=None, ge=0, le=1)
    message: str = Field(default='', max_length=1000)


class TrainingArtifactSchema(ApiSchema):
    id: int
    name: str
    sha256: str
    media_type: str
    byte_length: int


class TrainingJobResponse(ApiSchema):
    id: str
    experiment_id: str
    status: TrainingJobStatus
    execution_target: str
    code_revision: str
    node_id: str
    node_instance_id: str
    node_package_version: str
    action_name: str
    workflow_revision: int
    dataset_bindings: dict[str, DatasetBindingSchema]
    parameters: dict[str, JsonValue]
    random_seeds: dict[str, int]
    environment: dict[str, JsonValue]
    progress: TrainingProgressSchema | None
    metrics: dict[str, float]
    output_artifacts: list[TrainingArtifactSchema]
    error: str | None
    parent_run_id: str | None
    created_at: datetime
    completed_at: datetime | None