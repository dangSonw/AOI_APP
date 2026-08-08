import re
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.models.audit_event import AuditEvent
from app.schemas.workstation_preferences import WorkstationPreferenceContentSchema, WorkstationPreferencesSchema
from app.services.settings_service import SettingsIdentity, SettingsRevisionConflict, create_settings_version, get_current_settings


WORKSTATION_ID_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


class InvalidWorkstationId(ValueError):
    pass


class PreferenceStorageError(RuntimeError):
    pass


class StalePreferenceRevision(RuntimeError):
    pass


class WorkstationPreferenceRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def validate_workstation_id(workstation_id: str) -> str:
        if WORKSTATION_ID_PATTERN.fullmatch(workstation_id) is None:
            raise InvalidWorkstationId('The workstation ID is invalid.')
        return workstation_id

    def _identity(self, user_id: int, workstation_id: str) -> SettingsIdentity:
        if user_id < 1:
            raise ValueError('The user ID is invalid.')
        return SettingsIdentity('workstation', self.validate_workstation_id(workstation_id), 'workstation-preferences', user_id)

    @staticmethod
    def _response(user_id: int, workstation_id: str, version) -> WorkstationPreferencesSchema:
        return WorkstationPreferencesSchema(
            version=version.schema_version, revision=version.revision, user_id=user_id,
            workstation_id=workstation_id, updated_at=version.created_at, **version.payload,
        )

    def read(self, user_id: int, workstation_id: str) -> WorkstationPreferencesSchema:
        identity = self._identity(user_id, workstation_id)
        try:
            version = get_current_settings(self.session, identity)
        except SQLAlchemyError as error:
            raise PreferenceStorageError('The workstation preferences could not be loaded.') from error
        if version is None:
            return WorkstationPreferencesSchema.create_default(user_id, workstation_id)
        return self._response(user_id, workstation_id, version)

    def save(
        self,
        user_id: int,
        workstation_id: str,
        submitted: WorkstationPreferencesSchema,
        *,
        actor_id: int,
        request_id: str,
        reason: str = 'Updated workstation preferences.',
    ) -> WorkstationPreferencesSchema:
        identity = self._identity(user_id, workstation_id)
        if submitted.user_id != user_id or submitted.workstation_id != workstation_id:
            raise InvalidWorkstationId('The preference identity does not match the request.')
        content = WorkstationPreferenceContentSchema.model_validate(submitted.model_dump()).model_dump(mode='json', by_alias=True)
        try:
            previous = get_current_settings(self.session, identity)
            version = create_settings_version(
                self.session, identity, submitted.revision, submitted.version,
                content, actor_id, reason,
            )
            self.session.add(AuditEvent(
                actor_id=actor_id, action='update', method='PUT',
                path=f'/api/workstation-preferences/{workstation_id}',
                resource_type='workstation-preferences', resource_id=workstation_id,
                request_id=request_id, status_code=200, result='success',
                before_checksum=previous.checksum if previous is not None else None,
                after_checksum=version.checksum, reason=reason, client_metadata={},
            ))
            self.session.flush()
        except SettingsRevisionConflict as error:
            raise StalePreferenceRevision('The workstation preferences were updated by another request.') from error
        except SQLAlchemyError as error:
            raise PreferenceStorageError('The workstation preferences could not be persisted.') from error
        return self._response(user_id, workstation_id, version)