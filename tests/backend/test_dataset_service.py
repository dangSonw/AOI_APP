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


def test_validate_dataset_reports_duplicates_and_invalid_images(data_roots: SimpleNamespace) -> None:
    dataset_service.create_dataset('pcb-training')
    dataset_service.create_category('pcb-training', 'accepted')
    dataset_service.create_category('pcb-training', 'review')
    asyncio.run(dataset_service.upload_images('pcb-training', 'accepted', [upload('board.png')]))
    (data_roots.datasets_data_path / 'pcb-training' / 'review' / 'copy.png').write_bytes(PNG_BYTES)
    (data_roots.datasets_data_path / 'pcb-training' / 'review' / 'broken.png').write_bytes(b'not-an-image')

    report = dataset_service.validate_dataset('pcb-training')

    assert report['dataset_name'] == 'pcb-training'
    assert report['is_valid'] is False
    assert report['file_count'] == 3
    assert report['valid_file_count'] == 2
    assert report['duplicate_file_count'] == 1
    assert {issue['code'] for issue in report['issues']} == {'duplicate-content', 'invalid-image'}


def test_validate_dataset_accepts_valid_images(data_roots: SimpleNamespace) -> None:
    dataset_service.create_dataset('pcb-training')
    dataset_service.create_category('pcb-training', 'accepted')
    asyncio.run(dataset_service.upload_images('pcb-training', 'accepted', [upload('board.png')]))

    report = dataset_service.validate_dataset('pcb-training')

    assert report == {
        'dataset_name': 'pcb-training',
        'is_valid': True,
        'category_count': 1,
        'file_count': 1,
        'valid_file_count': 1,
        'total_size_bytes': len(PNG_BYTES),
        'duplicate_file_count': 0,
        'issues': [],
    }


def test_preview_csv_detects_schema_missing_values_and_sample_rows(data_roots: SimpleNamespace) -> None:
    del data_roots
    report = dataset_service.preview_csv(
        'training.csv',
        'label,score,enabled\npass,0.95,true\nfail,,false\n'.encode(),
    )

    assert report['delimiter'] == ','
    assert report['row_count'] == 2
    assert report['truncated'] is False
    assert report['sample_rows'][1]['score'] == ''
    assert [(column['name'], column['data_type'], column['missing_count']) for column in report['columns']] == [
        ('label', 'text', 0), ('score', 'number', 1), ('enabled', 'boolean', 0),
    ]


@pytest.mark.parametrize('filename,content,error', [
    ('training.txt', b'a,b\n1,2\n', 'requires a .csv'),
    ('training.csv', b'a,a\n1,2\n', 'headers must be unique'),
    ('training.csv', b'not a delimited file', 'delimiter could not be detected'),
])
def test_preview_csv_rejects_unsupported_or_invalid_input(
    data_roots: SimpleNamespace,
    filename: str,
    content: bytes,
    error: str,
) -> None:
    del data_roots
    with pytest.raises(ValueError, match=error):
        dataset_service.preview_csv(filename, content)


def test_prepare_csv_validates_columns_and_calculates_split(data_roots: SimpleNamespace) -> None:
    del data_roots
    report = dataset_service.prepare_csv(
        'training.csv',
        b'label,score,enabled\npass,0.95,true\nfail,0.10,false\npass,0.80,true\nfail,0.20,false\n',
        target_column='label',
        feature_columns=['score', 'enabled'],
        train_ratio=0.5,
        validation_ratio=0.25,
        test_ratio=0.25,
    )

    assert report['row_count'] == 4
    assert (report['train_rows'], report['validation_rows'], report['test_rows']) == (2, 1, 1)
    assert report['target_distribution'] == {'pass': 2, 'fail': 2}


def test_prepare_csv_rejects_target_feature_overlap(data_roots: SimpleNamespace) -> None:
    del data_roots
    with pytest.raises(ValueError, match='Target column cannot'):
        dataset_service.prepare_csv(
            'training.csv', b'label,score\npass,1\n', target_column='label',
            feature_columns=['label'], train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15,
        )


