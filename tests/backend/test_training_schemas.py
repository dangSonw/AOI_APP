import pytest
from pydantic import ValidationError

from app.schemas.training import DatasetBindingSchema, TrainingJobCreate, TrainingJobResponse


def valid_training_request() -> dict[str, object]:
    return {
        'experimentId': 'cat-dog-svm',
        'recipeSlug': 'rev-c-mainboard',
        'workflowRevision': 4,
        'nodeInstanceId': 'node-svm-01',
        'nodeId': 'svm-image-classifier',
        'nodePackageVersion': '1.0.0',
        'executionTarget': 'local-cpu',
        'datasetBindings': {
            'training-dataset': {'datasetId': 'cat-dog', 'version': 'sha256:' + 'a' * 64},
        },
        'parameters': {'kernel': 'rbf', 'c': 10},
        'randomSeeds': {'python': 42, 'numpy': 42},
    }


def test_training_job_create_accepts_only_client_intent() -> None:
    request = TrainingJobCreate.model_validate(valid_training_request())

    assert request.workflow_revision == 4
    assert request.dataset_bindings['training-dataset'] == DatasetBindingSchema(
        dataset_id='cat-dog', version='sha256:' + 'a' * 64,
    )


@pytest.mark.parametrize('platform_field', [
    'status', 'metrics', 'outputArtifacts', 'environment', 'codeRevision', 'error', 'progress',
])
def test_training_job_create_rejects_platform_owned_fields(platform_field: str) -> None:
    payload = {**valid_training_request(), platform_field: {}}

    with pytest.raises(ValidationError, match='Extra inputs are not permitted'):
        TrainingJobCreate.model_validate(payload)


def test_training_job_create_rejects_mutable_dataset_and_empty_target() -> None:
    payload = valid_training_request()
    payload['datasetBindings'] = {'training-dataset': {'datasetId': 'cat-dog', 'version': 'latest'}}
    with pytest.raises(ValidationError, match='immutable SHA-256'):
        TrainingJobCreate.model_validate(payload)

    payload = {**valid_training_request(), 'executionTarget': ''}
    with pytest.raises(ValidationError):
        TrainingJobCreate.model_validate(payload)


def test_training_job_response_exposes_server_owned_lineage() -> None:
    fields = TrainingJobResponse.model_fields
    assert {'status', 'progress', 'code_revision', 'environment', 'metrics', 'output_artifacts', 'parent_run_id'} <= set(fields)