from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.settings_document import SettingsDocument
from app.models.settings_version import SettingsVersion
from app.services.settings_diff import settings_checksum, settings_diff
from app.services.settings_schema_registry import validate_settings_payload


SettingsScope = Literal['user', 'workstation', 'recipe', 'system']


@dataclass(frozen=True)
class SettingsIdentity:
    scope: SettingsScope
    subject_id: str
    document_key: str
    owner_user_id: int | None


class SettingsRevisionConflict(RuntimeError):
    def __init__(
        self,
        expected_revision: int,
        current: SettingsVersion | None,
        submitted_payload: dict[str, Any],
    ) -> None:
        self.expected_revision = expected_revision
        self.current_revision = current.revision if current is not None else 0
        self.current_checksum = current.checksum if current is not None else None
        self.differences = settings_diff(
            submitted_payload,
            current.payload if current is not None else {},
        )
        super().__init__('The settings document was updated by another request.')


def _identity_query(identity: SettingsIdentity):
    owner_condition = (
        SettingsDocument.owner_user_id.is_(None)
        if identity.owner_user_id is None
        else SettingsDocument.owner_user_id == identity.owner_user_id
    )
    return select(SettingsDocument).where(
        SettingsDocument.scope == identity.scope,
        SettingsDocument.subject_id == identity.subject_id,
        SettingsDocument.document_key == identity.document_key,
        owner_condition,
    )


def _current_version(session: Session, document: SettingsDocument | None) -> SettingsVersion | None:
    if document is None or document.current_version_id is None:
        return None
    return session.get(SettingsVersion, document.current_version_id)


def get_current_settings(session: Session, identity: SettingsIdentity) -> SettingsVersion | None:
    document = session.scalar(_identity_query(identity))
    return _current_version(session, document)


def _locked_document(session: Session, identity: SettingsIdentity) -> SettingsDocument | None:
    return session.scalar(_identity_query(identity).with_for_update())


def _create_document(session: Session, identity: SettingsIdentity) -> SettingsDocument:
    document = SettingsDocument(
        scope=identity.scope,
        subject_id=identity.subject_id,
        document_key=identity.document_key,
        owner_user_id=identity.owner_user_id,
        current_revision=0,
    )
    session.add(document)
    session.flush()
    return document


def create_settings_version(
    session: Session,
    identity: SettingsIdentity,
    expected_revision: int,
    schema_version: int,
    payload: dict[str, Any],
    actor_id: int,
    reason: str,
    source_version_id: int | None = None,
) -> SettingsVersion:
    validated = validate_settings_payload(identity.document_key, schema_version, payload)
    document = _locked_document(session, identity)
    if document is None:
        if expected_revision != 0:
            raise SettingsRevisionConflict(expected_revision, None, validated)
        document = _create_document(session, identity)

    current = _current_version(session, document)
    if expected_revision != document.current_revision:
        raise SettingsRevisionConflict(expected_revision, current, validated)

    version = SettingsVersion(
        document_id=document.id,
        revision=document.current_revision + 1,
        schema_version=schema_version,
        payload=validated,
        checksum=settings_checksum(validated),
        created_by=actor_id,
        reason=reason,
        source_version_id=source_version_id,
    )
    session.add(version)
    session.flush()
    document.current_revision = version.revision
    document.current_version_id = version.id
    document.updated_at = datetime.now(timezone.utc)
    session.flush()
    return version


def list_settings_history(
    session: Session,
    identity: SettingsIdentity,
    offset: int = 0,
    limit: int = 50,
) -> tuple[list[SettingsVersion], int]:
    document = session.scalar(_identity_query(identity))
    if document is None:
        return [], 0
    total = session.scalar(
        select(func.count()).select_from(SettingsVersion).where(SettingsVersion.document_id == document.id)
    ) or 0
    versions = list(session.scalars(
        select(SettingsVersion)
        .where(SettingsVersion.document_id == document.id)
        .order_by(SettingsVersion.revision.desc())
        .offset(max(0, offset))
        .limit(min(100, max(1, limit)))
    ))
    return versions, total


def rollback_settings(
    session: Session,
    identity: SettingsIdentity,
    expected_revision: int,
    target_revision: int,
    actor_id: int,
    reason: str,
) -> SettingsVersion:
    document = _locked_document(session, identity)
    current = _current_version(session, document)
    if document is None or expected_revision != document.current_revision:
        raise SettingsRevisionConflict(expected_revision, current, {})
    target = session.scalar(select(SettingsVersion).where(
        SettingsVersion.document_id == document.id,
        SettingsVersion.revision == target_revision,
    ))
    if target is None:
        raise ValueError('The target settings revision does not exist.')
    return create_settings_version(
        session,
        identity,
        expected_revision,
        target.schema_version,
        target.payload,
        actor_id,
        reason,
        source_version_id=target.id,
    )