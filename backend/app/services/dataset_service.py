"""Dataset filesystem service.

Manages datasets as directories under ``data/datasets/`` with a companion
``metadata.json`` descriptor that is regenerated after every mutation.
"""

from __future__ import annotations

import json
import hashlib
import csv
import io
import math
import os
import re
import shutil
import struct
import tempfile
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path

from fastapi import UploadFile

from app.config.settings import get_settings

_NAME_RE = re.compile(r'^[a-z0-9]([a-z0-9-]*[a-z0-9])?$')
_FILENAME_RE = re.compile(r'^[a-zA-Z0-9_-]+\.(png|jpg|jpeg|bmp|tiff|tif)$', re.IGNORECASE)
_ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif'}
_IMAGE_MAGIC = {
    b'\x89PNG': 'image/png',
    b'\xff\xd8\xff': 'image/jpeg',
    b'BM': 'image/bmp',
    b'II': 'image/tiff',
    b'MM': 'image/tiff',
}
_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
_MAX_UPLOAD_BATCH = 100
_MAX_VALIDATION_FILES = 10_000
_MAX_VALIDATION_BYTES = 2 * 1024 * 1024 * 1024
_MAX_CSV_BYTES = 10 * 1024 * 1024
_MAX_CSV_ROWS = 10_000
_MAX_CSV_SAMPLE_ROWS = 20
_METADATA_FILENAME = 'metadata.json'
_PREPARATIONS_DIRECTORY = 'preparations'
_ARTIFACTS_DIRECTORY = 'artifacts'
_TRAINING_JOBS_DIRECTORY = 'training-jobs'


def _is_number(value: str) -> bool:
    try:
        float(value)
        return True
    except ValueError:
        return False


def _validate_name(name: str) -> None:
    if not _NAME_RE.match(name):
        raise ValueError(
            f'Invalid name "{name}". Use kebab-case with lowercase alphanumerics and hyphens.',
        )
    if len(name) > 64:
        raise ValueError('Name must not exceed 64 characters.')


def _validate_filename(filename: str) -> None:
    if '..' in filename or '/' in filename or '\\' in filename or '\x00' in filename:
        raise ValueError('Filename contains unsafe characters.')
    if filename.startswith('.'):
        raise ValueError('Hidden filenames are not allowed.')
    if not _FILENAME_RE.match(filename):
        raise ValueError(
            f'Invalid filename "{filename}". '
            f'Allowed extensions: {", ".join(sorted(_ALLOWED_EXTENSIONS))}.',
        )
    if len(filename) > 128:
        raise ValueError('Filename must not exceed 128 characters.')


def _validate_magic_bytes(data: bytes) -> str:
    """Return detected MIME type or raise if content is not a recognised image."""
    for magic, mime in _IMAGE_MAGIC.items():
        if data[:len(magic)] == magic:
            return mime
    raise ValueError('File content is not a recognised image format.')


# ---------------------------------------------------------------------------
# Path helpers & Image dimensions
# ---------------------------------------------------------------------------


def _datasets_root() -> Path:
    root = get_settings().datasets_data_path
    root.mkdir(parents=True, exist_ok=True)
    return root


def _captures_root() -> Path:
    root = get_settings().captures_data_path
    root.mkdir(parents=True, exist_ok=True)
    return root


def _dataset_path(name: str) -> Path:
    _validate_name(name)
    path = _datasets_root() / name
    if not path.exists():
        raise FileNotFoundError(f'Dataset "{name}" does not exist.')
    return path


def _category_path(dataset_name: str, category_name: str) -> Path:
    _validate_name(category_name)
    path = _dataset_path(dataset_name) / category_name
    if not path.exists():
        raise FileNotFoundError(
            f'Category "{category_name}" does not exist in dataset "{dataset_name}".',
        )
    return path


def _read_image_dimensions(file_path: Path) -> tuple[int | None, int | None]:
    """Read width and height from PNG or JPEG headers."""
    try:
        with open(file_path, 'rb') as fh:
            header = fh.read(32)
            if header[:4] == b'\x89PNG' and len(header) >= 24:
                width, height = struct.unpack('>II', header[16:24])
                return int(width), int(height)
            if header[:2] == b'\xff\xd8':
                fh.seek(0)
                data = fh.read(65536)
                offset = 2
                while offset < len(data) - 8:
                    if data[offset] != 0xFF:
                        break
                    marker = data[offset + 1]
                    if marker in (0xC0, 0xC1, 0xC2):
                        height = struct.unpack('>H', data[offset + 5:offset + 7])[0]
                        width = struct.unpack('>H', data[offset + 7:offset + 9])[0]
                        return int(width), int(height)
                    length = struct.unpack('>H', data[offset + 2:offset + 4])[0]
                    offset += 2 + length
    except Exception:
        pass
    return None, None


def _media_type_from_extension(filename: str) -> str:
    ext = filename.rsplit('.', 1)[-1].lower()
    mapping = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'bmp': 'image/bmp',
        'tiff': 'image/tiff',
        'tif': 'image/tiff',
    }
    return mapping.get(ext, 'application/octet-stream')


# ---------------------------------------------------------------------------
# Metadata management
# ---------------------------------------------------------------------------


