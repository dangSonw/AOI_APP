import base64
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile
from io import BytesIO

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.main import app
from app.services import dataset_service


PNG_BYTES = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
)


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    roots = SimpleNamespace(
        datasets_data_path=tmp_path / 'datasets',
        captures_data_path=tmp_path / 'captures',
    )
    monkeypatch.setattr(dataset_service, 'get_settings', lambda: roots)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=1, is_active=True)
    try:
        with TestClient(app) as test_client:
            yield test_client, roots
    finally:
        app.dependency_overrides.clear()


def test_dataset_endpoints_require_authentication() -> None:
    with TestClient(app) as anonymous_client:
        assert anonymous_client.get('/api/datasets').status_code == 401


@pytest.mark.parametrize('name', ('../dataset', 'Dataset', 'dataset_name', '-dataset'))
def test_dataset_endpoint_rejects_invalid_names(client, name: str) -> None:
    test_client, _ = client
    assert test_client.post('/api/datasets', json={'name': name}).status_code == 422


def test_dataset_category_and_image_endpoints_round_trip(client) -> None:
    test_client, _ = client

    created = test_client.post('/api/datasets', json={'name': 'pcb-training', 'description': 'Training set'})
    listed = test_client.get('/api/datasets')
    detailed = test_client.get('/api/datasets/pcb-training')
    category = test_client.post('/api/datasets/pcb-training/categories', json={'name': 'incoming'})
    test_client.post('/api/datasets/pcb-training/categories', json={'name': 'accepted'})
    uploaded = test_client.post(
        '/api/datasets/pcb-training/categories/incoming/images',
        files=[('files', ('board.png', PNG_BYTES, 'image/png'))],
    )
    images = test_client.get('/api/datasets/pcb-training/categories/incoming/images')
    renamed = test_client.patch(
        '/api/datasets/pcb-training/categories/incoming/images/board.png',
        json={'newFilename': 'board-pass.png'},
    )
    moved = test_client.post(
        '/api/datasets/pcb-training/categories/incoming/images/board-pass.png/move',
        json={'targetCategory': 'accepted'},
    )
    deleted_image = test_client.delete('/api/datasets/pcb-training/categories/accepted/images/board-pass.png')
    renamed_category = test_client.put(
        '/api/datasets/pcb-training/categories/incoming',
        json={'newName': 'review'},
    )
    deleted_category = test_client.delete('/api/datasets/pcb-training/categories/review')
    updated = test_client.put(
        '/api/datasets/pcb-training',
        json={'newName': 'pcb-validation', 'description': 'Validation set'},
    )
    deleted_dataset = test_client.delete('/api/datasets/pcb-validation')

    assert created.status_code == 201
    assert listed.json()['datasets'][0]['name'] == 'pcb-training'
    assert detailed.json()['description'] == 'Training set'
    assert category.status_code == 201
    assert uploaded.status_code == 201
    assert images.json()['images'][0]['filename'] == 'board.png'
    assert renamed.json()['filename'] == 'board-pass.png'
    assert moved.json()['filename'] == 'board-pass.png'
    assert deleted_image.status_code == 204
    assert renamed_category.status_code == 200
    assert deleted_category.status_code == 200
    assert updated.json()['name'] == 'pcb-validation'
    assert deleted_dataset.status_code == 204


def test_capture_import_and_export_use_safe_relative_paths(client) -> None:
    test_client, roots = client
    capture = roots.captures_data_path / 'run-01' / 'capture.png'
    capture.parent.mkdir(parents=True)
    capture.write_bytes(PNG_BYTES)
    test_client.post('/api/datasets', json={'name': 'pcb-training'})
    test_client.post('/api/datasets/pcb-training/categories', json={'name': 'incoming'})

    imported = test_client.post(
        '/api/datasets/pcb-training/import-captures',
        json={'filenames': ['run-01/capture.png'], 'targetCategory': 'incoming'},
    )
    traversal = test_client.post(
        '/api/datasets/pcb-training/import-captures',
        json={'filenames': ['../outside.png'], 'targetCategory': 'incoming'},
    )
    exported = test_client.get('/api/datasets/pcb-training/export')

    assert imported.status_code == 200
    assert imported.json()['images'][0]['filename'] == 'capture.png'
    assert traversal.status_code == 422
    assert exported.status_code == 200
    assert exported.headers['content-type'] == 'application/zip'
    with ZipFile(BytesIO(exported.content)) as archive:
        assert archive.namelist() == ['incoming/capture.png']