def test_create_csv_preparation_snapshot_is_immutable(data_roots: SimpleNamespace) -> None:
    dataset_service.create_dataset('pcb-training')
    content = b'label,score\npass,0.9\nfail,0.1\n'
    snapshot = dataset_service.create_csv_preparation_snapshot(
        'pcb-training', 'training.csv', content, target_column='label', feature_columns=['score'],
        train_ratio=0.5, validation_ratio=0.25, test_ratio=0.25,
    )

    snapshot_path = data_roots.datasets_data_path / 'pcb-training' / 'preparations' / snapshot['preparation_id']
    assert snapshot_path.joinpath('source.csv').read_bytes() == content
    metadata = snapshot_path.joinpath('preparation.json').read_text(encoding='utf-8')
    assert snapshot['source_sha256'] in metadata
    assert snapshot['config_sha256'] in metadata
    assert snapshot['preparation_id'].startswith('prep-')


def test_preparation_snapshots_are_not_dataset_categories(data_roots: SimpleNamespace) -> None:
    dataset_service.create_dataset('pcb-training')
    dataset_service.create_csv_preparation_snapshot(
        'pcb-training', 'training.csv', b'label,score\npass,0.9\n', target_column='label', feature_columns=['score'],
        train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15,
    )

    detail = dataset_service.get_dataset('pcb-training')

    assert detail['categories'] == []
    assert detail['category_count'] == 0


def test_snapshot_includes_and_validates_preprocessing_policy(data_roots: SimpleNamespace) -> None:
    dataset_service.create_dataset('pcb-training')
    snapshot = dataset_service.create_csv_preparation_snapshot(
        'pcb-training', 'training.csv', b'label,score\npass,0.9\n', target_column='label', feature_columns=['score'],
        train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15,
        preprocessing_policy={'scaling': 'standard'},
    )

    assert snapshot['preprocessing_policy']['scaling'] == 'standard'
    with pytest.raises(ValueError, match='Invalid preprocessing policy'):
        dataset_service.create_csv_preparation_snapshot(
            'pcb-training', 'training.csv', b'label,score\npass,0.9\n', target_column='label', feature_columns=['score'],
            train_ratio=0.7, validation_ratio=0.15, test_ratio=0.15,
            preprocessing_policy={'scaling': 'unsupported'},
        )


def test_preprocessing_preview_fits_numeric_statistics_on_train_only(data_roots: SimpleNamespace) -> None:
    dataset_service.create_dataset('pcb-training')
    snapshot = dataset_service.create_csv_preparation_snapshot(
        'pcb-training', 'training.csv', b'label,score\npass,1\npass,3\nfail,100\nfail,200\n',
        target_column='label', feature_columns=['score'], train_ratio=0.5, validation_ratio=0.25, test_ratio=0.25,
        preprocessing_policy={'scaling': 'standard'},
    )

    preview = dataset_service.preview_csv_preprocessing('pcb-training', snapshot['preparation_id'])

    assert preview['train_rows'] == 2
    assert preview['validation_rows'] == 1
    assert preview['test_rows'] == 1
    assert preview['fitted_statistics']['score']['mean'] == 2.0
    assert preview['train_sample_rows'][0]['score'] == -1.0


def test_preprocessing_preview_rejects_training_missing_values_with_error_policy(data_roots: SimpleNamespace) -> None:
    dataset_service.create_dataset('pcb-training')
    snapshot = dataset_service.create_csv_preparation_snapshot(
        'pcb-training', 'training.csv', b'label,score\npass,1\npass,\nfail,100\n',
        target_column='label', feature_columns=['score'], train_ratio=0.67, validation_ratio=0.16, test_ratio=0.17,
    )

    with pytest.raises(ValueError, match='contains missing training values'):
        dataset_service.preview_csv_preprocessing('pcb-training', snapshot['preparation_id'])


