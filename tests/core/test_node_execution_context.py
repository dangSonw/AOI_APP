import hashlib
from itertools import count

import pytest


def _artifact_binding(content: bytes):
    from core.nodes import ArtifactBinding

    return ArtifactBinding(
        sha256=hashlib.sha256(content).hexdigest(),
        media_type='application/x-numpy',
        byte_length=len(content),
    )


def test_context_resolves_artifact_bytes_and_verifies_immutable_record() -> None:
    from core.nodes import NodeArtifactIntegrityError, NodeExecutionContext

    content = b'golden-reference-array'
    binding = _artifact_binding(content)
    resolved_bindings = []
    context = NodeExecutionContext(
        artifacts={'golden': binding},
        resolve_artifact=lambda requested: resolved_bindings.append(requested) or content,
    )

    assert context.read_artifact('golden', expected_media_types=('application/x-numpy',)) == content
    assert resolved_bindings == [binding]

    corrupt_context = NodeExecutionContext(
        artifacts={'golden': binding},
        resolve_artifact=lambda _: b'corrupt',
    )
    with pytest.raises(NodeArtifactIntegrityError, match='checksum or byte length'):
        corrupt_context.read_artifact('golden')


def test_artifact_binding_rejects_filesystem_location_fields() -> None:
    from core.nodes import ArtifactBinding

    with pytest.raises(ValueError, match='immutable artifact fields'):
        ArtifactBinding.from_mapping({
            'artifactSha256': 'a' * 64,
            'mediaType': 'application/octet-stream',
            'byteLength': 1,
            'storageUri': '/tmp/untrusted-model.pt',
        })


def test_model_binding_requires_published_version_and_rejects_alias() -> None:
    from core.nodes import ModelBinding

    binding = ModelBinding.from_mapping({
        'modelName': 'pcb-anomaly',
        'modelVersion': 3,
        'artifactSha256': 'a' * 64,
    })

    assert binding.model_name == 'pcb-anomaly'
    assert binding.model_version == 3
    assert binding.artifact_sha256 == 'a' * 64

    with pytest.raises(ValueError, match='immutable model fields'):
        ModelBinding.from_mapping({'modelName': 'pcb-anomaly', 'alias': 'champion'})


def test_context_bindings_are_read_only_and_cancellation_is_typed() -> None:
    from core.nodes import ModelBinding, NodeExecutionCancelled, NodeExecutionContext

    models = {
        'detector': ModelBinding('pcb-anomaly', 1, 'a' * 64),
    }
    context = NodeExecutionContext(models=models, is_cancelled=lambda: True)
    models.clear()

    assert context.models['detector'].model_version == 1
    with pytest.raises(TypeError):
        context.models['other'] = ModelBinding('other', 1, 'b' * 64)  # type: ignore[index]
    with pytest.raises(NodeExecutionCancelled):
        context.checkpoint()


def test_runtime_invoke_preserves_legacy_executor_and_dispatches_contextual_executor() -> None:
    from core.nodes import NodeExecutionContext, NodeRuntime, NodeUse

    calls = []

    def legacy(inputs, parameters):
        calls.append(('legacy', inputs, parameters))
        return {'value': 1}

    legacy_runtime = NodeRuntime('legacy', NodeUse.DEBUG, (), ('value',), legacy)
    assert legacy_runtime.invoke({}, {}) == {'value': 1}

    def contextual(inputs, parameters, context):
        calls.append(('contextual', inputs, parameters, context.device.value))
        return {'value': 2}

    contextual_runtime = NodeRuntime(
        'contextual', NodeUse.DEBUG, (), ('value',), legacy,
        execute_with_context=contextual,
    )
    assert contextual_runtime.invoke({}, {}) == {'value': 1}
    assert contextual_runtime.invoke({}, {}, context=NodeExecutionContext()) == {'value': 2}
    assert [call[0] for call in calls] == ['legacy', 'legacy', 'contextual']


def test_delay_checks_cancellation_during_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.nodes import NodeExecutionCancelled, NodeExecutionContext, get_node_runtime

    probes = count()
    monkeypatch.setattr('time.sleep', lambda _: None)
    runtime = get_node_runtime('delay')
    assert runtime is not None

    with pytest.raises(NodeExecutionCancelled):
        runtime.invoke(
            {'image': object()}, {'milliseconds': 1000},
            context=NodeExecutionContext(is_cancelled=lambda: next(probes) >= 2),
        )