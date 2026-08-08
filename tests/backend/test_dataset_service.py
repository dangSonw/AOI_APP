import asyncio
import base64
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
from fastapi import UploadFile

from app.services import dataset_service


PNG_BYTES = base64.b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII='
)


@pytest.fixture
def data_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    roots = SimpleNamespace(
        datasets_data_path=tmp_path / 'datasets',
        captures_data_path=tmp_path / 'captures',
    )
    monkeypatch.setattr(dataset_service, 'get_settings', lambda: roots)
    return roots


def upload(filename: str, content: bytes = PNG_BYTES) -> UploadFile:
    return UploadFile(file=BytesIO(content), filename=filename)


def test_dataset_and_category_lifecycle_updates_metadata(data_roots: SimpleNamespace) -> None:
    created = dataset_service.create_dataset('pcb-training', 'Initial set')
    with_category = dataset_service.create_category('pcb-training', 'pass-images')
    renamed_category = dataset_service.rename_category('pcb-training', 'pass-images', 'accepted')
    without_category = dataset_service.delete_category('pcb-training', 'accepted')
    updated = dataset_service.update_dataset('pcb-training', 'pcb-validation', 'Validation set')

    assert created['description'] == 'Initial set'
    assert with_category['categories'][0]['name'] == 'pass-images'
    assert renamed_category['categories'][0]['name'] == 'accepted'
    assert without_category['categories'] == []
    assert updated['name'] == 'pcb-validation'
    assert updated['description'] == 'Validation set'
    assert dataset_service.list_datasets()[0]['name'] == 'pcb-validation'

    dataset_service.delete_dataset('pcb-validation')
    assert dataset_service.list_datasets() == []


def test_upload_validates_magic_bytes_safe_names_batch_and_size(
    data_roots: SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset_service.create_dataset('pcb-training')
    dataset_service.create_category('pcb-training', 'accepted')

    uploaded = asyncio.run(dataset_service.upload_images('pcb-training', 'accepted', [upload('board.png')]))
    assert uploaded[0]['filename'] == 'board.png'
    assert uploaded[0]['media_type'] == 'image/png'
    assert uploaded[0]['width_px'] == 1

    with pytest.raises(ValueError, match='unsafe'):
        asyncio.run(dataset_service.upload_images('pcb-training', 'accepted', [upload('../board.png')]))
    with pytest.raises(ValueError, match='recognised image'):
        asyncio.run(dataset_service.upload_images('pcb-training', 'accepted', [upload('fake.png', b'not-an-image')]))
    with pytest.raises(ValueError, match='batch'):
        asyncio.run(dataset_service.upload_images('pcb-training', 'accepted', [upload(f'board-{index}.png') for index in range(101)]))

    monkeypatch.setattr(dataset_service, '_MAX_FILE_SIZE', 8)
    with pytest.raises(ValueError, match='limit'):
        asyncio.run(dataset_service.upload_images('pcb-training', 'accepted', [upload('large.png')]))


def test_image_rename_move_and_delete_preserve_dataset_counts(data_roots: SimpleNamespace) -> None:
    dataset_service.create_dataset('pcb-training')
    dataset_service.create_category('pcb-training', 'incoming')
    dataset_service.create_category('pcb-training', 'accepted')
    asyncio.run(dataset_service.upload_images('pcb-training', 'incoming', [upload('board.png')]))

    renamed = dataset_service.rename_image('pcb-training', 'incoming', 'board.png', 'board-pass.png')
    moved = dataset_service.move_image('pcb-training', 'incoming', 'board-pass.png', 'accepted')

    assert renamed['filename'] == 'board-pass.png'
    assert moved['filename'] == 'board-pass.png'
    assert dataset_service.list_images('pcb-training', 'incoming') == []
    assert dataset_service.get_dataset('pcb-training')['total_images'] == 1

    dataset_service.delete_image('pcb-training', 'accepted', 'board-pass.png')
    assert dataset_service.get_dataset('pcb-training')['total_images'] == 0


def test_capture_import_rejects_traversal_and_renames_duplicates(data_roots: SimpleNamespace) -> None:
    capture = data_roots.captures_data_path / 'run-01' / 'board.png'
    capture.parent.mkdir(parents=True)
    capture.write_bytes(PNG_BYTES)
    dataset_service.create_dataset('pcb-training')
    dataset_service.create_category('pcb-training', 'incoming')

    first = dataset_service.import_captures('pcb-training', ['run-01/board.png'], 'incoming')
    second = dataset_service.import_captures('pcb-training', ['run-01/board.png'], 'incoming')

    assert first[0]['filename'] == 'board.png'
    assert second[0]['filename'] == 'board-1.png'
    with pytest.raises(ValueError, match='Unsafe|traversal'):
        dataset_service.import_captures('pcb-training', ['../outside.png'], 'incoming')


def test_export_zip_contains_only_relative_image_paths(data_roots: SimpleNamespace) -> None:
    dataset_service.create_dataset('pcb-training')
    dataset_service.create_category('pcb-training', 'accepted')
    asyncio.run(dataset_service.upload_images('pcb-training', 'accepted', [upload('board.png')]))

    with ZipFile(dataset_service.export_dataset_zip('pcb-training')) as archive:
        assert archive.namelist() == ['accepted/board.png']
        assert archive.read('accepted/board.png') == PNG_BYTES
        assert all(not name.startswith(('/', '\\')) and '..' not in name for name in archive.namelist())