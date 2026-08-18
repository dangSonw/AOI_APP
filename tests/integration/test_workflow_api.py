from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api.workflows import get_workflow_repository
from app.auth.dependencies import get_current_user
from app.main import app
from app.services.workflow_repository import WorkflowRepository
from core.pipeline import create_default_workflow


@pytest.fixture
def client(tmp_path: Path):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, is_active=True)
    app.dependency_overrides[get_workflow_repository] = lambda: WorkflowRepository(tmp_path)
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def default_payload() -> dict[str, object]:
    from app.schemas.workflow import WorkflowSchema

    return WorkflowSchema.from_core(create_default_workflow()).model_dump(mode='json', by_alias=True)


def test_workflow_endpoints_require_authentication() -> None:
    with TestClient(app) as anonymous_client:
        assert anonymous_client.get('/api/algorithms').status_code == 401
        assert anonymous_client.get('/api/recipes/rev-c-mainboard/workflow').status_code == 401


def test_catalog_and_missing_workflow_are_returned_in_camel_case(client: TestClient) -> None:
    catalog_response = client.get('/api/algorithms')
    workflow_response = client.get('/api/recipes/rev-c-mainboard/workflow')

    assert catalog_response.status_code == 200
    assert len(catalog_response.json()) == 99
    assert catalog_response.json()[0]['availability'] == 'configuration-only'
    assert catalog_response.json()[0]['use'] == 'debug'
    assert catalog_response.json()[0]['outputs'][0]['dataType'] == 'image'
    assert workflow_response.status_code == 200
    assert workflow_response.json()['recipeSlug'] == 'rev-c-mainboard'
    assert workflow_response.json()['revision'] == 0


def test_algorithm_documentation_is_returned_in_requested_language(client: TestClient) -> None:
    vietnamese_response = client.get('/api/algorithms/camera-capture/documentation?language=vi')
    english_response = client.get('/api/algorithms/camera-capture/documentation?language=en')
    missing_response = client.get('/api/algorithms/not-a-node/documentation?language=vi')

    assert vietnamese_response.status_code == 200
    assert vietnamese_response.json()['algorithmId'] == 'camera-capture'
    assert vietnamese_response.json()['language'] == 'vi'
    assert '# Node Camera capture' in vietnamese_response.json()['content']
    assert '## Mục đích và cách dùng nhanh' in vietnamese_response.json()['content']
    assert english_response.status_code == 200
    assert english_response.json()['language'] == 'en'
    assert '## Purpose and quick use' in english_response.json()['content']
    assert missing_response.status_code == 404


def test_save_increments_revision_and_rejects_stale_payload(client: TestClient) -> None:
    payload = default_payload()

    saved_response = client.put('/api/recipes/rev-c-mainboard/workflow', json=payload)
    stale_response = client.put('/api/recipes/rev-c-mainboard/workflow', json=payload)

    assert saved_response.status_code == 200
    assert saved_response.json()['revision'] == 1
    assert stale_response.status_code == 409
    assert 'updated by another request' in stale_response.json()['detail']


def test_invalid_graph_returns_structured_issues(client: TestClient) -> None:
    payload = default_payload()
    payload['connections'][0]['targetPortId'] = 'missing-port'  # type: ignore[index]

    response = client.put('/api/recipes/rev-c-mainboard/workflow', json=payload)

    assert response.status_code == 422
    assert response.json()['detail'][0]['code'] == 'unknown-port'
    assert response.json()['detail'][0]['connectionId'] == payload['connections'][0]['id']  # type: ignore[index]


def test_control_connection_requires_persisted_kind(client: TestClient) -> None:
    payload = default_payload()
    connections: list[dict[str, object]] = payload['connections']  # type: ignore[assignment]
    control_ids = [str(connection['id']) for connection in connections if connection.get('kind') == 'control']
    for connection in connections:
        if connection.get('kind') == 'control':
            del connection['kind']

    rejected = client.put('/api/recipes/rev-c-mainboard/workflow', json=payload)

    assert rejected.status_code == 422
    issues = rejected.json()['detail']
    port_issues = [item for item in issues if item['code'] == 'unknown-port']
    assert {item['connectionId'] for item in port_issues} == set(control_ids)
    assert port_issues[0]['message'] == 'Data connections require data output and input ports.'
    assert all(item['code'] in {'unknown-port', 'cycle', 'dependency-order'} for item in issues)

    accepted = client.put('/api/recipes/rev-c-mainboard/workflow', json=default_payload())

    assert accepted.status_code == 200
    assert {str(connection['kind']) for connection in accepted.json()['connections']} == {'data', 'control'}


def test_invalid_slug_and_body_slug_mismatch_return_422(client: TestClient) -> None:
    invalid_slug = client.get('/api/recipes/Rev-C/workflow')
    payload = default_payload()
    mismatch = client.put('/api/recipes/other-recipe/workflow', json=payload)

    assert invalid_slug.status_code == 422
    assert mismatch.status_code == 422


def test_invalid_persisted_data_returns_service_unavailable(client: TestClient, tmp_path: Path) -> None:
    workflow_path = tmp_path / 'rev-c-mainboard' / 'workflow.json'
    workflow_path.parent.mkdir(parents=True)
    workflow_path.write_text('{broken', encoding='utf-8')

    response = client.get('/api/recipes/rev-c-mainboard/workflow')

    assert response.status_code == 503
    assert '/home/' not in response.json()['detail']