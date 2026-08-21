import pytest
from pathlib import Path

from core.algorithms import get_algorithm_catalog
from core.nodes import NodeNotImplementedError, NodeUse, get_node_registry


def test_every_catalog_definition_has_one_runtime_package() -> None:
    catalog = get_algorithm_catalog()
    registry = get_node_registry()

    assert len(registry) == len(catalog) == 102
    assert set(registry) == {definition.id for definition in catalog}


def test_runtime_contracts_match_catalog_ports() -> None:
    definitions = {definition.id: definition for definition in get_algorithm_catalog()}

    for node_id, runtime in get_node_registry().items():
        definition = definitions[node_id]
        assert runtime.use in set(NodeUse)
        assert runtime.input_keys == tuple(port.key for port in definition.inputs)
        assert runtime.output_keys == tuple(port.key for port in definition.outputs)
        assert runtime.input_count == len(definition.inputs)
        assert runtime.output_count == len(definition.outputs)


def test_placeholder_runtime_has_an_explicit_entry_point() -> None:
    runtime = get_node_registry()['patchcore']

    with pytest.raises(NodeNotImplementedError, match='patchcore'):
        runtime.execute({'image': object()}, {'memoryBankSize': 10_000})

def test_every_runtime_package_owns_one_versioned_manifest() -> None:
    from core.nodes.registry import get_node_manifest_registry

    manifests = get_node_manifest_registry()

    assert len(manifests) == 102
    assert set(manifests) == set(get_node_registry())
    assert all(manifest.manifest_version == 1 for manifest in manifests.values())
    assert all(manifest.execution_target in {'local-cpu', 'local-gpu', 'adapter'} for manifest in manifests.values())


def test_manifest_and_runtime_contracts_cannot_drift() -> None:
    from core.nodes.registry import get_node_manifest_registry

    manifests = get_node_manifest_registry()
    for node_id, runtime in get_node_registry().items():
        manifest = manifests[node_id]
        assert runtime.input_keys == tuple(port.key for port in manifest.definition.inputs)
        assert runtime.output_keys == tuple(port.key for port in manifest.definition.outputs)
        assert runtime.use == manifest.use


def test_manifest_catalog_projection_has_no_monolithic_definition_table() -> None:
    from core.algorithms.catalog import get_algorithm_catalog
    from core.nodes.registry import get_node_manifest_registry

    catalog = get_algorithm_catalog()
    manifests = get_node_manifest_registry()

    assert catalog == tuple(manifest.definition for manifest in sorted(manifests.values(), key=lambda item: item.catalog_order))


def test_production_workflow_rejects_test_or_unsupported_runtimes() -> None:
    from core.nodes.registry import validate_node_runtime_support

    assert validate_node_runtime_support('patchcore', deployment_mode='production') == (
        'Node patchcore uses a test runtime and cannot run in production.',
    )
    assert validate_node_runtime_support('patchcore', deployment_mode='research') == ()
    assert validate_node_runtime_support('does-not-exist', deployment_mode='production') == (
        'Node does-not-exist is not registered.',
    )
    for node_id in (
        'kmeans-image-segmentation', 'nearest-centroid-object-classifier',
        'gaussian-naive-bayes-object-classifier', 'pca-anomaly-detector',
        'logistic-object-classifier',
    ):
        assert validate_node_runtime_support(node_id, deployment_mode='production') == (
            f'Node {node_id} uses a debug runtime and cannot run in production.',
        )


def test_every_node_package_has_english_and_vietnamese_documentation() -> None:
    nodes_root = Path('core/nodes')
    package_directories = {path.parent for path in nodes_root.glob('*/*/manifest.json')}

    assert len(package_directories) == 102
    assert all((directory / 'README.md').is_file() for directory in package_directories)
    assert all((directory / 'README.md.vn').is_file() for directory in package_directories)
