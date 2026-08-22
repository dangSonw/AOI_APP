import pytest

from app.services.deep_learning_contract import validate_external_artifact_contract


def _contract() -> dict:
    return {
        'format': 'onnx',
        'runtime': 'onnxruntime',
        'runtime_version': '1.18.0',
        'input_schema': [{'name': 'image', 'dtype': 'float32', 'shape': [1, 3, 224, 224]}],
        'output_schema': [{'name': 'scores', 'dtype': 'float32', 'shape': [1, 2]}],
        'preprocessing': {'channelOrder': 'RGB'},
        'postprocessing': {'kind': 'classification'},
    }


def test_external_contract_is_normalized_and_preserves_tensor_schema() -> None:
    contract = validate_external_artifact_contract(_contract())

    assert contract['format'] == 'onnx'
    assert contract['inputSchema'][0]['shape'] == [1, 3, 224, 224]


@pytest.mark.parametrize('field,value', [
    ('format', 'pytorch'),
    ('runtime', 'torch'),
    ('input_schema', []),
    ('output_schema', [{'name': 'scores', 'dtype': 'float32', 'shape': [1]}, {'name': 'scores', 'dtype': 'float32', 'shape': [1]}]),
])
def test_external_contract_rejects_unsupported_or_ambiguous_schema(field: str, value: object) -> None:
    payload = _contract()
    payload[field] = value

    with pytest.raises(ValueError):
        validate_external_artifact_contract(payload)