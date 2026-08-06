from collections.abc import Mapping
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from core.devices.models import DeviceStatus, HealthResponse, PROTOCOL_VERSION


ResponseModel = TypeVar('ResponseModel', bound=BaseModel)


class DeviceServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.status_code = status_code


class DeviceClient:
    def __init__(
        self,
        base_url: str,
        *,
        transport: httpx.BaseTransport | None = None,
        connect_timeout_seconds: float = 1.0,
        read_timeout_seconds: float = 10.0,
        write_timeout_seconds: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip('/')
        self._client = httpx.Client(
            base_url=self.base_url,
            transport=transport,
            timeout=httpx.Timeout(
                connect=connect_timeout_seconds,
                read=read_timeout_seconds,
                write=write_timeout_seconds,
                pool=connect_timeout_seconds,
            ),
        )

    @property
    def is_closed(self) -> bool:
        return self._client.is_closed

    def close(self) -> None:
        self._client.close()

    def health(self) -> HealthResponse:
        health = self.get_model('/health', HealthResponse)
        if health.protocol_version != PROTOCOL_VERSION:
            raise DeviceServiceError(
                f'The device adapter protocol is incompatible; expected {PROTOCOL_VERSION}.',
            )
        return health

    def require_ready(self) -> HealthResponse:
        health = self.health()
        if health.status is not DeviceStatus.READY:
            raise DeviceServiceError('The device adapter is not ready.', 503)
        return health

    def get_model(self, path: str, model_type: type[ResponseModel]) -> ResponseModel:
        response = self._request('GET', path)
        return self._parse_model(response, model_type)

    def post_model(
        self,
        path: str,
        request: BaseModel,
        model_type: type[ResponseModel],
    ) -> ResponseModel:
        response = self._request(
            'POST',
            path,
            json=request.model_dump(mode='json', by_alias=True),
        )
        return self._parse_model(response, model_type)

    def put_model(
        self,
        path: str,
        request: BaseModel,
        model_type: type[ResponseModel],
    ) -> ResponseModel:
        response = self._request(
            'PUT',
            path,
            json=request.model_dump(mode='json', by_alias=True),
        )
        return self._parse_model(response, model_type)

    def get_bytes(self, path: str, maximum_bytes: int) -> httpx.Response:
        response = self._request('GET', path)
        if len(response.content) > maximum_bytes:
            raise DeviceServiceError('The device artifact exceeds the configured size limit.', 502)
        return response

    def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        try:
            response = self._client.request(method, path, **kwargs)
            response.raise_for_status()
            return response
        except httpx.TimeoutException as error:
            raise DeviceServiceError('The device adapter request timed out.', 504) from error
        except httpx.NetworkError as error:
            raise DeviceServiceError('The device adapter is unavailable.', 503) from error
        except httpx.HTTPStatusError as error:
            status_code = error.response.status_code
            detail = self._safe_error_detail(error.response)
            if 400 <= status_code < 500:
                raise DeviceServiceError(detail, status_code) from error
            raise DeviceServiceError('The device adapter could not complete the request.', 502) from error

    @staticmethod
    def _parse_model(response: httpx.Response, model_type: type[ResponseModel]) -> ResponseModel:
        try:
            return model_type.model_validate(response.json())
        except (ValueError, ValidationError) as error:
            raise DeviceServiceError('The device adapter returned an invalid response.', 502) from error

    @staticmethod
    def _safe_error_detail(response: httpx.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return 'The device adapter rejected the request.'
        if isinstance(payload, Mapping):
            detail = payload.get('detail')
            if isinstance(detail, str) and 0 < len(detail) <= 500:
                return detail
        return 'The device adapter rejected the request.'