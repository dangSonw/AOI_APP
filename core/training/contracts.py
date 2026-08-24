from dataclasses import dataclass
from enum import StrEnum
import re


_IMMUTABLE_DATASET_VERSION = re.compile(r'^sha256:[0-9a-f]{64}$')


class TrainingJobStatus(StrEnum):
    QUEUED = 'queued'
    PREPARING_DATASET = 'preparing-dataset'
    VALIDATING = 'validating'
    TRAINING = 'training'
    EVALUATING = 'evaluating'
    PERSISTING_ARTIFACTS = 'persisting-artifacts'
    CANCELLING = 'cancelling'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


TERMINAL_TRAINING_STATUSES = frozenset({
    TrainingJobStatus.COMPLETED,
    TrainingJobStatus.FAILED,
    TrainingJobStatus.CANCELLED,
})

_ALLOWED_TRANSITIONS: dict[TrainingJobStatus, frozenset[TrainingJobStatus]] = {
    TrainingJobStatus.QUEUED: frozenset({
        TrainingJobStatus.PREPARING_DATASET, TrainingJobStatus.CANCELLED, TrainingJobStatus.FAILED,
    }),
    TrainingJobStatus.PREPARING_DATASET: frozenset({
        TrainingJobStatus.VALIDATING, TrainingJobStatus.CANCELLING, TrainingJobStatus.FAILED,
    }),
    TrainingJobStatus.VALIDATING: frozenset({
        TrainingJobStatus.TRAINING, TrainingJobStatus.CANCELLING, TrainingJobStatus.FAILED,
    }),
    TrainingJobStatus.TRAINING: frozenset({
        TrainingJobStatus.EVALUATING, TrainingJobStatus.CANCELLING, TrainingJobStatus.FAILED,
    }),
    TrainingJobStatus.EVALUATING: frozenset({
        TrainingJobStatus.PERSISTING_ARTIFACTS, TrainingJobStatus.CANCELLING, TrainingJobStatus.FAILED,
    }),
    TrainingJobStatus.PERSISTING_ARTIFACTS: frozenset({
        TrainingJobStatus.COMPLETED, TrainingJobStatus.CANCELLING, TrainingJobStatus.FAILED,
    }),
    TrainingJobStatus.CANCELLING: frozenset({TrainingJobStatus.CANCELLED, TrainingJobStatus.FAILED}),
}


class InvalidTrainingTransition(ValueError):
    pass


def transition_training_status(
    current: TrainingJobStatus,
    next_status: TrainingJobStatus,
) -> TrainingJobStatus:
    if current in TERMINAL_TRAINING_STATUSES:
        raise InvalidTrainingTransition(f'Training status {current} is terminal and cannot transition.')
    if next_status not in _ALLOWED_TRANSITIONS[current]:
        raise InvalidTrainingTransition(f'Invalid training status transition: {current} -> {next_status}.')
    return next_status


@dataclass(frozen=True, slots=True)
class DatasetBinding:
    dataset_id: str
    version: str

    def __post_init__(self) -> None:
        if not self.dataset_id:
            raise ValueError('Dataset ID cannot be empty.')
        if _IMMUTABLE_DATASET_VERSION.fullmatch(self.version) is None:
            raise ValueError('Dataset version must be an immutable SHA-256 identifier.')


@dataclass(frozen=True, slots=True)
class TrainingProgress:
    stage: TrainingJobStatus
    processed_units: int = 0
    total_units: int | None = None
    message: str = ''

    def __post_init__(self) -> None:
        if self.stage in TERMINAL_TRAINING_STATUSES:
            raise ValueError('Progress stage must be non-terminal.')
        if self.processed_units < 0:
            raise ValueError('Processed units cannot be negative.')
        if self.total_units is not None:
            if self.total_units < 1:
                raise ValueError('Total units must be positive.')
            if self.processed_units > self.total_units:
                raise ValueError('Processed units cannot exceed total units.')

    @property
    def fraction(self) -> float | None:
        if self.total_units is None:
            return None
        return self.processed_units / self.total_units