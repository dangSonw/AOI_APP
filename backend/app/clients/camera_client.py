import hashlib
from dataclasses import dataclass

import httpx

from core.devices.camera import CameraCapabilities, CameraConfiguration, CaptureRequest, CaptureResult

from .device_client import DeviceClient, DeviceServiceError


MAXIMUM_INSPECTION_IMAGE_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class InspectionImage:
    content: bytes
    media_type: str
    sha256: str


class CameraClient(DeviceClient):
    def health(self):
        health = super().health()
        if health.service != 'camera':
            raise DeviceServiceError('The configured adapter is not a camera service.', 502)
        return health

    def capabilities(self) -> CameraCapabilities:
        self.require_ready()
        return self.get_model('/capabilities', CameraCapabilities)

    def configuration(self) -> CameraConfiguration:
        self.require_ready()
        return self.get_model('/configuration', CameraConfiguration)

    def configure(self, configuration: CameraConfiguration) -> CameraConfiguration:
        self.require_ready()
        return self.put_model('/configuration', configuration, CameraConfiguration)

    def preview(self) -> InspectionImage:
        self.require_ready()
        response = self.get_bytes('/preview', MAXIMUM_INSPECTION_IMAGE_BYTES)
        media_type = response.headers.get('content-type', '').split(';', 1)[0].strip().lower()
        if media_type not in {'image/png', 'image/tiff'}:
            raise DeviceServiceError('The camera returned an unsupported preview image type.', 502)
        checksum = hashlib.sha256(response.content).hexdigest()
        return InspectionImage(response.content, media_type, checksum)

    def capture(self, request: CaptureRequest) -> CaptureResult:
        self.require_ready()
        result = self.post_model('/captures', request, CaptureResult)
        expected_path = f'/captures/{result.capture_id}/inspection-image'
        if result.inspection_image_url != expected_path:
            raise DeviceServiceError('The camera returned an unsafe inspection image URL.', 502)
        self.inspection_image(result.capture_id, expected_sha256=result.sha256, expected_bytes=result.byte_length)
        return result

    def inspection_image(
        self,
        capture_id: str,
        *,
        expected_sha256: str | None = None,
        expected_bytes: int | None = None,
    ) -> InspectionImage:
        response = self.get_bytes(
            f'/captures/{capture_id}/inspection-image',
            MAXIMUM_INSPECTION_IMAGE_BYTES,
        )
        media_type = response.headers.get('content-type', '').split(';', 1)[0].strip().lower()
        if media_type not in {'image/png', 'image/tiff'}:
            raise DeviceServiceError('The camera returned an unsupported inspection image type.', 502)
        if expected_bytes is not None and len(response.content) != expected_bytes:
            raise DeviceServiceError('The inspection image byte length does not match its metadata.', 502)
        checksum = hashlib.sha256(response.content).hexdigest()
        if expected_sha256 is not None and checksum != expected_sha256:
            raise DeviceServiceError('The inspection image checksum does not match its metadata.', 502)
        return InspectionImage(response.content, media_type, checksum)