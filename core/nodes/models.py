from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeAlias


NodeInputs: TypeAlias = Mapping[str, Any]
NodeParameters: TypeAlias = Mapping[str, bool | int | float | str]
NodeOutputs: TypeAlias = Mapping[str, Any]
NodeExecutor: TypeAlias = Callable[[NodeInputs, NodeParameters], NodeOutputs]


class NodeUse(StrEnum):
    TEST = 'test'
    DEBUG = 'debug'
    RELEASE = 'release'


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