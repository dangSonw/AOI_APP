from fastapi import APIRouter, Query

from app.auth.dependencies import CurrentUser, DatabaseSession
from app.schemas.audit import AuditEventListResponse, AuditEventResponse
from app.services.audit_service import list_audit_events


router = APIRouter(prefix='/api/audit-events', tags=['audit'])


@router.get('', response_model=AuditEventListResponse)
def get_audit_events(
    _: CurrentUser,
    session: DatabaseSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> AuditEventListResponse:
    events, total = list_audit_events(session, page=page, page_size=page_size)
    return AuditEventListResponse(
        events=[AuditEventResponse.model_validate(event) for event in events],
        total=total,
        page=page,
        page_size=page_size,
    )