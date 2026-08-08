from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


class InspectionCancelled(RuntimeError):
    pass


class InspectionTimedOut(RuntimeError):
    pass


@dataclass(slots=True)
class CancellationToken:
    cancelled: bool = False


@dataclass(frozen=True, slots=True)
class ExecutionContext:
    run_id: str
    node_id: str
    deadline: datetime
    cancellation: CancellationToken
    resources: dict[str, Any]

    def checkpoint(self) -> None:
        if self.cancellation.cancelled:
            raise InspectionCancelled(f'Inspection run {self.run_id} was cancelled.')
        if datetime.now(timezone.utc) >= self.deadline:
            raise InspectionTimedOut(f'Node {self.node_id} exceeded its deadline.')


@dataclass(frozen=True, slots=True)
class InspectionInput:
    artifact_sha256: str
    observed_sha256: str
    byte_length: int
    is_blurred: bool
    is_registered: bool
    motion_in_position: bool
    pose_observed_at: datetime
    pose_tolerance_seconds: float
    reference_score: float = 0.0


@dataclass(frozen=True, slots=True)
class NodeRunOutcome:
    node_id: str
    status: Literal['completed', 'faulted', 'cancelled']
    parameters: dict[str, Any]
    outputs: dict[str, Any]
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class InspectionOutcome:
    decision: Literal['PASS', 'FAIL', 'FAULT', 'CANCELLED']
    score: float | None
    evidence_sha256: str
    node_runs: tuple[NodeRunOutcome, ...]
    error_code: str | None = None


def _evidence_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _precheck(value: InspectionInput) -> str | None:
    if value.byte_length <= 0:
        return 'corrupt'
    if len(value.artifact_sha256) != 64 or value.artifact_sha256 != value.observed_sha256:
        return 'checksum-invalid'
    if value.is_blurred:
        return 'blurred'
    if not value.is_registered:
        return 'unregistered'
    if not value.motion_in_position:
        return 'motion-not-in-position'
    age = (datetime.now(timezone.utc) - value.pose_observed_at).total_seconds()
    if age < 0 or age > value.pose_tolerance_seconds:
        return 'stale-pose'
    return None


class InspectionOrchestrator:
    def run_reference_slice(
        self,
        value: InspectionInput,
        *,
        threshold: float,
        algorithm_version: str = '2.0.0',
    ) -> InspectionOutcome:
        error = _precheck(value)
        base_evidence: dict[str, Any] = {
            'artifactSha256': value.artifact_sha256,
            'observedSha256': value.observed_sha256,
            'byteLength': value.byte_length,
            'threshold': threshold,
        }
        if algorithm_version == '2.0.0':
            base_evidence.update(algorithmVersion=algorithm_version, referenceScore=value.reference_score)
        if error:
            node = NodeRunOutcome('safety-precheck', 'faulted', {}, {}, error)
            return InspectionOutcome('FAULT', None, _evidence_hash({**base_evidence, 'error': error}), (node,), error)

        if algorithm_version == '1.0.0':
            score = 1.0 - (sum(bytes.fromhex(value.artifact_sha256)) / (32 * 255))
        elif algorithm_version == '2.0.0':
            score = min(max(value.reference_score, 0.0), 1.0)
        else:
            raise ValueError(f'Unsupported deterministic reference version: {algorithm_version}.')
        decision: Literal['PASS', 'FAIL'] = 'PASS' if score <= threshold else 'FAIL'
        outputs = {'score': score, 'decision': decision, 'artifactSha256': value.artifact_sha256}
        node = NodeRunOutcome('deterministic-reference', 'completed', {'threshold': threshold}, outputs)
        return InspectionOutcome(decision, score, _evidence_hash({**base_evidence, **outputs}), (node,))


def recover_interrupted_status(status: str) -> tuple[str, str | None]:
    if status in {'moving', 'capturing', 'executing'}:
        return 'faulted', 'restart-during-physical-operation'
    if status in {'queued', 'precheck'}:
        return 'cancelled', 'restart-before-execution'
    return status, None
