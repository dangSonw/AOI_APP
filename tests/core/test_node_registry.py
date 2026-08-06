import pytest

from core.algorithms import get_algorithm_catalog
from core.nodes import NodeNotImplementedError, NodeUse, get_node_registry


def test_every_catalog_definition_has_one_runtime_package() -> None:
    catalog = get_algorithm_catalog()
    registry = get_node_registry()

    assert len(registry) == len(catalog) == 58
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