def test_processed_artifact_writes_splits_and_integrity_manifest(data_roots: SimpleNamespace) -> None:
    dataset_service.create_dataset('pcb-training')
    snapshot = dataset_service.create_csv_preparation_snapshot(
        'pcb-training', 'training.csv', b'label,score\npass,1\npass,3\nfail,100\nfail,200\n',
        target_column='label', feature_columns=['score'], train_ratio=0.5, validation_ratio=0.25, test_ratio=0.25,
        preprocessing_policy={'scaling': 'standard'},
    )

    artifact = dataset_service.create_csv_processed_artifact('pcb-training', snapshot['preparation_id'])

    artifact_path = data_roots.datasets_data_path / 'pcb-training' / 'preparations' / snapshot['preparation_id'] / 'artifacts' / artifact['artifact_id']
    assert artifact_path.joinpath('train.csv').exists()
    assert artifact_path.joinpath('validation.csv').exists()
    assert artifact_path.joinpath('test.csv').exists()
    manifest = artifact_path.joinpath('manifest.json').read_text(encoding='utf-8')
    assert artifact['split_sha256']['train'] in manifest
    assert artifact['manifest_sha256'] == __import__('hashlib').sha256(artifact_path.joinpath('manifest.json').read_bytes()).hexdigest()


def test_artifact_listing_and_verification_detect_tampering(data_roots: SimpleNamespace) -> None:
    dataset_service.create_dataset('pcb-training')
    snapshot = dataset_service.create_csv_preparation_snapshot(
        'pcb-training', 'training.csv', b'label,score\npass,1\npass,3\nfail,100\n',
        target_column='label', feature_columns=['score'], train_ratio=0.67, validation_ratio=0.16, test_ratio=0.17,
    )
    artifact = dataset_service.create_csv_processed_artifact('pcb-training', snapshot['preparation_id'])

    assert dataset_service.list_csv_processed_artifacts('pcb-training', snapshot['preparation_id'])[0]['artifact_id'] == artifact['artifact_id']
    assert dataset_service.verify_csv_processed_artifact('pcb-training', snapshot['preparation_id'], artifact['artifact_id'])['is_valid'] is True
    path = data_roots.datasets_data_path / 'pcb-training' / 'preparations' / snapshot['preparation_id'] / 'artifacts' / artifact['artifact_id'] / 'train.csv'
    path.write_bytes(b'changed')
    report = dataset_service.verify_csv_processed_artifact('pcb-training', snapshot['preparation_id'], artifact['artifact_id'])
    assert report['is_valid'] is False
    assert report['issues'] == ['train.csv checksum mismatch.']


def test_knn_training_requires_verified_numeric_artifact_and_persists_metrics(data_roots: SimpleNamespace) -> None:
    dataset_service.create_dataset('pcb-training')
    snapshot = dataset_service.create_csv_preparation_snapshot(
        'pcb-training', 'training.csv', b'label,score\npass,1\npass,2\nfail,9\nfail,10\n',
        target_column='label', feature_columns=['score'], train_ratio=0.5, validation_ratio=0.25, test_ratio=0.25,
    )
    artifact = dataset_service.create_csv_processed_artifact('pcb-training', snapshot['preparation_id'])

    job = dataset_service.create_csv_knn_training_job('pcb-training', snapshot['preparation_id'], artifact['artifact_id'], k=1)

    assert job['status'] == 'completed'
    assert job['algorithm'] == 'knn-classifier'
    assert job['validation_accuracy'] == 1.0
    assert job['test_accuracy'] == 1.0
    assert dataset_service.list_csv_knn_training_jobs('pcb-training', snapshot['preparation_id'], artifact['artifact_id'])[0]['job_id'] == job['job_id']


def test_knn_training_rejects_tampered_artifact(data_roots: SimpleNamespace) -> None:
    dataset_service.create_dataset('pcb-training')
    snapshot = dataset_service.create_csv_preparation_snapshot(
        'pcb-training', 'training.csv', b'label,score\npass,1\nfail,9\n', target_column='label', feature_columns=['score'],
        train_ratio=0.5, validation_ratio=0.25, test_ratio=0.25,
    )
    artifact = dataset_service.create_csv_processed_artifact('pcb-training', snapshot['preparation_id'])
    artifact_path = data_roots.datasets_data_path / 'pcb-training' / 'preparations' / snapshot['preparation_id'] / 'artifacts' / artifact['artifact_id'] / 'test.csv'
    artifact_path.write_bytes(b'tampered')

    with pytest.raises(ValueError, match='integrity verification failed'):
        dataset_service.create_csv_knn_training_job('pcb-training', snapshot['preparation_id'], artifact['artifact_id'])