def _regenerate_metadata(dataset_path: Path) -> dict:
    """Scan dataset directory and atomically rewrite metadata.json."""
    name = dataset_path.name
    meta_path = dataset_path / _METADATA_FILENAME

    existing_meta: dict = {}
    if meta_path.exists():
        try:
            existing_meta = json.loads(meta_path.read_text(encoding='utf-8'))
        except Exception:
            existing_meta = {}

    created_at = existing_meta.get('createdAt', datetime.now(timezone.utc).isoformat())
    description = existing_meta.get('description', '')

    categories: list[dict] = []
    total_images = 0
    total_size = 0

    for entry in sorted(dataset_path.iterdir()):
        if not entry.is_dir() or entry.name.startswith('.') or entry.name == _PREPARATIONS_DIRECTORY:
            continue
        cat_images = 0
        cat_size = 0
        for img_file in entry.iterdir():
            if img_file.is_file() and not img_file.name.startswith('.'):
                ext = img_file.suffix.lstrip('.').lower()
                if ext in _ALLOWED_EXTENSIONS:
                    cat_images += 1
                    cat_size += img_file.stat().st_size
        categories.append({
            'name': entry.name,
            'imageCount': cat_images,
            'totalSizeBytes': cat_size,
        })
        total_images += cat_images
        total_size += cat_size

    metadata = {
        'name': name,
        'description': description,
        'createdAt': created_at,
        'updatedAt': datetime.now(timezone.utc).isoformat(),
        'categories': categories,
        'totalImages': total_images,
        'totalSizeBytes': total_size,
    }

    fd, tmp_path = tempfile.mkstemp(dir=str(dataset_path), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            json.dump(metadata, fh, indent=2)
        os.replace(tmp_path, str(meta_path))
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return metadata


def _read_metadata(dataset_path: Path) -> dict:
    meta_path = dataset_path / _METADATA_FILENAME
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding='utf-8'))
    return _regenerate_metadata(dataset_path)


def _metadata_to_summary(meta: dict) -> dict:
    return {
        'name': meta['name'],
        'description': meta.get('description', ''),
        'total_images': meta.get('totalImages', 0),
        'total_size_bytes': meta.get('totalSizeBytes', 0),
        'category_count': len(meta.get('categories', [])),
        'created_at': meta.get('createdAt', ''),
        'updated_at': meta.get('updatedAt', ''),
    }


def _metadata_to_detail(meta: dict) -> dict:
    summary = _metadata_to_summary(meta)
    summary['categories'] = [
        {
            'name': c['name'],
            'image_count': c.get('imageCount', 0),
            'total_size_bytes': c.get('totalSizeBytes', 0),
        }
        for c in meta.get('categories', [])
    ]
    return summary


# ---------------------------------------------------------------------------
# Dataset CRUD
# ---------------------------------------------------------------------------


def list_datasets() -> list[dict]:
    root = _datasets_root()
    result: list[dict] = []
    for entry in sorted(root.iterdir()):
        if entry.is_dir() and not entry.name.startswith('.'):
            meta = _read_metadata(entry)
            result.append(_metadata_to_summary(meta))
    return result


def create_dataset(name: str, description: str = '') -> dict:
    _validate_name(name)
    dataset_dir = _datasets_root() / name
    if dataset_dir.exists():
        raise ValueError(f'Dataset "{name}" already exists.')
    dataset_dir.mkdir(parents=True)

    initial_meta = {
        'name': name,
        'description': description,
        'createdAt': datetime.now(timezone.utc).isoformat(),
        'updatedAt': datetime.now(timezone.utc).isoformat(),
        'categories': [],
        'totalImages': 0,
        'totalSizeBytes': 0,
    }
    meta_path = dataset_dir / _METADATA_FILENAME
    meta_path.write_text(json.dumps(initial_meta, indent=2), encoding='utf-8')
    return _metadata_to_detail(initial_meta)


def get_dataset(name: str) -> dict:
    path = _dataset_path(name)
    meta = _read_metadata(path)
    return _metadata_to_detail(meta)


def validate_dataset(name: str) -> dict:
    """Perform a bounded, read-only integrity scan of every dataset image."""
    dataset_path = _dataset_path(name)
    issues: list[dict] = []
    hashes: dict[str, tuple[str, str]] = {}
    file_count = 0
    valid_file_count = 0
    total_size = 0
    category_count = 0

    for category_path in sorted(dataset_path.iterdir()):
        if not category_path.is_dir() or category_path.name.startswith('.'):
            continue
        category_count += 1
        for file_path in sorted(category_path.iterdir()):
            if not file_path.is_file() or file_path.name.startswith('.'):
                continue
            file_count += 1
            if file_count > _MAX_VALIDATION_FILES:
                issues.append({
                    'category_name': category_path.name,
                    'filename': file_path.name,
                    'code': 'file-limit-exceeded',
                    'message': f'Dataset validation is limited to {_MAX_VALIDATION_FILES} files.',
                })
                break
            size = file_path.stat().st_size
            total_size += size
            if total_size > _MAX_VALIDATION_BYTES:
                issues.append({
                    'category_name': category_path.name,
                    'filename': file_path.name,
                    'code': 'byte-limit-exceeded',
                    'message': 'Dataset validation stopped at the 2 GB scan limit.',
                })
                break
            try:
                content = file_path.read_bytes()
                detected_type = _validate_magic_bytes(content)
                expected_type = _media_type_from_extension(file_path.name)
                if detected_type != expected_type:
                    raise ValueError(f'Content type {detected_type} does not match extension type {expected_type}.')
                width, height = _read_image_dimensions(file_path)
                if width is None or height is None or width < 1 or height < 1:
                    raise ValueError('Image dimensions could not be read.')
                digest = hashlib.sha256(content).hexdigest()
                previous = hashes.get(digest)
                if previous is not None:
                    issues.append({
                        'category_name': category_path.name,
                        'filename': file_path.name,
                        'code': 'duplicate-content',
                        'message': f'Content duplicates {previous[0]}/{previous[1]}.',
                    })
                else:
                    hashes[digest] = (category_path.name, file_path.name)
                valid_file_count += 1
            except (OSError, ValueError) as error:
                issues.append({
                    'category_name': category_path.name,
                    'filename': file_path.name,
                    'code': 'invalid-image',
                    'message': str(error),
                })
        if file_count > _MAX_VALIDATION_FILES or total_size > _MAX_VALIDATION_BYTES:
            break

    duplicate_count = sum(issue['code'] == 'duplicate-content' for issue in issues)
    return {
        'dataset_name': name,
        'is_valid': not issues,
        'category_count': category_count,
        'file_count': file_count,
        'valid_file_count': valid_file_count,
        'total_size_bytes': total_size,
        'duplicate_file_count': duplicate_count,
        'issues': issues,
    }


