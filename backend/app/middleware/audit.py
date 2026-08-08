import logging
import re
from uuid import uuid4

import jwt
from jwt.exceptions import InvalidTokenError
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config.settings import get_settings
from app.database.session import SessionLocal
from app.services.audit_service import record_audit_event


logger = logging.getLogger(__name__)

AUDITED_METHODS = {'POST', 'PUT', 'PATCH', 'DELETE'}
ACTION_BY_METHOD = {
    'POST': 'create',
    'PUT': 'update',
    'PATCH': 'update',
    'DELETE': 'delete',
}
REQUEST_ID_PATTERN = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')


def _request_id(request: Request) -> str:
    supplied_request_id = request.headers.get('X-Request-ID', '')
    if REQUEST_ID_PATTERN.fullmatch(supplied_request_id):
        return supplied_request_id
    return str(uuid4())


def _verified_actor_id(request: Request) -> int | None:
    authorization = request.headers.get('Authorization', '')
    scheme, separator, token = authorization.partition(' ')
    if not separator or scheme.lower() != 'bearer' or not token:
        return None

    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return int(payload['sub'])
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        return None


def _resource_parts(path: str) -> tuple[str, str | None]:
    parts = [part for part in path.split('/') if part]
    if parts and parts[0] == 'api':
        parts = parts[1:]
    resource_type = parts[0] if parts else 'application'
    resource_id = parts[1] if len(parts) > 1 else None
    return resource_type, resource_id


class AuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = _request_id(request)
        request.state.request_id = request_id
        actor_id = _verified_actor_id(request)
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            if request.method in AUDITED_METHODS:
                self._record(request, request_id, actor_id, status_code)
            raise

        response.headers['X-Request-ID'] = request_id
        if request.method in AUDITED_METHODS and not getattr(request.state, 'audit_recorded', False):
            self._record(request, request_id, actor_id, status_code)
        return response

    @staticmethod
    def _record(request: Request, request_id: str, actor_id: int | None, status_code: int) -> None:
        resource_type, resource_id = _resource_parts(request.url.path)
        try:
            with SessionLocal() as session:
                record_audit_event(session, {
                    'actor_id': actor_id,
                    'action': ACTION_BY_METHOD[request.method],
                    'method': request.method,
                    'path': request.url.path,
                    'resource_type': resource_type,
                    'resource_id': resource_id,
                    'request_id': request_id,
                    'status_code': status_code,
                    'result': 'success' if status_code < 400 else 'failure',
                })
        except Exception:
            logger.exception('Audit event could not be persisted for request %s.', request_id)