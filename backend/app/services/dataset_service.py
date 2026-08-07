"""Dataset filesystem service.

Manages datasets as directories under ``data/datasets/`` with a companion
``metadata.json`` descriptor that is regenerated after every mutation.
"""

from __future__ import annotations

import json
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
_METADATA_FILENAME = 'metadata.json'


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
        if not entry.is_dir() or entry.name.startswith('.'):
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
