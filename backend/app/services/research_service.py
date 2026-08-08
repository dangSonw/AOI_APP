from __future__ import annotations

import hashlib
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


class ArtifactIntegrityError(RuntimeError):
    pass


class PromotionRejected(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    sha256: str
    media_type: str
    byte_length: int
    storage_uri: str


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, content: bytes, *, media_type: str) -> ArtifactRecord:
        digest = hashlib.sha256(content).hexdigest()
        path = self.root / digest[:2] / digest
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            temporary = path.with_suffix('.tmp')
            temporary.write_bytes(content)
            temporary.replace(path)
        return ArtifactRecord(digest, media_type, len(content), str(path))

    def read_verified(self, artifact: ArtifactRecord) -> bytes:
        path = Path(artifact.storage_uri).resolve()
        if self.root not in path.parents or path.name != artifact.sha256:
            raise ArtifactIntegrityError('Artifact storage URI is outside the content-addressed store.')
        content = path.read_bytes()
        if len(content) != artifact.byte_length or hashlib.sha256(content).hexdigest() != artifact.sha256:
            raise ArtifactIntegrityError('Artifact checksum or byte length does not match its immutable record.')
        return content


@dataclass(frozen=True, slots=True)
class ResearchRunRecord:
    run_id: str
    experiment_id: str
    code_revision: str
    node_versions: dict[str, str]
    environment: dict[str, Any]
    random_seeds: dict[str, int]
    resources: dict[str, Any]
    dataset_versions: dict[str, str]
    parameters: dict[str, Any]
    metrics: dict[str, float]
    output_artifacts: dict[str, str]
    status: Literal['queued', 'running', 'completed', 'failed', 'cancelled']
    error: str | None


def build_reproducibility_manifest(run: ResearchRunRecord) -> dict[str, Any]:
    return {
        'schemaVersion': 1,
        'runId': run.run_id,
        'experimentId': run.experiment_id,
        'codeRevision': run.code_revision,
        'nodeVersions': deepcopy(run.node_versions),
        'environment': deepcopy(run.environment),
        'randomSeeds': deepcopy(run.random_seeds),
        'resources': deepcopy(run.resources),
        'datasetVersions': deepcopy(run.dataset_versions),
        'parameters': deepcopy(run.parameters),
        'metrics': deepcopy(run.metrics),
        'outputArtifacts': deepcopy(run.output_artifacts),
        'status': run.status,
        'error': run.error,
    }


@dataclass(frozen=True, slots=True)
class ResearchJobSpec:
    run_id: str
    node_id: str
    execution_target: str
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ModelVersionRecord:
    model_name: str
    version: int
    run_id: str
    artifact_sha256: str


@dataclass(frozen=True, slots=True)
class PromotionEvent:
    action: Literal['promote', 'rollback']
    model_name: str
    alias: str
    previous_version: int | None
    next_version: int
    actor_id: int
    reason: str


@dataclass(slots=True)
class ModelRegistry:
    _versions: dict[str, list[ModelVersionRecord]] = field(default_factory=dict)
    _aliases: dict[tuple[str, str], int] = field(default_factory=dict)
    _history: dict[tuple[str, str], list[int]] = field(default_factory=dict)
    events: list[PromotionEvent] = field(default_factory=list)

    def register_version(self, model_name: str, *, run_id: str, artifact_sha256: str) -> ModelVersionRecord:
        if len(artifact_sha256) != 64 or any(character not in '0123456789abcdef' for character in artifact_sha256):
            raise ValueError('Model artifact SHA-256 is invalid.')
        versions = self._versions.setdefault(model_name, [])
        record = ModelVersionRecord(model_name, len(versions) + 1, run_id, artifact_sha256)
        versions.append(record)
        return record

    def get_version(self, model_name: str, version: int) -> ModelVersionRecord:
        versions = self._versions.get(model_name, [])
        if version < 1 or version > len(versions):
            raise KeyError(f'Model {model_name} version {version} does not exist.')
        return versions[version - 1]

    def promote(self, model_name: str, alias: str, version: int, *, actor_id: int, reason: str, validation_passed: bool) -> PromotionEvent:
        if alias not in {'candidate', 'champion', 'rollback'}:
            raise PromotionRejected('Model alias is unsupported.')
        if not validation_passed:
            raise PromotionRejected('Model promotion requires passing validation evidence.')
        self.get_version(model_name, version)
        key = (model_name, alias)
        previous = self._aliases.get(key)
        if previous is not None:
            self._history.setdefault(key, []).append(previous)
        self._aliases[key] = version
        event = PromotionEvent('promote', model_name, alias, previous, version, actor_id, reason)
        self.events.append(event)
        return event

    def rollback(self, model_name: str, alias: str, *, actor_id: int, reason: str) -> PromotionEvent:
        key = (model_name, alias)
        history = self._history.get(key, [])
        if not history:
            raise PromotionRejected('Model alias has no prior version to restore.')
        previous = self._aliases[key]
        restored = history.pop()
        self._aliases[key] = restored
        event = PromotionEvent('rollback', model_name, alias, previous, restored, actor_id, reason)
        self.events.append(event)
        return event

    def resolve(self, model_name: str, alias: str) -> ModelVersionRecord:
        try:
            version = self._aliases[(model_name, alias)]
        except KeyError as error:
            raise PromotionRejected(f'Model {model_name} alias {alias} is not assigned.') from error
        return self.get_version(model_name, version)


def resolve_production_bindings(value: Any, registry: ModelRegistry) -> Any:
    if isinstance(value, list):
        return [resolve_production_bindings(item, registry) for item in value]
    if isinstance(value, dict):
        if set(value) == {'modelName', 'alias'}:
            record = registry.resolve(str(value['modelName']), str(value['alias']))
            return {
                'modelName': record.model_name,
                'modelVersion': record.version,
                'artifactSha256': record.artifact_sha256,
            }
        return {key: resolve_production_bindings(item, registry) for key, item in value.items()}
    return value
