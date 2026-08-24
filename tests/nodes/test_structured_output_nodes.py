import pytest
from core.nodes import get_node_manifest_registry, get_node_registry

def test_structured_output_nodes_validate_and_normalize_payloads() -> None:
    manifests = get_node_manifest_registry(); runtimes = get_node_registry()
    assert manifests['plot-2d-output'].definition.capabilities == ('plot-2d-preview',)
    assert manifests['table-output'].definition.capabilities == ('table-preview',)
    confusion = {'schema': 'aoi.confusion-matrix.v1', 'labels': ['a'], 'matrix': [[2]]}
    table = {'schema': 'aoi.table.v1', 'columns': [{'key': 'x', 'label': 'X', 'type': 'number'}], 'rows': [{'x': 1.0}]}
    assert runtimes['plot-2d-output'].execute({'payload': confusion}, {})['validated-payload'] == confusion
    assert runtimes['table-output'].execute({'payload': table}, {})['validated-payload'] == table
    with pytest.raises(ValueError): runtimes['plot-2d-output'].execute({'payload': table}, {})
    with pytest.raises(ValueError): runtimes['table-output'].execute({'payload': confusion}, {})