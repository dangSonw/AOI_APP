from collections.abc import Mapping
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent


def record_audit_event(session: Session, event_data: Mapping[str, Any]) -> AuditEvent:
    event = AuditEvent(**event_data)
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def list_audit_events(
    session: Session,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[AuditEvent], int]:
    bounded_page = max(1, page)
    bounded_page_size = min(100, max(1, page_size))
    total = session.scalar(select(func.count()).select_from(AuditEvent)) or 0
    events = list(session.scalars(
        select(AuditEvent)
        .order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc())
        .offset((bounded_page - 1) * bounded_page_size)
        .limit(bounded_page_size)
    ))
    return events, total