from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent
from app.services.audit_service import list_audit_events, record_audit_event


def test_record_audit_event_persists_security_metadata_without_request_content() -> None:
    engine = create_engine('sqlite+pysqlite:///:memory:')
    AuditEvent.__table__.create(engine)

    with Session(engine) as session:
        event = record_audit_event(session, {
            'actor_id': 7,
            'action': 'update',
            'method': 'PUT',
            'path': '/api/workstation-preferences/station-01',
            'resource_type': 'workstation-preferences',
            'resource_id': 'station-01',
            'request_id': 'request-001',
            'status_code': 200,
            'result': 'success',
        })
        persisted = session.get(AuditEvent, event.id)

    assert persisted is not None
    assert persisted.actor_id == 7
    assert persisted.action == 'update'
    assert persisted.result == 'success'
    assert persisted.request_id == 'request-001'
    assert not hasattr(persisted, 'request_body')
    assert not hasattr(persisted, 'authorization')


def test_list_audit_events_returns_newest_events_with_bounded_pagination() -> None:
    engine = create_engine('sqlite+pysqlite:///:memory:')
    AuditEvent.__table__.create(engine)

    with Session(engine) as session:
        for index in range(3):
            record_audit_event(session, {
                'actor_id': 7,
                'action': 'update',
                'method': 'PUT',
                'path': f'/api/workstation-preferences/station-0{index + 1}',
                'resource_type': 'workstation-preferences',
                'resource_id': f'station-0{index + 1}',
                'request_id': f'request-00{index + 1}',
                'status_code': 200,
                'result': 'success',
            })

        events, total = list_audit_events(session, page=1, page_size=2)

    assert total == 3
    assert [event.request_id for event in events] == ['request-003', 'request-002']