import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock

from pydantic import ValidationError

from app.schemas.workstation_preferences import WorkstationPreferencesSchema


WORKSTATION_ID_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


class InvalidWorkstationId(ValueError):
    pass


class PreferenceStorageError(RuntimeError):
    pass


class StalePreferenceRevision(RuntimeError):
    pass


class WorkstationPreferenceRepository:
    _write_lock = RLock()

    def __init__(self, root: Path) -> None:
        self.root = root

    @staticmethod
    def validate_workstation_id(workstation_id: str) -> str:
        if WORKSTATION_ID_PATTERN.fullmatch(workstation_id) is None:
            raise InvalidWorkstationId('The workstation ID is invalid.')
        return workstation_id

    def _path(self, user_id: int, workstation_id: str) -> Path:
        if user_id < 1:
            raise ValueError('The user ID is invalid.')
        return self.root / 'users' / str(user_id) / f'{self.validate_workstation_id(workstation_id)}.json'

    @staticmethod
    def _read_file(path: Path) -> WorkstationPreferencesSchema:
        try:
            return WorkstationPreferencesSchema.model_validate_json(path.read_text(encoding='utf-8'))
        except (OSError, ValidationError, ValueError) as error:
            raise PreferenceStorageError('The workstation contains invalid persisted preferences.') from error

    def read(self, user_id: int, workstation_id: str) -> WorkstationPreferencesSchema:
        path = self._path(user_id, workstation_id)
        if not path.exists():
            return WorkstationPreferencesSchema.create_default(user_id, workstation_id)
        preferences = self._read_file(path)
        if preferences.user_id != user_id or preferences.workstation_id != workstation_id:
            raise PreferenceStorageError('The workstation contains invalid persisted preferences.')
        return preferences

    def save(
        self,
        user_id: int,
        workstation_id: str,
        submitted: WorkstationPreferencesSchema,
    ) -> WorkstationPreferencesSchema:
        path = self._path(user_id, workstation_id)
        if submitted.user_id != user_id or submitted.workstation_id != workstation_id:
            raise InvalidWorkstationId('The preference identity does not match the request.')

        with self._write_lock:
            stored_revision = self._read_file(path).revision if path.exists() else 0
            if submitted.revision != stored_revision:
                raise StalePreferenceRevision('The workstation preferences were updated by another request.')
            updated = submitted.model_copy(update={
                'revision': stored_revision + 1,
                'updated_at': datetime.now(timezone.utc),
            })
            temporary_path = path.with_suffix('.json.tmp')
            path.parent.mkdir(parents=True, exist_ok=True)
            try:
                with temporary_path.open('w', encoding='utf-8') as preference_file:
                    json.dump(updated.model_dump(mode='json', by_alias=True), preference_file, ensure_ascii=False, indent=2)
                    preference_file.write('\n')
                    preference_file.flush()
                    os.fsync(preference_file.fileno())
                os.replace(temporary_path, path)
            except OSError as error:
                temporary_path.unlink(missing_ok=True)
                raise PreferenceStorageError('The workstation preferences could not be persisted.') from error
            return updated