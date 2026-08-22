from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class TensorSpec(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra='forbid')

    name: str = Field(min_length=1, max_length=128)
    dtype: str = Field(pattern=r'^(float32|float16|int64|int32|uint8|bool)$')
    shape: list[int | str] = Field(min_length=1, max_length=8)

    @field_validator('shape')
    @classmethod
    def validate_shape(cls, value: list[int | str]) -> list[int | str]:
        if any((isinstance(item, int) and item < -1) or (isinstance(item, str) and not item.strip()) for item in value):
            raise ValueError('Tensor dimensions must be positive, -1, or a non-empty symbolic name.')
        return value


class DeepLearningArtifactContract(BaseModel):
    """Portable contract for an externally trained ONNX model artifact.

    This describes the boundary only; parsing/executing ONNX is deliberately left
    to a separately locked inference adapter.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra='forbid')

    format: str = Field(pattern=r'^onnx$')
    runtime: str = Field(pattern=r'^onnxruntime$')
    runtime_version: str = Field(min_length=1, max_length=64)
    input_schema: list[TensorSpec] = Field(min_length=1, max_length=32)
    output_schema: list[TensorSpec] = Field(min_length=1, max_length=32)
    preprocessing: dict[str, Any] = Field(default_factory=dict)
    postprocessing: dict[str, Any] = Field(default_factory=dict)

    @field_validator('input_schema', 'output_schema')
    @classmethod
    def unique_tensor_names(cls, value: list[TensorSpec]) -> list[TensorSpec]:
        names = [item.name for item in value]
        if len(names) != len(set(names)):
            raise ValueError('Tensor names must be unique within a schema.')
        return value


def validate_external_artifact_contract(value: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize an external deep-learning artifact contract."""
    return DeepLearningArtifactContract.model_validate(value).model_dump(by_alias=True)