def preview_csv(filename: str, content: bytes) -> dict:
    """Parse a bounded CSV upload without persisting or mutating it."""
    if not filename.lower().endswith('.csv'):
        raise ValueError('CSV preview requires a .csv file.')
    if len(content) == 0:
        raise ValueError('CSV file is empty.')
    if len(content) > _MAX_CSV_BYTES:
        raise ValueError(f'CSV file exceeds the {_MAX_CSV_BYTES // (1024 * 1024)} MB preview limit.')

    decoded: str | None = None
    encoding = ''
    for candidate in ('utf-8-sig', 'utf-8'):
        try:
            decoded = content.decode(candidate)
            encoding = candidate
            break
        except UnicodeDecodeError:
            continue
    if decoded is None:
        raise ValueError('CSV must use UTF-8 encoding.')

    sample = decoded[:8192]
    delimiter_scores = {candidate: sample.count(candidate) for candidate in (',', ';', '\t', '|')}
    delimiter = max(delimiter_scores, key=delimiter_scores.get)
    if delimiter_scores[delimiter] == 0:
        raise ValueError('CSV delimiter could not be detected.')

    reader = csv.reader(io.StringIO(decoded), delimiter=delimiter)
    try:
        headers = next(reader)
    except StopIteration as error:
        raise ValueError('CSV must contain a header row.') from error
    headers = [header.strip() for header in headers]
    if not headers or any(not header for header in headers):
        raise ValueError('CSV headers must not be empty.')
    if len(set(headers)) != len(headers):
        raise ValueError('CSV headers must be unique.')

    rows: list[list[str]] = []
    warnings: list[str] = []
    row_count = 0
    for raw_row in reader:
        if not any(cell.strip() for cell in raw_row):
            continue
        row_count += 1
        if row_count <= _MAX_CSV_ROWS:
            if len(raw_row) != len(headers):
                warnings.append(f'Row {row_count} has {len(raw_row)} values; expected {len(headers)}.')
                raw_row = (raw_row + [''] * len(headers))[:len(headers)]
            rows.append([cell.strip() for cell in raw_row])
        else:
            break

    sample_rows = [dict(zip(headers, row, strict=True)) for row in rows[:_MAX_CSV_SAMPLE_ROWS]]
    columns: list[dict] = []
    for index, header in enumerate(headers):
        values = [row[index] for row in rows]
        non_empty = [value for value in values if value != '']
        data_type = 'text'
        if non_empty and all(value.lower() in {'true', 'false'} for value in non_empty):
            data_type = 'boolean'
        elif non_empty:
            try:
                [float(value) for value in non_empty]
                data_type = 'number'
            except ValueError:
                pass
        columns.append({
            'name': header,
            'data_type': data_type,
            'missing_count': len(values) - len(non_empty),
            'unique_count': len(set(non_empty)),
        })

    truncated = row_count > _MAX_CSV_ROWS
    if truncated:
        warnings.append(f'Preview stopped after {_MAX_CSV_ROWS} rows.')
    return {
        'filename': filename,
        'encoding': encoding,
        'delimiter': '\\t' if delimiter == '\t' else delimiter,
        'row_count': min(row_count, _MAX_CSV_ROWS),
        'sample_rows': sample_rows,
        'truncated': truncated,
        'columns': columns,
        'warnings': list(dict.fromkeys(warnings)),
    }


def prepare_csv(
    filename: str,
    content: bytes,
    *,
    target_column: str,
    feature_columns: list[str],
    train_ratio: float,
    validation_ratio: float,
    test_ratio: float,
) -> dict:
    """Validate a tabular preparation draft without persisting or training it."""
    ratios = (train_ratio, validation_ratio, test_ratio)
    if any(ratio <= 0 or ratio >= 1 for ratio in ratios):
        raise ValueError('Split ratios must be greater than zero and less than one.')
    if abs(sum(ratios) - 1.0) > 1e-6:
        raise ValueError('Split ratios must sum to 1.0.')
    if not feature_columns:
        raise ValueError('At least one feature column is required.')
    if len(set(feature_columns)) != len(feature_columns):
        raise ValueError('Feature columns must be unique.')

    preview = preview_csv(filename, content)
    columns = {column['name'] for column in preview['columns']}
    if target_column not in columns:
        raise ValueError(f'Target column "{target_column}" does not exist.')
    missing_features = [column for column in feature_columns if column not in columns]
    if missing_features:
        raise ValueError(f'Feature columns do not exist: {", ".join(missing_features)}.')
    if target_column in feature_columns:
        raise ValueError('Target column cannot also be a feature column.')

    row_count = preview['row_count']
    train_rows = int(row_count * train_ratio)
    validation_rows = int(row_count * validation_ratio)
    test_rows = row_count - train_rows - validation_rows
    warnings = list(preview['warnings'])
    target_distribution: dict[str, int] = {}
    for row in preview['sample_rows']:
        value = row.get(target_column, '') or '<missing>'
        target_distribution[value] = target_distribution.get(value, 0) + 1
    target_column_info = next(column for column in preview['columns'] if column['name'] == target_column)
    if target_column_info['missing_count'] > 0:
        warnings.append(f'Target column contains {target_column_info["missing_count"]} missing value(s) in the preview.')
    if preview['truncated']:
        warnings.append('Preparation counts are based on the bounded preview, not the full file.')

    return {
        'filename': preview['filename'],
        'target_column': target_column,
        'feature_columns': feature_columns,
        'row_count': row_count,
        'train_rows': train_rows,
        'validation_rows': validation_rows,
        'test_rows': test_rows,
        'target_distribution': target_distribution,
        'warnings': list(dict.fromkeys(warnings)),
    }


