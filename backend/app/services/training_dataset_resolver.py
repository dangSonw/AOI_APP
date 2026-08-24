from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import tempfile
from typing import Any, Literal

from app.services import dataset_service
from core.training.contracts import DatasetBinding


MAX_DATASET_ITEMS = 10_000
MAX_DATASET_BYTES = 2 * 1024 * 1024 * 1024
MAX_DECODED_PIXELS = 500_000_000
ALLOWED_LOGICAL_MEDIA_TYPES = frozenset({'image/png', 'image/jpeg'})
ALLOWED_SPLITS = frozenset({'train', 'validation', 'test'})
_VERSIONS_DIRECTORY = '.versions'
_MANIFEST_FILENAME = 'manifest.json'
_RESERVED_DATASET_DIRECTORIES = frozenset({'preparations', 'artifacts', 'training-jobs'})


class DatasetIntegrityError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ImmutableDatasetItem:
    logical_path: str
    path: Path
    sha256: str
    media_type: str
    byte_length: int
    width_px: int
    height_px: int
    class_name: str
    class_id: int
    split: Literal['train', 'validation', 'test']

    def public_metadata(self) -> dict[str, Any]:
        return {
            'logicalPath': self.logical_path,
            'sha256': self.sha256,
            'mediaType': self.media_type,
            'byteLength': self.byte_length,
            'widthPx': self.width_px,
            'heightPx': self.height_px,
            'className': self.class_name,
            'classId': self.class_id,
            'split': self.split,
        }


@dataclass(frozen=True, slots=True)
class ImmutableDatasetHandle:
    dataset_id: str
    version: str
    class_mapping: dict[str, int]
    items: tuple[ImmutableDatasetItem, ...]

    def public_metadata(self) -> dict[str, Any]:
        return {
            'datasetId': self.dataset_id,
            'version': self.version,
            'classMapping': dict(self.class_mapping),
            'itemCount': len(self.items),
            'items': [item.public_metadata() for item in self.items],
        }


