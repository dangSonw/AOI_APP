import hashlib
import os
import struct
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import Field

from core.devices.camera import CameraConfiguration, CaptureRequest, CaptureResult
from core.devices.models import ContractModel


MAX_SOURCE_IMAGE_BYTES = 16 * 1024 * 1024
SAFE_IDENTIFIER_PATTERN = r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$'
CameraSourceMode = Literal['test-pattern', 'uploaded']
CameraFault = Literal['none', 'failed-frame', 'unavailable', 'checksum-mismatch']


class CameraSimulationConfiguration(ContractModel):
    source_mode: CameraSourceMode = 'test-pattern'
    selected_image_id: str | None = Field(default=None, pattern=r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')
    frame_delay_milliseconds: int = Field(default=0, ge=0, le=10_000)
    fault: CameraFault = 'none'


class SourceImage(ContractModel):
    image_id: str
    filename: str
    media_type: str
    byte_length: int
    sha256: str
    width: int
    height: int


class CameraSimulationError(RuntimeError):
    pass


def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
    body = chunk_type + data
    return struct.pack('>I', len(data)) + body + struct.pack('>I', zlib.crc32(body) & 0xFFFFFFFF)


def create_test_pattern_png() -> bytes:
    width = 2
    height = 2
    raw_rows = b'\x00\x00\x00\x00\xff\xff\xff' + b'\x00\xff\x00\x00\x00\xff\x00'
    return (
        b'\x89PNG\r\n\x1a\n'
        + _png_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b'IDAT', zlib.compress(raw_rows))
        + _png_chunk(b'IEND', b'')
    )


class ReplayCaptureService:
    def __init__(self, capture_directory: Path) -> None:
        self.capture_directory = capture_directory
        self.source_directory = capture_directory / 'sources'
        self.configuration = CameraSimulationConfiguration()
        self.camera_configuration = CameraConfiguration(
            camera_id='top-camera',
            sensor_mode='3280x2464',
            exposure_microseconds=8000,
            analog_gain=1,
        )
        self._results: dict[str, CaptureResult] = {}

    def configure(self, configuration: CameraSimulationConfiguration) -> CameraSimulationConfiguration:
        if configuration.source_mode == 'uploaded':
            if configuration.selected_image_id is None:
                raise ValueError('An uploaded source image must be selected.')
            self.source_image(configuration.selected_image_id)
        self.configuration = configuration
        return configuration

    def configure_camera(self, configuration: CameraConfiguration) -> CameraConfiguration:
        self.camera_configuration = configuration
        return configuration

    def upload_source(self, image_id: str, filename: str, media_type: str, image_bytes: bytes) -> SourceImage:
        validate_identifier(image_id, 'image ID')
        if media_type != 'image/png' or not filename.lower().endswith('.png'):
            raise TypeError('Only PNG source images are supported.')
        if len(image_bytes) > MAX_SOURCE_IMAGE_BYTES:
            raise OverflowError('The source image exceeds the 16 MiB limit.')
        width, height = png_dimensions(image_bytes)
        self.source_directory.mkdir(parents=True, exist_ok=True)
        artifact_path = self.source_directory / f'{image_id}.png'
        temporary_path = artifact_path.with_suffix('.png.tmp')
        _atomic_write(temporary_path, artifact_path, image_bytes)
        return SourceImage(
            image_id=image_id,
            filename=Path(filename).name,
            media_type=media_type,
            byte_length=len(image_bytes),
            sha256=hashlib.sha256(image_bytes).hexdigest(),
            width=width,
            height=height,
        )

    def list_sources(self) -> list[SourceImage]:
        if not self.source_directory.exists():
            return []
        return [self.source_image(path.stem) for path in sorted(self.source_directory.glob('*.png'))]

    def source_image(self, image_id: str) -> SourceImage:
        validate_identifier(image_id, 'image ID')
        path = self.source_directory / f'{image_id}.png'
        if not path.is_file():
            raise FileNotFoundError('The selected source image does not exist.')
        image_bytes = path.read_bytes()
        width, height = png_dimensions(image_bytes)
        return SourceImage(
            image_id=image_id,
            filename=path.name,
            media_type='image/png',
            byte_length=len(image_bytes),
            sha256=hashlib.sha256(image_bytes).hexdigest(),
            width=width,
            height=height,
        )

    def preview_bytes(self) -> bytes:
        return self._source_bytes()[0]

    def capture(self, request: CaptureRequest) -> CaptureResult:
        existing = self._results.get(request.request_id)
        if existing is not None:
            return existing
        if self.configuration.fault in {'failed-frame', 'unavailable'}:
            raise CameraSimulationError(f'Injected camera fault: {self.configuration.fault}.')
        if self.configuration.frame_delay_milliseconds:
            time.sleep(self.configuration.frame_delay_milliseconds / 1000)
        self.capture_directory.mkdir(parents=True, exist_ok=True)
        capture_id = request.request_id
        artifact_path = self.capture_directory / f'{capture_id}.png'
        temporary_path = artifact_path.with_suffix('.png.tmp')
        image_bytes, width, height = self._source_bytes()
        try:
            _atomic_write(temporary_path, artifact_path, image_bytes)
        except OSError:
            temporary_path.unlink(missing_ok=True)
            raise
        checksum = hashlib.sha256(image_bytes).hexdigest()
        if self.configuration.fault == 'checksum-mismatch':
            checksum = '0' * 64
        result = CaptureResult(
            capture_id=capture_id,
            request_id=request.request_id,
            status='ready',
            camera_id=request.camera_id,
            sensor_model='simulated-imx219',
            captured_at=datetime.now(timezone.utc),
            monotonic_timestamp_nanoseconds=time.monotonic_ns(),
            width=width,
            height=height,
            pixel_format='rgb8',
            position=request.expected_position,
            exposure_microseconds=request.exposure_microseconds,
            analog_gain=request.analog_gain,
            media_type='image/png',
            byte_length=len(image_bytes),
            sha256=checksum,
            inspection_image_url=f'/captures/{capture_id}/inspection-image',
        )
        self._results[request.request_id] = result
        return result

    def artifact_path(self, capture_id: str) -> Path:
        validate_identifier(capture_id, 'capture ID')
        return self.capture_directory / f'{capture_id}.png'

    def _source_bytes(self) -> tuple[bytes, int, int]:
        if self.configuration.source_mode == 'test-pattern':
            image_bytes = create_test_pattern_png()
            width, height = png_dimensions(image_bytes)
            return image_bytes, width, height
        source = self.source_image(self.configuration.selected_image_id or '')
        image_bytes = (self.source_directory / f'{source.image_id}.png').read_bytes()
        return image_bytes, source.width, source.height


def png_dimensions(image_bytes: bytes) -> tuple[int, int]:
    if len(image_bytes) < 24 or image_bytes[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('The uploaded content is not a valid PNG image.')
    width, height = struct.unpack('>II', image_bytes[16:24])
    if width <= 0 or height <= 0:
        raise ValueError('The PNG dimensions are invalid.')
    return width, height


def validate_identifier(identifier: str, label: str) -> None:
    import re

    if re.fullmatch(SAFE_IDENTIFIER_PATTERN, identifier) is None:
        raise ValueError(f'The {label} contains unsupported characters.')


def _atomic_write(temporary_path: Path, artifact_path: Path, image_bytes: bytes) -> None:
    with temporary_path.open('wb') as artifact_file:
        artifact_file.write(image_bytes)
        artifact_file.flush()
        os.fsync(artifact_file.fileno())
    temporary_path.replace(artifact_path)