def create_csv_preparation_snapshot(
    dataset_name: str,
    filename: str,
    content: bytes,
    *,
    target_column: str,
    feature_columns: list[str],
    train_ratio: float,
    validation_ratio: float,
    test_ratio: float,
    preprocessing_policy: dict[str, str] | None = None,
) -> dict:
    """Persist an immutable preparation input and its validated configuration."""
    dataset_path = _dataset_path(dataset_name)
    report = prepare_csv(
        filename,
        content,
        target_column=target_column,
        feature_columns=feature_columns,
        train_ratio=train_ratio,
        validation_ratio=validation_ratio,
        test_ratio=test_ratio,
    )
    policy = {
        'numeric_missing': 'error',
        'categorical_missing': 'error',
        'scaling': 'none',
        'categorical_encoding': 'none',
        **(preprocessing_policy or {}),
    }
    allowed_policy_values = {
        'numeric_missing': {'error', 'mean', 'median'},
        'categorical_missing': {'error', 'most-frequent', 'constant'},
        'scaling': {'none', 'standard'},
        'categorical_encoding': {'none', 'one-hot'},
    }
    unknown_policy_keys = set(policy) - set(allowed_policy_values)
    if unknown_policy_keys:
        raise ValueError(f'Unknown preprocessing policy option(s): {", ".join(sorted(unknown_policy_keys))}.')
    invalid_policy = [
        f'{key}={value}' for key, value in policy.items() if value not in allowed_policy_values[key]
    ]
    if invalid_policy:
        raise ValueError(f'Invalid preprocessing policy option(s): {", ".join(invalid_policy)}.')
    preview = preview_csv(filename, content)
    feature_types = {column['name']: column['data_type'] for column in preview['columns']}
    if policy['scaling'] == 'standard' and any(feature_types[column] != 'number' for column in feature_columns):
        raise ValueError('Standard scaling requires all feature columns to be numeric.')
    if policy['categorical_encoding'] == 'one-hot' and not any(feature_types[column] in {'text', 'boolean'} for column in feature_columns):
        raise ValueError('One-hot encoding requires at least one categorical feature.')
    source_sha256 = hashlib.sha256(content).hexdigest()
    config = {
        'feature_columns': feature_columns,
        'target_column': target_column,
        'test_ratio': test_ratio,
        'train_ratio': train_ratio,
        'validation_ratio': validation_ratio,
        'preprocessing_policy': policy,
    }
    canonical_config = json.dumps(config, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
    config_sha256 = hashlib.sha256(canonical_config).hexdigest()
    created_at = datetime.now(timezone.utc)
    preparation_id = f'prep-{created_at.strftime("%Y%m%dT%H%M%S%fZ")}-{config_sha256[:12]}'
    preparations_path = dataset_path / _PREPARATIONS_DIRECTORY
    preparations_path.mkdir(exist_ok=True)
    snapshot_path = preparations_path / preparation_id
    temporary_path = Path(tempfile.mkdtemp(prefix=f'.{preparation_id}-', dir=str(preparations_path)))
    try:
        (temporary_path / 'source.csv').write_bytes(content)
        metadata = {
            **report,
            'config': config,
            'config_sha256': config_sha256,
            'created_at': created_at.isoformat(),
            'dataset_name': dataset_name,
            'preparation_id': preparation_id,
            'source_sha256': source_sha256,
            'source_filename': filename,
            'schema_version': 1,
        }
        (temporary_path / 'preparation.json').write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + '\n',
            encoding='utf-8',
        )
        os.replace(temporary_path, snapshot_path)
    except Exception:
        shutil.rmtree(temporary_path, ignore_errors=True)
        raise
    return {
        **report,
        'preparation_id': preparation_id,
        'dataset_name': dataset_name,
        'source_sha256': source_sha256,
        'config_sha256': config_sha256,
        'created_at': created_at,
        'preprocessing_policy': policy,
    }