def _canonical_manifest_bytes(manifest: dict[str, Any]) -> bytes:
    return json.dumps(manifest, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('utf-8')


def _manifest_version(manifest: dict[str, Any]) -> str:
    return 'sha256:' + hashlib.sha256(_canonical_manifest_bytes(manifest)).hexdigest()


def _safe_logical_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if (
        not value
        or '\\' in value
        or path.is_absolute()
        or len(path.parts) != 2
        or any(part in {'', '.', '..'} or part.startswith('.') for part in path.parts)
    ):
        raise DatasetIntegrityError(f'Unsafe dataset logical path: {value!r}.')
    return path


def _scan_live_dataset(
    dataset_path: Path,
    class_mapping: dict[str, int] | None,
    split_by_item: dict[str, str] | None,
) -> tuple[dict[str, Any], list[tuple[Path, str]]]:
    categories = sorted(
        entry.name for entry in dataset_path.iterdir()
        if (
            entry.is_dir()
            and not entry.name.startswith('.')
            and entry.name not in _RESERVED_DATASET_DIRECTORIES
        )
    )
    if not categories:
        raise ValueError('Dataset must contain at least one class category.')

    effective_mapping = class_mapping or {name: index for index, name in enumerate(categories)}
    if set(effective_mapping) != set(categories):
        raise ValueError('Class mapping must contain every dataset category exactly once.')
    if set(effective_mapping.values()) != set(range(len(categories))):
        raise ValueError('Class mapping IDs must be unique and contiguous from zero.')

    source_items: list[tuple[Path, str]] = []
    item_records: list[dict[str, Any]] = []
    total_bytes = 0
    total_pixels = 0
    for category in categories:
        category_path = dataset_path / category
        if category_path.is_symlink():
            raise DatasetIntegrityError('Dataset category symlinks are not allowed.')
        for source_path in sorted(category_path.iterdir()):
            if not source_path.is_file() or source_path.name.startswith('.'):
                continue
            if source_path.is_symlink():
                raise DatasetIntegrityError('Dataset item symlinks are not allowed.')
            dataset_service._validate_filename(source_path.name)
            logical_path = f'{category}/{source_path.name}'
            _safe_logical_path(logical_path)
            content = source_path.read_bytes()
            media_type = dataset_service._validate_magic_bytes(content)
            expected_media_type = dataset_service._media_type_from_extension(source_path.name)
            if media_type != expected_media_type or media_type not in ALLOWED_LOGICAL_MEDIA_TYPES:
                raise ValueError(f'Unsupported or mismatched logical media type for {logical_path}.')
            width, height = dataset_service._read_image_dimensions(source_path)
            if width is None or height is None or width < 1 or height < 1:
                raise ValueError(f'Image dimensions could not be read for {logical_path}.')

            total_bytes += len(content)
            total_pixels += width * height
            if len(item_records) + 1 > MAX_DATASET_ITEMS:
                raise ValueError(f'Dataset exceeds the {MAX_DATASET_ITEMS} item limit.')
            if total_bytes > MAX_DATASET_BYTES:
                raise ValueError('Dataset exceeds the byte limit.')
            if total_pixels > MAX_DECODED_PIXELS:
                raise ValueError('Dataset exceeds the decoded-pixel limit.')

            split = (split_by_item or {}).get(logical_path, 'train')
            if split not in ALLOWED_SPLITS:
                raise ValueError(f'Unsupported split {split!r} for {logical_path}.')
            item_records.append({
                'logicalPath': logical_path,
                'sha256': hashlib.sha256(content).hexdigest(),
                'mediaType': media_type,
                'byteLength': len(content),
                'widthPx': width,
                'heightPx': height,
                'className': category,
                'classId': effective_mapping[category],
                'split': split,
            })
            source_items.append((source_path, logical_path))

    logical_paths = {record['logicalPath'] for record in item_records}
    if split_by_item is not None and set(split_by_item) != logical_paths:
        raise ValueError('Explicit split metadata must contain every dataset item exactly once.')
    if not item_records:
        raise ValueError('Dataset must contain at least one supported image item.')

    manifest = {
        'schemaVersion': 1,
        'datasetId': dataset_path.name,
        'classMapping': dict(sorted(effective_mapping.items())),
        'itemCount': len(item_records),
        'totalSizeBytes': total_bytes,
        'totalDecodedPixels': total_pixels,
        'items': item_records,
    }
    return manifest, source_items


def create_immutable_dataset_version(
    dataset_id: str,
    *,
    class_mapping: dict[str, int] | None = None,
    split_by_item: dict[str, str] | None = None,
) -> DatasetBinding:
    dataset_path = dataset_service._dataset_path(dataset_id)
    manifest, source_items = _scan_live_dataset(dataset_path, class_mapping, split_by_item)
    binding = DatasetBinding(dataset_id=dataset_id, version=_manifest_version(manifest))
    digest = binding.version.removeprefix('sha256:')
    versions_path = dataset_path / _VERSIONS_DIRECTORY
    versions_path.mkdir(exist_ok=True)
    target_path = versions_path / digest

    if target_path.exists():
        try:
            resolve_immutable_dataset(binding)
            return binding
        except (DatasetIntegrityError, FileNotFoundError, OSError, ValueError):
            shutil.rmtree(target_path)

    temporary_path = Path(tempfile.mkdtemp(prefix=f'.{digest}.', dir=versions_path))
    try:
        items_path = temporary_path / 'items'
        for source_path, logical_path in source_items:
            destination = items_path.joinpath(*PurePosixPath(logical_path).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, destination)
        (temporary_path / _MANIFEST_FILENAME).write_bytes(_canonical_manifest_bytes(manifest))
        temporary_path.rename(target_path)
    except Exception:
        shutil.rmtree(temporary_path, ignore_errors=True)
        raise
    return binding


def resolve_immutable_dataset(
    binding: DatasetBinding,
    *,
    verify_manifest_hash: bool = True,
) -> ImmutableDatasetHandle:
    validated_binding = DatasetBinding(dataset_id=binding.dataset_id, version=binding.version)
    dataset_path = dataset_service._dataset_path(validated_binding.dataset_id)
    digest = validated_binding.version.removeprefix('sha256:')
    version_path = dataset_path / _VERSIONS_DIRECTORY / digest
    if not version_path.is_dir():
        raise FileNotFoundError(
            f'Dataset version {validated_binding.version} does not exist for {validated_binding.dataset_id}.',
        )
    manifest_path = version_path / _MANIFEST_FILENAME
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        raise DatasetIntegrityError('Dataset version manifest is missing or malformed.') from error
    if not isinstance(manifest, dict) or manifest.get('schemaVersion') != 1:
        raise DatasetIntegrityError('Unsupported dataset version manifest schema.')
    if manifest.get('datasetId') != validated_binding.dataset_id:
        raise DatasetIntegrityError('Dataset version manifest ID does not match its binding.')
    if verify_manifest_hash and _manifest_version(manifest) != validated_binding.version:
        raise DatasetIntegrityError('Dataset version manifest hash does not match its binding.')

    raw_mapping = manifest.get('classMapping')
    raw_items = manifest.get('items')
    if not isinstance(raw_mapping, dict) or not isinstance(raw_items, list):
        raise DatasetIntegrityError('Dataset version manifest metadata is malformed.')
    try:
        class_mapping = {str(name): int(class_id) for name, class_id in raw_mapping.items()}
    except (TypeError, ValueError) as error:
        raise DatasetIntegrityError('Dataset version manifest metadata is malformed.') from error
    if len(raw_items) != manifest.get('itemCount') or len(raw_items) > MAX_DATASET_ITEMS:
        raise DatasetIntegrityError('Dataset version item count is invalid or exceeds its limit.')

    resolved_items: list[ImmutableDatasetItem] = []
    total_bytes = 0
    total_pixels = 0
    items_root = (version_path / 'items').resolve()
    for record in raw_items:
        if not isinstance(record, dict):
            raise DatasetIntegrityError('Dataset version item metadata is malformed.')
        logical = _safe_logical_path(str(record.get('logicalPath', '')))
        item_path = items_root.joinpath(*logical.parts).resolve()
        if items_root not in item_path.parents or not item_path.is_file() or item_path.is_symlink():
            raise DatasetIntegrityError(f'Dataset item logical path escapes its immutable snapshot: {logical}.')
        content = item_path.read_bytes()
        checksum = hashlib.sha256(content).hexdigest()
        if checksum != record.get('sha256'):
            raise DatasetIntegrityError(f'Dataset item checksum mismatch: {logical}.')
        if len(content) != record.get('byteLength'):
            raise DatasetIntegrityError(f'Dataset item byte length mismatch: {logical}.')
        media_type = str(record.get('mediaType', ''))
        if media_type not in ALLOWED_LOGICAL_MEDIA_TYPES:
            raise DatasetIntegrityError(f'Dataset item media type is unsupported: {logical}.')
        try:
            width = int(record.get('widthPx', 0))
            height = int(record.get('heightPx', 0))
            class_name = str(record.get('className', ''))
            class_id = int(record.get('classId', -1))
        except (TypeError, ValueError) as error:
            raise DatasetIntegrityError('Dataset version item metadata is malformed.') from error
        split = str(record.get('split', ''))
        if width < 1 or height < 1 or class_mapping.get(class_name) != class_id or split not in ALLOWED_SPLITS:
            raise DatasetIntegrityError(f'Dataset item integrity metadata is invalid: {logical}.')
        total_bytes += len(content)
        total_pixels += width * height
        if total_bytes > MAX_DATASET_BYTES or total_pixels > MAX_DECODED_PIXELS:
            raise DatasetIntegrityError('Dataset version exceeds bounded resource limits.')
        resolved_items.append(ImmutableDatasetItem(
            logical_path=str(logical), path=item_path, sha256=checksum, media_type=media_type,
            byte_length=len(content), width_px=width, height_px=height,
            class_name=class_name, class_id=class_id, split=split,  # type: ignore[arg-type]
        ))

    if total_bytes != manifest.get('totalSizeBytes') or total_pixels != manifest.get('totalDecodedPixels'):
        raise DatasetIntegrityError('Dataset version aggregate integrity metadata does not match its items.')
    return ImmutableDatasetHandle(
        dataset_id=validated_binding.dataset_id,
        version=validated_binding.version,
        class_mapping=class_mapping,
        items=tuple(resolved_items),
    )