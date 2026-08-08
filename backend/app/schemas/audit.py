from datetime import datetime

from app.schemas.base import ApiSchema


class AuditEventResponse(ApiSchema):
    id: int
    actor_id: int | None
    action: str
    method: str
    path: str
    resource_type: str
    resource_id: str | None
    request_id: str
    status_code: int
    result: str
    created_at: datetime


class AuditEventListResponse(ApiSchema):
    events: list[AuditEventResponse]
    total: int
    page: int
    page_size: int