def preview_csv_preprocessing(dataset_name: str, preparation_id: str) -> dict:
    """Preview bounded preprocessing, fitting all statistics on train rows only."""
    snapshot_path = _dataset_path(dataset_name) / _PREPARATIONS_DIRECTORY / preparation_id
    if not re.match(r'^prep-[0-9TZ-]+-[a-f0-9]{12}$', preparation_id) or not snapshot_path.is_dir():
        raise FileNotFoundError(f'Preparation snapshot "{preparation_id}" does not exist.')
    metadata = json.loads((snapshot_path / 'preparation.json').read_text(encoding='utf-8'))
    config = metadata['config']
    policy = config['preprocessing_policy']
    content = (snapshot_path / 'source.csv').read_bytes()
    decoded = content.decode('utf-8-sig')
    dialect = csv.Sniffer().sniff(decoded[:8192], delimiters=',;\t|')
    reader = csv.DictReader(io.StringIO(decoded), dialect=dialect)
    rows = [dict(row) for row in reader if any((value or '').strip() for value in row.values())][: _MAX_CSV_ROWS]
    total = len(rows)
    train_count = int(total * config['train_ratio'])
    validation_count = int(total * config['validation_ratio'])
    partitions = (rows[:train_count], rows[train_count:train_count + validation_count], rows[train_count + validation_count:])
    feature_columns = config['feature_columns']
    statistics: dict[str, dict] = {}
    processed_columns: list[str] = []
    for column in feature_columns:
        values = [row.get(column, '') or '' for row in partitions[0]]
        is_numeric = all(not value or _is_number(value) for value in values)
        missing_policy = policy['numeric_missing'] if is_numeric else policy['categorical_missing']
        non_empty = [float(value) for value in values if value] if is_numeric else [value for value in values if value]
        if any(not value for value in values) and missing_policy == 'error':
            raise ValueError(f'Feature column "{column}" contains missing training values.')
        if not non_empty and missing_policy == 'error':
            raise ValueError(f'Feature column "{column}" has no usable training values.')
        if is_numeric:
            fill = 0.0 if not non_empty else (sum(non_empty) / len(non_empty) if missing_policy == 'mean' else sorted(non_empty)[(len(non_empty) - 1) // 2])
            mean = sum(non_empty) / len(non_empty) if non_empty else 0.0
            variance = sum((value - mean) ** 2 for value in non_empty) / len(non_empty) if non_empty else 0.0
            statistics[column] = {'type': 'number', 'fill': fill, 'mean': mean, 'scale': variance ** 0.5 or 1.0}
            processed_columns.append(column)
        else:
            categories = sorted(set(non_empty))
            fill = (max(set(non_empty), key=non_empty.count) if non_empty and missing_policy == 'most-frequent' else '<missing>')
            statistics[column] = {'type': 'categorical', 'fill': fill, 'categories': categories}
            processed_columns.extend([f'{column}={category}' for category in categories] if policy['categorical_encoding'] == 'one-hot' else [column])

    target_column = config['target_column']

    def transform(partition: list[dict], limit: int | None = _MAX_CSV_SAMPLE_ROWS) -> list[dict[str, str | float]]:
        transformed: list[dict[str, str | float]] = []
        for row in partition[:limit]:
            output: dict[str, str | float] = {}
            for column in feature_columns:
                stat = statistics[column]
                value = row.get(column, '') or ''
                if stat['type'] == 'number':
                    numeric = float(value) if value else float(stat['fill'])
                    output[column] = (numeric - float(stat['mean'])) / float(stat['scale']) if policy['scaling'] == 'standard' else numeric
                elif policy['categorical_encoding'] == 'one-hot':
                    for category in stat['categories']:
                        output[f'{column}={category}'] = 1.0 if (value or stat['fill']) == category else 0.0
                else:
                    output[column] = value or str(stat['fill'])
            output[target_column] = row.get(target_column, '') or ''
            transformed.append(output)
        return transformed

    return {
        'preparation_id': preparation_id,
        'target_column': target_column,
        'feature_columns': feature_columns,
        'processed_columns': processed_columns,
        'train_rows': len(partitions[0]), 'validation_rows': len(partitions[1]), 'test_rows': len(partitions[2]),
        'train_sample_rows': transform(partitions[0]), 'validation_sample_rows': transform(partitions[1]), 'test_sample_rows': transform(partitions[2]),
        'fitted_statistics': statistics,
        'warnings': ['Statistics and category vocabulary were fitted on train rows only.'],
        '_transformed_partitions': [transform(partition, None) for partition in partitions],
    }


def create_csv_processed_artifact(dataset_name: str, preparation_id: str) -> dict:
    """Materialize a bounded, immutable processed CSV artifact from a snapshot."""
    preview = preview_csv_preprocessing(dataset_name, preparation_id)
    dataset_path = _dataset_path(dataset_name)
    snapshot_path = dataset_path / _PREPARATIONS_DIRECTORY / preparation_id
    metadata = json.loads((snapshot_path / 'preparation.json').read_text(encoding='utf-8'))
    created_at = datetime.now(timezone.utc)
    artifact_seed = hashlib.sha256(f'{preparation_id}:{created_at.isoformat()}'.encode()).hexdigest()
    artifact_id = f'artifact-{created_at.strftime("%Y%m%dT%H%M%S%fZ")}-{artifact_seed[:12]}'
    artifacts_path = snapshot_path / _ARTIFACTS_DIRECTORY
    artifacts_path.mkdir(exist_ok=True)
    destination = artifacts_path / artifact_id
    temporary = Path(tempfile.mkdtemp(prefix=f'.{artifact_id}-', dir=str(artifacts_path)))
    split_names = ('train', 'validation', 'test')
    fieldnames = [*preview['processed_columns'], preview['target_column']]
    split_sha256: dict[str, str] = {}
    try:
        for split_name, rows in zip(split_names, preview['_transformed_partitions'], strict=True):
            output = io.StringIO(newline='')
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='raise')
            writer.writeheader()
            writer.writerows(rows)
            content = output.getvalue().encode('utf-8')
            (temporary / f'{split_name}.csv').write_bytes(content)
            split_sha256[split_name] = hashlib.sha256(content).hexdigest()
        manifest = {
            'artifact_id': artifact_id,
            'created_at': created_at.isoformat(),
            'fitted_statistics': preview['fitted_statistics'],
            'output_columns': fieldnames,
            'preparation_id': preparation_id,
            'preprocessing_policy': metadata['config']['preprocessing_policy'],
            'row_counts': {name: len(rows) for name, rows in zip(split_names, preview['_transformed_partitions'], strict=True)},
            'schema_version': 1,
            'source_sha256': metadata['source_sha256'],
            'config_sha256': metadata['config_sha256'],
            'split_sha256': split_sha256,
            'target_column': preview['target_column'],
        }
        manifest_content = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
        (temporary / 'manifest.json').write_bytes(manifest_content)
        os.replace(temporary, destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return {
        'artifact_id': artifact_id, 'preparation_id': preparation_id, 'target_column': preview['target_column'],
        'processed_columns': preview['processed_columns'], 'train_rows': preview['train_rows'],
        'validation_rows': preview['validation_rows'], 'test_rows': preview['test_rows'],
        'split_sha256': split_sha256, 'manifest_sha256': hashlib.sha256(manifest_content).hexdigest(), 'created_at': created_at,
    }


def _artifact_path(dataset_name: str, preparation_id: str, artifact_id: str) -> Path:
    if not re.match(r'^artifact-[0-9TZ-]+-[a-f0-9]{12}$', artifact_id):
        raise FileNotFoundError(f'Processed artifact "{artifact_id}" does not exist.')
    path = _dataset_path(dataset_name) / _PREPARATIONS_DIRECTORY / preparation_id / _ARTIFACTS_DIRECTORY / artifact_id
    if not path.is_dir():
        raise FileNotFoundError(f'Processed artifact "{artifact_id}" does not exist.')
    return path


def list_csv_processed_artifacts(dataset_name: str, preparation_id: str) -> list[dict]:
    snapshot_path = _dataset_path(dataset_name) / _PREPARATIONS_DIRECTORY / preparation_id
    if not snapshot_path.is_dir():
        raise FileNotFoundError(f'Preparation snapshot "{preparation_id}" does not exist.')
    artifacts_path = snapshot_path / _ARTIFACTS_DIRECTORY
    if not artifacts_path.exists():
        return []
    artifacts: list[dict] = []
    for path in sorted(artifacts_path.iterdir(), reverse=True):
        if not path.is_dir() or not re.match(r'^artifact-[0-9TZ-]+-[a-f0-9]{12}$', path.name):
            continue
        try:
            manifest_content = (path / 'manifest.json').read_bytes()
            manifest = json.loads(manifest_content)
            artifacts.append({
                'artifact_id': manifest['artifact_id'], 'preparation_id': manifest['preparation_id'],
                'target_column': manifest['target_column'], 'processed_columns': manifest['output_columns'][:-1],
                'train_rows': manifest['row_counts']['train'], 'validation_rows': manifest['row_counts']['validation'],
                'test_rows': manifest['row_counts']['test'], 'split_sha256': manifest['split_sha256'],
                'manifest_sha256': hashlib.sha256(manifest_content).hexdigest(), 'created_at': manifest['created_at'],
            })
        except (OSError, KeyError, json.JSONDecodeError):
            continue
    return artifacts


def verify_csv_processed_artifact(dataset_name: str, preparation_id: str, artifact_id: str) -> dict:
    path = _artifact_path(dataset_name, preparation_id, artifact_id)
    issues: list[str] = []
    manifest_content = (path / 'manifest.json').read_bytes()
    manifest_sha256 = hashlib.sha256(manifest_content).hexdigest()
    try:
        manifest = json.loads(manifest_content)
    except json.JSONDecodeError:
        return {'artifact_id': artifact_id, 'is_valid': False, 'manifest_sha256': manifest_sha256, 'split_sha256': {}, 'issues': ['Manifest is not valid JSON.']}
    actual_hashes: dict[str, str] = {}
    for split_name in ('train', 'validation', 'test'):
        split_path = path / f'{split_name}.csv'
        if not split_path.is_file():
            issues.append(f'Missing {split_name}.csv.')
            continue
        actual_hashes[split_name] = hashlib.sha256(split_path.read_bytes()).hexdigest()
        if actual_hashes[split_name] != manifest.get('split_sha256', {}).get(split_name):
            issues.append(f'{split_name}.csv checksum mismatch.')
    if manifest.get('artifact_id') != artifact_id:
        issues.append('Manifest artifact ID does not match its directory.')
    if manifest.get('preparation_id') != preparation_id:
        issues.append('Manifest preparation ID does not match its parent snapshot.')
    return {'artifact_id': artifact_id, 'is_valid': not issues, 'manifest_sha256': manifest_sha256, 'split_sha256': actual_hashes, 'issues': issues}


def _read_numeric_split(path: Path, feature_columns: list[str], target_column: str) -> list[tuple[list[float], str]]:
    with path.open(encoding='utf-8', newline='') as file_handle:
        reader = csv.DictReader(file_handle)
        if reader.fieldnames != [*feature_columns, target_column]:
            raise ValueError('Processed artifact CSV schema does not match its manifest.')
        rows: list[tuple[list[float], str]] = []
        for row in reader:
            try:
                features = [float(row[column]) for column in feature_columns]
            except (TypeError, ValueError) as exc:
                raise ValueError('KNN baseline requires numeric processed feature columns.') from exc
            if not all(math.isfinite(value) for value in features):
                raise ValueError('KNN baseline requires finite processed feature values.')
            target = row.get(target_column, '')
            if not target:
                raise ValueError('KNN baseline requires non-empty target labels.')
            rows.append((features, target))
    return rows


def _knn_predict(training_rows: list[tuple[list[float], str]], features: list[float], k: int) -> str:
    neighbours = sorted(
        ((sum((left - right) ** 2 for left, right in zip(vector, features, strict=True)), label) for vector, label in training_rows),
        key=lambda item: (item[0], item[1]),
    )[:k]
    votes: dict[str, int] = {}
    for _, label in neighbours:
        votes[label] = votes.get(label, 0) + 1
    return min(votes, key=lambda label: (-votes[label], label))


def create_csv_knn_training_job(dataset_name: str, preparation_id: str, artifact_id: str, k: int = 3) -> dict:
    """Synchronously train and persist a bounded pure-Python KNN classification baseline."""
    verification = verify_csv_processed_artifact(dataset_name, preparation_id, artifact_id)
    if not verification['is_valid']:
        raise ValueError(f'Processed artifact integrity verification failed: {" ".join(verification["issues"])}')
    artifact_path = _artifact_path(dataset_name, preparation_id, artifact_id)
    manifest = json.loads((artifact_path / 'manifest.json').read_text(encoding='utf-8'))
    feature_columns = manifest['output_columns'][:-1]
    target_column = manifest['target_column']
    train_rows = _read_numeric_split(artifact_path / 'train.csv', feature_columns, target_column)
    if not train_rows:
        raise ValueError('KNN baseline requires at least one training row.')
    if k > len(train_rows):
        raise ValueError(f'K must not exceed the number of training rows ({len(train_rows)}).')
    validation_rows = _read_numeric_split(artifact_path / 'validation.csv', feature_columns, target_column)
    test_rows = _read_numeric_split(artifact_path / 'test.csv', feature_columns, target_column)
    accuracy = lambda rows: (sum(_knn_predict(train_rows, features, k) == label for features, label in rows) / len(rows)) if rows else None
    created_at = datetime.now(timezone.utc)
    job_seed = hashlib.sha256(f'{artifact_id}:{k}:{created_at.isoformat()}'.encode()).hexdigest()
    job_id = f'job-{created_at.strftime("%Y%m%dT%H%M%S%fZ")}-{job_seed[:12]}'
    jobs_path = artifact_path / _TRAINING_JOBS_DIRECTORY
    jobs_path.mkdir(exist_ok=True)
    destination = jobs_path / job_id
    temporary = Path(tempfile.mkdtemp(prefix=f'.{job_id}-', dir=str(jobs_path)))
    model = {'algorithm': 'knn-classifier', 'artifact_id': artifact_id, 'feature_columns': feature_columns, 'k': k, 'target_column': target_column, 'training_rows': [{'features': features, 'label': label} for features, label in train_rows]}
    model_content = (json.dumps(model, indent=2, ensure_ascii=False) + '\n').encode('utf-8')
    response = {'job_id': job_id, 'artifact_id': artifact_id, 'preparation_id': preparation_id, 'algorithm': 'knn-classifier', 'status': 'completed', 'k': k, 'feature_columns': feature_columns, 'target_column': target_column, 'train_rows': len(train_rows), 'validation_accuracy': accuracy(validation_rows), 'test_accuracy': accuracy(test_rows), 'model_sha256': hashlib.sha256(model_content).hexdigest(), 'created_at': created_at}
    try:
        (temporary / 'model.json').write_bytes(model_content)
        (temporary / 'job.json').write_text(json.dumps({**response, 'created_at': created_at.isoformat(), 'artifact_manifest_sha256': verification['manifest_sha256'], 'schema_version': 1}, indent=2) + '\n', encoding='utf-8')
        os.replace(temporary, destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return response


def list_csv_knn_training_jobs(dataset_name: str, preparation_id: str, artifact_id: str) -> list[dict]:
    jobs_path = _artifact_path(dataset_name, preparation_id, artifact_id) / _TRAINING_JOBS_DIRECTORY
    if not jobs_path.exists():
        return []
    jobs: list[dict] = []
    for path in sorted(jobs_path.iterdir(), reverse=True):
        if not path.is_dir() or not re.match(r'^job-[0-9TZ-]+-[a-f0-9]{12}$', path.name):
            continue
        try:
            job = json.loads((path / 'job.json').read_text(encoding='utf-8'))
            job['created_at'] = datetime.fromisoformat(job['created_at'])
            jobs.append(job)
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            continue
    return jobs


def update_dataset(
    name: str,
    new_name: str | None = None,
    description: str | None = None,
) -> dict:
    path = _dataset_path(name)
    meta = _read_metadata(path)

    if description is not None:
        meta['description'] = description

    if new_name is not None and new_name != name:
        _validate_name(new_name)
        new_path = _datasets_root() / new_name
        if new_path.exists():
            raise ValueError(f'Dataset "{new_name}" already exists.')
        path.rename(new_path)
        path = new_path
        meta['name'] = new_name

    fd, tmp = tempfile.mkstemp(dir=str(path), suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
            json.dump(meta, fh, indent=2)
        os.replace(tmp, str(path / _METADATA_FILENAME))
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise

    updated_meta = _regenerate_metadata(path)
    return _metadata_to_detail(updated_meta)




# ---------------------------------------------------------------------------
# Category CRUD
# ---------------------------------------------------------------------------


def create_category(dataset_name: str, category_name: str) -> dict:
    _validate_name(category_name)
    ds_path = _dataset_path(dataset_name)
    cat_path = ds_path / category_name
    if cat_path.exists():
        raise ValueError(f'Category "{category_name}" already exists.')
    cat_path.mkdir()
    meta = _regenerate_metadata(ds_path)
    return _metadata_to_detail(meta)


def rename_category(dataset_name: str, old_name: str, new_name: str) -> dict:
    _validate_name(new_name)
    cat_path = _category_path(dataset_name, old_name)
    ds_path = cat_path.parent
    new_cat_path = ds_path / new_name
    if new_cat_path.exists():
        raise ValueError(f'Category "{new_name}" already exists.')
    cat_path.rename(new_cat_path)
    meta = _regenerate_metadata(ds_path)
    return _metadata_to_detail(meta)


def delete_category(dataset_name: str, category_name: str) -> dict:
    cat_path = _category_path(dataset_name, category_name)
    ds_path = cat_path.parent
    shutil.rmtree(cat_path)
    meta = _regenerate_metadata(ds_path)
    return _metadata_to_detail(meta)

def delete_dataset(name: str) -> None:
    path = _dataset_path(name)
    resolved = path.resolve()
    root_resolved = _datasets_root().resolve()
    if not str(resolved).startswith(str(root_resolved)):
        raise ValueError('Path traversal detected.')
    shutil.rmtree(path)


# ---------------------------------------------------------------------------
# Image operations
# ---------------------------------------------------------------------------


def _image_info(file_path: Path) -> dict:
    stat = file_path.stat()
    width, height = _read_image_dimensions(file_path)
    return {
        'filename': file_path.name,
        'size_bytes': stat.st_size,
        'media_type': _media_type_from_extension(file_path.name),
        'width_px': width,
        'height_px': height,
        'created_at': datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
    }


def list_images(dataset_name: str, category_name: str) -> list[dict]:
    cat_path = _category_path(dataset_name, category_name)
    result: list[dict] = []
    for entry in sorted(cat_path.iterdir()):
        if entry.is_file() and not entry.name.startswith('.'):
            ext = entry.suffix.lstrip('.').lower()
            if ext in _ALLOWED_EXTENSIONS:
                result.append(_image_info(entry))
    return result


async def upload_images(
    dataset_name: str,
    category_name: str,
    files: list[UploadFile],
) -> list[dict]:
    if len(files) > _MAX_UPLOAD_BATCH:
        raise ValueError(f'Upload batch must not exceed {_MAX_UPLOAD_BATCH} files.')

    cat_path = _category_path(dataset_name, category_name)
    ds_path = cat_path.parent
    uploaded: list[dict] = []

    for upload_file in files:
        filename = upload_file.filename or 'unnamed.png'
        _validate_filename(filename)

        content = await upload_file.read()
        if len(content) > _MAX_FILE_SIZE:
            raise ValueError(
                f'File "{filename}" exceeds the {_MAX_FILE_SIZE // (1024 * 1024)} MB limit.',
            )
        if len(content) == 0:
            raise ValueError(f'File "{filename}" is empty.')

        _validate_magic_bytes(content)

        target = cat_path / filename
        if target.exists():
            stem = filename.rsplit('.', 1)[0]
            ext = filename.rsplit('.', 1)[1]
            counter = 1
            while target.exists():
                target = cat_path / f'{stem}-{counter}.{ext}'
                counter += 1

        fd, tmp_path = tempfile.mkstemp(dir=str(cat_path), suffix='.tmp')
        try:
            with os.fdopen(fd, 'wb') as fh:
                fh.write(content)
            os.replace(tmp_path, str(target))
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise

        uploaded.append(_image_info(target))

    _regenerate_metadata(ds_path)
    return uploaded


def get_image_path(dataset_name: str, category_name: str, filename: str) -> Path:
    _validate_filename(filename)
    cat_path = _category_path(dataset_name, category_name)
    file_path = cat_path / filename
    if not file_path.is_file():
        raise FileNotFoundError(f'Image "{filename}" not found.')
    return file_path


def delete_image(dataset_name: str, category_name: str, filename: str) -> None:
    file_path = get_image_path(dataset_name, category_name, filename)
    ds_path = file_path.parent.parent
    file_path.unlink()
    _regenerate_metadata(ds_path)


def rename_image(
    dataset_name: str,
    category_name: str,
    old_name: str,
    new_name: str,
) -> dict:
    _validate_filename(new_name)
    file_path = get_image_path(dataset_name, category_name, old_name)
    cat_path = file_path.parent
    ds_path = cat_path.parent
    new_path = cat_path / new_name
    if new_path.exists():
        raise ValueError(f'Image "{new_name}" already exists.')
    file_path.rename(new_path)
    _regenerate_metadata(ds_path)
    return _image_info(new_path)


def move_image(
    dataset_name: str,
    category_name: str,
    filename: str,
    target_category: str,
) -> dict:
    _validate_name(target_category)
    file_path = get_image_path(dataset_name, category_name, filename)
    ds_path = file_path.parent.parent
    target_cat_path = ds_path / target_category
    if not target_cat_path.is_dir():
        raise FileNotFoundError(f'Target category "{target_category}" does not exist.')
    target_path = target_cat_path / filename
    if target_path.exists():
        raise ValueError(f'Image "{filename}" already exists in "{target_category}".')
    shutil.move(str(file_path), str(target_path))
    _regenerate_metadata(ds_path)
    return _image_info(target_path)


# ---------------------------------------------------------------------------
# Import captures & Export & List captures
# ---------------------------------------------------------------------------


def import_captures(
    dataset_name: str,
    filenames: list[str],
    target_category: str,
) -> list[dict]:
    _validate_name(target_category)
    ds_path = _dataset_path(dataset_name)
    cat_path = ds_path / target_category
    if not cat_path.is_dir():
        raise FileNotFoundError(
            f'Category "{target_category}" does not exist in dataset "{dataset_name}".',
        )

    captures_root = _captures_root()
    imported: list[dict] = []

    for relative_name in filenames:
        if '..' in relative_name or '\x00' in relative_name:
            raise ValueError(f'Unsafe capture path: {relative_name}')

        source = captures_root / relative_name
        resolved_source = source.resolve()
        if not str(resolved_source).startswith(str(captures_root.resolve())):
            raise ValueError(f'Path traversal detected in capture path: {relative_name}')
        if not source.is_file():
            raise FileNotFoundError(f'Capture file not found: {relative_name}')

        dest_name = source.name
        _validate_filename(dest_name)

        dest = cat_path / dest_name
        if dest.exists():
            stem = dest_name.rsplit('.', 1)[0]
            ext = dest_name.rsplit('.', 1)[1]
            counter = 1
            while dest.exists():
                dest = cat_path / f'{stem}-{counter}.{ext}'
                counter += 1

        shutil.copy2(str(source), str(dest))
        imported.append(_image_info(dest))

    _regenerate_metadata(ds_path)
    return imported


def export_dataset_zip(name: str) -> BytesIO:
    ds_path = _dataset_path(name)
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root_dir, _dirs, files in os.walk(ds_path):
            for file_name in sorted(files):
                if file_name == _METADATA_FILENAME:
                    continue
                abs_path = Path(root_dir) / file_name
                arc_name = str(abs_path.relative_to(ds_path))
                zf.write(abs_path, arc_name)
    buffer.seek(0)
    return buffer


def list_captures() -> list[dict]:
    root = _captures_root()
    result: list[dict] = []
    for file_path in sorted(root.rglob('*')):
        if not file_path.is_file() or file_path.name.startswith('.'):
            continue
        ext = file_path.suffix.lstrip('.').lower()
        if ext not in _ALLOWED_EXTENSIONS:
            continue
        result.append({
            'relative_path': str(file_path.relative_to(root)),
            'filename': file_path.name,
            'size_bytes': file_path.stat().st_size,
        })
    return result
