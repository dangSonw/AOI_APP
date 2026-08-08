from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeAlias

from core.algorithms.models import AlgorithmDefinition, ParameterValue


NodeInputs: TypeAlias = Mapping[str, Any]
NodeParameters: TypeAlias = Mapping[str, ParameterValue]
NodeOutputs: TypeAlias = Mapping[str, Any]
NodeExecutor: TypeAlias = Callable[[NodeInputs, NodeParameters], NodeOutputs]


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

    @property
    def input_count(self) -> int:
        return len(self.input_keys)

    @property
    def output_count(self) -> int:
        return len(self.output_keys)
