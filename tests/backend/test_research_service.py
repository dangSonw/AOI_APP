from pathlib import Path

import pytest


def test_artifact_store_is_content_addressed_and_checksum_verified(tmp_path: Path) -> None:
    from app.services.research_service import ArtifactStore, ArtifactIntegrityError

    store = ArtifactStore(tmp_path)
    first = store.put_bytes(b'model-weights', media_type='application/octet-stream')
    second = store.put_bytes(b'model-weights', media_type='application/octet-stream')

    assert first.sha256 == second.sha256
    assert first.storage_uri == second.storage_uri
    assert store.read_verified(first) == b'model-weights'
    Path(first.storage_uri).write_bytes(b'corrupt')
    with pytest.raises(ArtifactIntegrityError):
        store.read_verified(first)


def test_reproducibility_manifest_records_complete_execution_inputs() -> None:
    from app.services.research_service import ResearchRunRecord, build_reproducibility_manifest

    run = ResearchRunRecord(
        run_id='run-01', experiment_id='experiment-01', code_revision='9ae70df',
        node_versions={'patchcore': '1.0.0'}, environment={'python': '3.12'},
        random_seeds={'python': 42, 'numpy': 42}, resources={'cpuCores': 4},
        dataset_versions={'pcb-train': 'sha256:' + 'a' * 64},
        parameters={'memoryBankSize': 10000}, metrics={'auroc': 0.98},
        output_artifacts={'weights': 'sha256:' + 'b' * 64}, status='completed', error=None,
    )

    manifest = build_reproducibility_manifest(run)

    assert manifest['codeRevision'] == '9ae70df'
    assert manifest['nodeVersions'] == {'patchcore': '1.0.0'}
    assert manifest['datasetVersions']['pcb-train'].endswith('a' * 64)
    assert manifest['randomSeeds']['numpy'] == 42
    assert manifest['outputArtifacts']['weights'].endswith('b' * 64)


def test_model_promotion_requires_validation_and_is_reversible() -> None:
    from app.services.research_service import ModelRegistry, PromotionRejected

    registry = ModelRegistry()
    version_1 = registry.register_version('pcb-anomaly', run_id='run-01', artifact_sha256='a' * 64)
    version_2 = registry.register_version('pcb-anomaly', run_id='run-02', artifact_sha256='b' * 64)

    with pytest.raises(PromotionRejected):
        registry.promote('pcb-anomaly', 'champion', version_1.version, actor_id=1, reason='No evidence', validation_passed=False)

    first = registry.promote('pcb-anomaly', 'champion', version_1.version, actor_id=1, reason='Validated baseline', validation_passed=True)
    second = registry.promote('pcb-anomaly', 'champion', version_2.version, actor_id=1, reason='Higher AUROC', validation_passed=True)
    rollback = registry.rollback('pcb-anomaly', 'champion', actor_id=1, reason='Pilot regression')

    assert first.previous_version is None
    assert second.previous_version == version_1.version
    assert rollback.next_version == version_1.version
    assert [event.action for event in registry.events] == ['promote', 'promote', 'rollback']


def test_production_binding_resolves_alias_to_immutable_model_version() -> None:
    from app.services.research_service import ModelRegistry, resolve_production_bindings

    registry = ModelRegistry()
    version = registry.register_version('pcb-anomaly', run_id='run-01', artifact_sha256='a' * 64)
    registry.promote('pcb-anomaly', 'champion', version.version, actor_id=1, reason='Validated', validation_passed=True)

    resolved = resolve_production_bindings(
        {'model': {'modelName': 'pcb-anomaly', 'alias': 'champion'}, 'threshold': 0.8}, registry,
    )

    assert resolved == {'model': {'modelName': 'pcb-anomaly', 'modelVersion': 1, 'artifactSha256': 'a' * 64}, 'threshold': 0.8}


def test_job_spec_keeps_execution_location_outside_node_contract() -> None:
    from app.services.research_service import ResearchJobSpec

    spec = ResearchJobSpec(run_id='run-01', node_id='patchcore', execution_target='local-gpu', payload={'seed': 42})

    assert spec.execution_target == 'local-gpu'
    assert spec.payload == {'seed': 42}
