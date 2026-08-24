import asyncio
import base64
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services import dataset_service
from app.services.training_dataset_resolver import (
    DatasetIntegrityError, create_immutable_dataset_version, resolve_immutable_dataset,
)
from core.training.contracts import DatasetBinding


PNG_BYTES = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
)


@pytest.fixture
def dataset_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    roots = SimpleNamespace(
        datasets_data_path=tmp_path / 'datasets',
        captures_data_path=tmp_path / 'captures',
    )
    monkeypatch.setattr(dataset_service, 'get_settings', lambda: roots)
    dataset_service.create_dataset('cat-dog')
    dataset_service.create_category('cat-dog', 'cats')
    dataset_service.create_category('cat-dog', 'dogs')
    for category, filename in [('cats', 'cat.png'), ('dogs', 'dog.png')]:
        upload = dataset_service.UploadFile(filename=filename, file=dataset_service.BytesIO(PNG_BYTES))
        asyncio.run(dataset_service.upload_images('cat-dog', category, [upload]))
    return roots.datasets_data_path / 'cat-dog'


def test_snapshot_and_resolve_preserve_class_mapping_split_and_private_paths(dataset_root: Path) -> None:
    binding = create_immutable_dataset_version(
        'cat-dog',
        class_mapping={'cats': 0, 'dogs': 1},
        split_by_item={'cats/cat.png': 'train', 'dogs/dog.png': 'test'},
    )

    handle = resolve_immutable_dataset(binding)

    assert binding.version.startswith('sha256:')
    assert handle.dataset_id == 'cat-dog'
    assert handle.class_mapping == {'cats': 0, 'dogs': 1}
    assert [(item.logical_path, item.class_id, item.split) for item in handle.items] == [
        ('cats/cat.png', 0, 'train'), ('dogs/dog.png', 1, 'test'),
    ]
    assert all(item.path.is_file() and '.versions' in item.path.parts for item in handle.items)
    assert 'path' not in handle.public_metadata()
    assert all('path' not in item for item in handle.public_metadata()['items'])


def test_snapshot_is_stable_and_unchanged_when_live_dataset_mutates(dataset_root: Path) -> None:
    first = create_immutable_dataset_version('cat-dog')
    same = create_immutable_dataset_version('cat-dog')
    (dataset_root / 'cats' / 'cat.png').write_bytes(PNG_BYTES + b'changed')

    changed = create_immutable_dataset_version('cat-dog')
    old_handle = resolve_immutable_dataset(first)

    assert same == first
    assert changed.version != first.version
    assert old_handle.items[0].path.read_bytes() == PNG_BYTES


@pytest.mark.parametrize('version', ['latest', 'sha256:' + '0' * 64])
def test_resolver_rejects_mutable_or_missing_versions(dataset_root: Path, version: str) -> None:
    del dataset_root
    binding = DatasetBinding.__new__(DatasetBinding)
    object.__setattr__(binding, 'dataset_id', 'cat-dog')
    object.__setattr__(binding, 'version', version)

    with pytest.raises((ValueError, FileNotFoundError), match='immutable SHA-256|does not exist'):
        resolve_immutable_dataset(binding)


def test_resolver_rejects_manifest_and_content_mismatch(dataset_root: Path) -> None:
    binding = create_immutable_dataset_version('cat-dog')
    version_dir = dataset_root / '.versions' / binding.version.removeprefix('sha256:')
    manifest_path = version_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['classMapping'] = {'cats': 1, 'dogs': 0}
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(DatasetIntegrityError, match='manifest hash'):
        resolve_immutable_dataset(binding)

    binding = create_immutable_dataset_version('cat-dog')
    version_dir = dataset_root / '.versions' / binding.version.removeprefix('sha256:')
    (version_dir / 'items' / 'cats' / 'cat.png').write_bytes(b'tampered')
    with pytest.raises(DatasetIntegrityError, match='checksum'):
        resolve_immutable_dataset(binding)


def test_resolver_rejects_path_traversal_in_manifest(dataset_root: Path) -> None:
    binding = create_immutable_dataset_version('cat-dog')
    version_dir = dataset_root / '.versions' / binding.version.removeprefix('sha256:')
    manifest_path = version_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['items'][0]['logicalPath'] = '../outside.png'
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(DatasetIntegrityError, match='logical path'):
        resolve_immutable_dataset(binding, verify_manifest_hash=False)


def test_snapshot_rejects_invalid_class_or_split_metadata(dataset_root: Path) -> None:
    del dataset_root
    with pytest.raises(ValueError, match='Class mapping'):
        create_immutable_dataset_version('cat-dog', class_mapping={'cats': 0})
    with pytest.raises(ValueError, match='split metadata'):
        create_immutable_dataset_version('cat-dog', split_by_item={'cats/cat.png': 'train'})
    with pytest.raises(ValueError, match='Unsupported split'):
        create_immutable_dataset_version(
            'cat-dog', split_by_item={'cats/cat.png': 'train', 'dogs/dog.png': 'holdout'},
        )


def test_snapshot_enforces_item_pixel_and_media_bounds(dataset_root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr('app.services.training_dataset_resolver.MAX_DATASET_ITEMS', 1)
    with pytest.raises(ValueError, match='item limit'):
        create_immutable_dataset_version('cat-dog')

    monkeypatch.setattr('app.services.training_dataset_resolver.MAX_DATASET_ITEMS', 10)
    monkeypatch.setattr('app.services.training_dataset_resolver.MAX_DECODED_PIXELS', 1)
    with pytest.raises(ValueError, match='decoded-pixel limit'):
        create_immutable_dataset_version('cat-dog')

    monkeypatch.setattr('app.services.training_dataset_resolver.MAX_DECODED_PIXELS', 10)
    (dataset_root / 'cats' / 'cat.png').write_bytes(b'BM' + b'\x00' * 30)
    with pytest.raises(ValueError, match='dimensions|media type'):
        create_immutable_dataset_version('cat-dog')


def test_snapshot_ignores_reserved_dataset_service_directories(dataset_root: Path) -> None:
    (dataset_root / 'preparations').mkdir()
    (dataset_root / 'artifacts').mkdir()
    (dataset_root / 'training-jobs').mkdir()

    handle = resolve_immutable_dataset(create_immutable_dataset_version('cat-dog'))

    assert handle.class_mapping == {'cats': 0, 'dogs': 1}


def test_resolver_normalizes_malformed_manifest_metadata(dataset_root: Path) -> None:
    binding = create_immutable_dataset_version('cat-dog')
    version_dir = dataset_root / '.versions' / binding.version.removeprefix('sha256:')
    manifest_path = version_dir / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['items'][0]['widthPx'] = {'invalid': True}
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(DatasetIntegrityError, match='metadata is malformed'):
        resolve_immutable_dataset(binding, verify_manifest_hash=False)