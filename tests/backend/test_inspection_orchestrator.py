from datetime import datetime, timedelta, timezone

import pytest


def valid_input():
    from app.services.inspection_orchestrator import InspectionInput
    return InspectionInput(
        artifact_sha256='a' * 64, observed_sha256='a' * 64, byte_length=1024,
        is_blurred=False, is_registered=True, motion_in_position=True,
        pose_observed_at=datetime.now(timezone.utc), pose_tolerance_seconds=1.0,
        reference_score=0.25,
    )


@pytest.mark.parametrize('mutation,code', [
    ({'observed_sha256': 'b' * 64}, 'checksum-invalid'),
    ({'is_blurred': True}, 'blurred'),
    ({'is_registered': False}, 'unregistered'),
    ({'motion_in_position': False}, 'motion-not-in-position'),
    ({'byte_length': 0}, 'corrupt'),
])
def test_unsafe_inputs_never_produce_pass(mutation, code) -> None:
    from dataclasses import replace
    from app.services.inspection_orchestrator import InspectionOrchestrator

    outcome = InspectionOrchestrator().run_reference_slice(replace(valid_input(), **mutation), threshold=0.5)

    assert outcome.decision == 'FAULT'
    assert outcome.error_code == code


def test_stale_pose_never_produces_pass() -> None:
    from dataclasses import replace
    from app.services.inspection_orchestrator import InspectionOrchestrator

    stale = replace(valid_input(), pose_observed_at=datetime.now(timezone.utc) - timedelta(seconds=5))
    outcome = InspectionOrchestrator().run_reference_slice(stale, threshold=0.5)

    assert outcome.decision == 'FAULT'
    assert outcome.error_code == 'stale-pose'


def test_typed_context_enforces_cancel_timeout_and_resources() -> None:
    from app.services.inspection_orchestrator import CancellationToken, ExecutionContext, InspectionCancelled, InspectionTimedOut

    cancelled = CancellationToken(cancelled=True)
    context = ExecutionContext(run_id='run-01', node_id='absolute-difference', deadline=datetime.now(timezone.utc) + timedelta(seconds=1), cancellation=cancelled, resources={'cpuCores': 1})
    with pytest.raises(InspectionCancelled):
        context.checkpoint()

    timed_out = ExecutionContext(run_id='run-02', node_id='absolute-difference', deadline=datetime.now(timezone.utc) - timedelta(seconds=1), cancellation=CancellationToken(), resources={'cpuCores': 1})
    with pytest.raises(InspectionTimedOut):
        timed_out.checkpoint()


def test_restart_recovery_faults_incomplete_runs_without_resuming_motion() -> None:
    from app.services.inspection_orchestrator import recover_interrupted_status

    assert recover_interrupted_status('moving') == ('faulted', 'restart-during-physical-operation')
    assert recover_interrupted_status('capturing') == ('faulted', 'restart-during-physical-operation')
    assert recover_interrupted_status('queued') == ('cancelled', 'restart-before-execution')
    assert recover_interrupted_status('completed') == ('completed', None)


def test_one_thousand_deterministic_runs_have_identical_artifact_and_decision() -> None:
    from app.services.inspection_orchestrator import InspectionOrchestrator

    orchestrator = InspectionOrchestrator()
    outcomes = [orchestrator.run_reference_slice(valid_input(), threshold=0.5) for _ in range(1000)]

    assert {outcome.decision for outcome in outcomes} == {'PASS'}
    assert len({outcome.evidence_sha256 for outcome in outcomes}) == 1
    assert all(outcome.node_runs[0].status == 'completed' for outcome in outcomes)


def test_legacy_reference_version_remains_replayable_after_pixel_scoring_release() -> None:
    from app.services.inspection_orchestrator import InspectionOrchestrator

    orchestrator = InspectionOrchestrator()
    legacy = orchestrator.run_reference_slice(valid_input(), threshold=0.5, algorithm_version='1.0.0')
    current = orchestrator.run_reference_slice(valid_input(), threshold=0.5, algorithm_version='2.0.0')

    assert legacy.evidence_sha256 != current.evidence_sha256
    assert orchestrator.run_reference_slice(
        valid_input(), threshold=0.5, algorithm_version='1.0.0',
    ).evidence_sha256 == legacy.evidence_sha256
