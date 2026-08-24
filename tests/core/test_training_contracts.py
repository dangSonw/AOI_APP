import pytest

from core.training.contracts import (
    DatasetBinding, InvalidTrainingTransition, TrainingJobStatus, TrainingProgress,
    transition_training_status,
)


@pytest.mark.parametrize(('current', 'next_status'), [
    ('queued', 'preparing-dataset'),
    ('preparing-dataset', 'validating'),
    ('validating', 'training'),
    ('training', 'evaluating'),
    ('evaluating', 'persisting-artifacts'),
    ('persisting-artifacts', 'completed'),
    ('queued', 'cancelled'),
    ('preparing-dataset', 'cancelling'),
    ('training', 'cancelling'),
    ('cancelling', 'cancelled'),
    ('queued', 'failed'),
    ('evaluating', 'failed'),
])
def test_training_state_machine_accepts_documented_transitions(current: str, next_status: str) -> None:
    assert transition_training_status(TrainingJobStatus(current), TrainingJobStatus(next_status)) is TrainingJobStatus(next_status)


@pytest.mark.parametrize('terminal', ['completed', 'failed', 'cancelled'])
@pytest.mark.parametrize('next_status', list(TrainingJobStatus))
def test_training_terminal_states_reject_every_transition(terminal: str, next_status: TrainingJobStatus) -> None:
    with pytest.raises(InvalidTrainingTransition, match='terminal'):
        transition_training_status(TrainingJobStatus(terminal), next_status)


def test_training_state_machine_rejects_skipped_or_reversed_stages() -> None:
    for current, next_status in (
        ('queued', 'training'), ('training', 'validating'), ('cancelling', 'completed'),
    ):
        with pytest.raises(InvalidTrainingTransition, match=f'{current} -> {next_status}'):
            transition_training_status(TrainingJobStatus(current), TrainingJobStatus(next_status))


def test_dataset_binding_and_progress_are_immutable_and_bounded() -> None:
    binding = DatasetBinding(dataset_id='cat-dog', version='sha256:' + 'a' * 64)
    progress = TrainingProgress(stage=TrainingJobStatus.TRAINING, processed_units=5, total_units=10, message='Fitting model')

    assert binding.version.endswith('a' * 64)
    assert progress.fraction == 0.5
    with pytest.raises((AttributeError, TypeError)):
        binding.dataset_id = 'changed'  # type: ignore[misc]
    with pytest.raises(ValueError, match='cannot exceed'):
        TrainingProgress(stage=TrainingJobStatus.TRAINING, processed_units=11, total_units=10)
    with pytest.raises(ValueError, match='immutable SHA-256'):
        DatasetBinding(dataset_id='cat-dog', version='latest')