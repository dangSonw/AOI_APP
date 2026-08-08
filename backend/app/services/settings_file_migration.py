import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.settings_document import SettingsDocument
from app.models.user import User
from app.schemas.workstation_preferences import (
    WorkstationPreferenceContentSchema,
    WorkstationPreferencesSchema,
)
from app.services.settings_diff import settings_checksum
from app.services.settings_service import SettingsIdentity, create_settings_version, get_current_settings


WORKSTATION_ID_PATTERN = re.compile(r'^[a-z0-9]+(?:-[a-z0-9]+)*$')


class InvalidPreferenceMigration(RuntimeError):
    pass


@dataclass(frozen=True)
class PreferenceFileCandidate:
    path: Path
    relative_path: Path
    user_id: int
    workstation_id: str


@dataclass(frozen=True)
class LoadedPreferenceCandidate:
    candidate: PreferenceFileCandidate
    payload: dict


@dataclass
class PreferenceMigrationReport:
    discovered: int = 0
    imported: int = 0
    unchanged: int = 0
    conflicts: int = 0
    invalid: int = 0


def discover_preference_files(root: Path) -> list[PreferenceFileCandidate]:
    candidates: list[PreferenceFileCandidate] = []
    users_root = root / 'users'
    if not users_root.exists():
        return candidates
    for path in users_root.glob('*/*.json'):
        relative = path.relative_to(root)
        if len(relative.parts) != 3 or not relative.parts[1].isdigit():
            continue
        user_id = int(relative.parts[1])
        workstation_id = path.stem
        if user_id < 1 or WORKSTATION_ID_PATTERN.fullmatch(workstation_id) is None:
            continue
        candidates.append(PreferenceFileCandidate(path, relative, user_id, workstation_id))
    return sorted(candidates, key=lambda item: (item.user_id, item.workstation_id))


def load_preference_candidate(
    path: Path,
    root: Path,
    *,
    user_id: int,
    workstation_id: str,
) -> LoadedPreferenceCandidate:
    candidate = PreferenceFileCandidate(path, path.relative_to(root), user_id, workstation_id)
    try:
        preferences = WorkstationPreferencesSchema.model_validate_json(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, ValidationError) as error:
        raise InvalidPreferenceMigration(f'{candidate.relative_path}: invalid preference content.') from error
    if preferences.user_id != user_id or preferences.workstation_id != workstation_id:
        raise InvalidPreferenceMigration(f'{candidate.relative_path}: preference identity does not match its path.')
    content = WorkstationPreferenceContentSchema.model_validate(preferences.model_dump()).model_dump(
        mode='json', by_alias=True,
    )
    return LoadedPreferenceCandidate(candidate, content)


def migrate_preference_files(
    session: Session,
    root: Path,
    *,
    actor_id: int,
    apply: bool = False,
) -> PreferenceMigrationReport:
    candidates = discover_preference_files(root)
    report = PreferenceMigrationReport(discovered=len(candidates))
    loaded: list[tuple[LoadedPreferenceCandidate, SettingsIdentity]] = []
    for candidate in candidates:
        if session.get(User, candidate.user_id) is None:
            report.invalid += 1
            continue
        try:
            item = load_preference_candidate(
                candidate.path, root, user_id=candidate.user_id, workstation_id=candidate.workstation_id,
            )
        except InvalidPreferenceMigration:
            report.invalid += 1
            continue
        identity = SettingsIdentity(
            'workstation', candidate.workstation_id, 'workstation-preferences', candidate.user_id,
        )
        current = get_current_settings(session, identity)
        if current is not None and current.checksum == settings_checksum(item.payload):
            report.unchanged += 1
        elif current is not None:
            report.conflicts += 1
        else:
            report.imported += 1
            loaded.append((item, identity))
    if report.invalid or report.conflicts or not apply:
        return report
    for item, identity in loaded:
        create_settings_version(
            session, identity, 0, 1, item.payload, actor_id,
            'Migrated from legacy workstation preference JSON.',
        )
    return report