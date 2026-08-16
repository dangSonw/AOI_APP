import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any, TypeAlias

from core.algorithms.models import AlgorithmDefinition, ParameterValue

from .errors import NodeArtifactIntegrityError, NodeExecutionCancelled


NodeInputs: TypeAlias = Mapping[str, Any]
NodeParameters: TypeAlias = Mapping[str, ParameterValue]
NodeOutputs: TypeAlias = Mapping[str, Any]
NodeExecutor: TypeAlias = Callable[[NodeInputs, NodeParameters], NodeOutputs]


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(character in '0123456789abcdef' for character in value)


@dataclass(frozen=True, slots=True)
class ArtifactBinding:
    sha256: str
    media_type: str
    byte_length: int

    def __post_init__(self) -> None:
        if not _is_sha256(self.sha256):
            raise ValueError('Artifact SHA-256 is invalid.')
        if not self.media_type:
            raise ValueError('Artifact media type is required.')
        if self.byte_length < 0:
            raise ValueError('Artifact byte length cannot be negative.')

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'ArtifactBinding':
        if set(value) != {'artifactSha256', 'mediaType', 'byteLength'}:
            raise ValueError('Artifact binding must contain only immutable artifact fields.')
        return cls(
            sha256=str(value['artifactSha256']),
            media_type=str(value['mediaType']),
            byte_length=int(value['byteLength']),
        )


@dataclass(frozen=True, slots=True)
class ModelBinding:
    model_name: str
    model_version: int
    artifact_sha256: str

    def __post_init__(self) -> None:
        if not self.model_name:
            raise ValueError('Model name is required.')
        if self.model_version < 1:
            raise ValueError('Model version must identify a published version.')
        if not _is_sha256(self.artifact_sha256):
            raise ValueError('Model artifact SHA-256 is invalid.')

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> 'ModelBinding':
        if set(value) != {'modelName', 'modelVersion', 'artifactSha256'}:
            raise ValueError('Model binding must contain only immutable model fields.')
        return cls(
            model_name=str(value['modelName']),
            model_version=int(value['modelVersion']),
            artifact_sha256=str(value['artifactSha256']),
        )


class NodeDevice(StrEnum):
    CPU = 'cpu'
    CUDA = 'cuda'


ArtifactResolver: TypeAlias = Callable[[ArtifactBinding], bytes]
CancellationProbe: TypeAlias = Callable[[], bool]


def _not_cancelled() -> bool:
    return False


@dataclass(frozen=True, slots=True)
class NodeExecutionContext:
    artifacts: Mapping[str, ArtifactBinding] = MappingProxyType({})
    models: Mapping[str, ModelBinding] = MappingProxyType({})
    resolve_artifact: ArtifactResolver | None = None
    device: NodeDevice = NodeDevice.CPU
    is_cancelled: CancellationProbe = _not_cancelled

    def __post_init__(self) -> None:
        object.__setattr__(self, 'artifacts', MappingProxyType(dict(self.artifacts)))
        object.__setattr__(self, 'models', MappingProxyType(dict(self.models)))
        object.__setattr__(self, 'device', NodeDevice(self.device))

    def checkpoint(self) -> None:
        if self.is_cancelled():
            raise NodeExecutionCancelled('Node execution was cancelled.')

    def read_artifact(self, key: str, *, expected_media_types: tuple[str, ...] = ()) -> bytes:
        self.checkpoint()
        try:
            binding = self.artifacts[key]
        except KeyError as error:
            raise NodeArtifactIntegrityError(f'Artifact binding {key} is not available.') from error
        if expected_media_types and binding.media_type not in expected_media_types:
            raise NodeArtifactIntegrityError(
                f'Artifact binding {key} has unsupported media type {binding.media_type}.',
            )
        if self.resolve_artifact is None:
            raise NodeArtifactIntegrityError('Artifact resolver is not configured.')
        content = self.resolve_artifact(binding)
        if not isinstance(content, bytes):
            raise NodeArtifactIntegrityError('Artifact resolver must return bytes.')
        if len(content) != binding.byte_length or hashlib.sha256(content).hexdigest() != binding.sha256:
            raise NodeArtifactIntegrityError('Artifact checksum or byte length does not match its immutable binding.')
        return content


ContextualNodeExecutor: TypeAlias = Callable[
    [NodeInputs, NodeParameters, NodeExecutionContext],
    NodeOutputs,
]


class NodeUse(StrEnum):
    TEST = 'test'
    DEBUG = 'debug'
    RELEASE = 'release'


@dataclass(frozen=True, slots=True)
class NodeManifest:
    manifest_version: int
    catalog_order: int
    package_version: str
    id: str
    use: NodeUse
    execution_target: str
    capabilities: tuple[str, ...]
    resource_hints: Mapping[str, int]
    artifact_contracts: Mapping[str, tuple[str, ...]]
    parameter_migration_hooks: tuple[str, ...]
    inspector_kind: str
    custom_inspector_key: str | None
    definition: AlgorithmDefinition


@dataclass(frozen=True, slots=True)
class NodeRuntime:
    id: str
    use: NodeUse
    input_keys: tuple[str, ...]
    output_keys: tuple[str, ...]
    execute: NodeExecutor
    execute_with_context: ContextualNodeExecutor | None = None

    def invoke(
        self,
        inputs: NodeInputs,
        parameters: NodeParameters,
        *,
        context: NodeExecutionContext | None = None,
    ) -> NodeOutputs:
        if context is not None:
            context.checkpoint()
        if self.execute_with_context is None:
            return self.execute(inputs, parameters)
        if context is None:
            return self.execute(inputs, parameters)
        return self.execute_with_context(inputs, parameters, context)

    @property
    def input_count(self) -> int:
        return len(self.input_keys)

    @property
    def output_count(self) -> int:
        return len(self.output_keys)
