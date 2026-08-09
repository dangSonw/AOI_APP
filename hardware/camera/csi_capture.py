from __future__ import annotations

import hashlib
import shutil
import struct
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from core.devices.camera import CameraConfiguration, CaptureRequest, CaptureResult


class CsiCaptureError(RuntimeError):
    pass


Runner = Callable[[list[str], float], None]


def _default_runner(argv: list[str], timeout_seconds: float) -> None:
    try:
        subprocess.run(argv, check=True, timeout=timeout_seconds, capture_output=True)
    except (OSError, subprocess.SubprocessError) as error:
        raise CsiCaptureError('Jetson CSI capture command failed.') from error


class JetsonCsiCaptureService:
    def __init__(
        self,
        capture_directory: Path,
        *,
        runner: Runner = _default_runner,
        pipeline_available: Callable[[], bool] | None = None,
    ) -> None:
        self.capture_directory = capture_directory
        self.runner = runner
        self.pipeline_available = pipeline_available or (lambda: shutil.which('gst-launch-1.0') is not None)
        self.configuration = CameraConfiguration(
            camera_id='top-camera', sensor_mode='3280x2464',
            exposure_microseconds=8000, analog_gain=1,
        )

    @property
    def is_available(self) -> bool:
        return self.pipeline_available()

    def configure(self, configuration: CameraConfiguration) -> CameraConfiguration:
        if not configuration.sensor_mode.replace('x', '').isdigit() or configuration.sensor_mode.count('x') != 1:
            raise CsiCaptureError('Unsupported CSI sensor mode.')
        width, height = (int(value) for value in configuration.sensor_mode.split('x'))
        if width <= 0 or height <= 0 or width > 10000 or height > 10000:
            raise CsiCaptureError('Unsupported CSI sensor mode.')
        self.configuration = configuration
        return configuration

    def artifact_path(self, capture_id: str) -> Path:
        return self.capture_directory / f'{capture_id}.png'

    def capture(self, request: CaptureRequest) -> CaptureResult:
        if not self.pipeline_available():
            raise CsiCaptureError('Jetson CSI pipeline is unavailable.')
        self.configure(CameraConfiguration(
            camera_id=request.camera_id, sensor_mode=request.sensor_mode,
            exposure_microseconds=request.exposure_microseconds, analog_gain=request.analog_gain,
        ))
        self.capture_directory.mkdir(parents=True, exist_ok=True)
        destination = self.artifact_path(request.request_id)
        temporary = destination.with_suffix('.png.tmp')
        width, height = (int(value) for value in request.sensor_mode.split('x'))
        argv = [
            'gst-launch-1.0', '-q', 'nvarguscamerasrc',
            f'exposuretimerange={request.exposure_microseconds} {request.exposure_microseconds}',
            '!', f'video/x-raw(memory:NVMM),width={width},height={height},format=NV12',
            '!', 'nvvidconv', '!', 'pngenc', '!', 'filesink', f'location={temporary}',
        ]
        try:
            self.runner(argv, 15.0)
            content = temporary.read_bytes()
            if len(content) < 24 or content[:8] != b'\x89PNG\r\n\x1a\n':
                raise CsiCaptureError('CSI output is not a complete lossless PNG artifact.')
            actual_width, actual_height = struct.unpack('>II', content[16:24])
            temporary.replace(destination)
        except (OSError, ValueError):
            temporary.unlink(missing_ok=True)
            raise CsiCaptureError('CSI capture artifact could not be published.')
        except CsiCaptureError:
            temporary.unlink(missing_ok=True)
            raise
        checksum = hashlib.sha256(content).hexdigest()
        return CaptureResult(
            capture_id=request.request_id, request_id=request.request_id, status='ready',
            camera_id=request.camera_id, sensor_model='jetson-csi', captured_at=datetime.now(timezone.utc),
            monotonic_timestamp_nanoseconds=time.monotonic_ns(), width=actual_width, height=actual_height,
            pixel_format='rgb8', position=request.expected_position,
            exposure_microseconds=request.exposure_microseconds, analog_gain=request.analog_gain,
            media_type='image/png', byte_length=len(content), sha256=checksum,
            inspection_image_url=f'/captures/{request.request_id}/inspection-image',
        )