import hashlib
from pathlib import Path
from urllib.parse import unquote, urlsplit

from pydantic import BaseModel


class OperationsError(RuntimeError):
    pass


class DiskPreflight(BaseModel):
    ready: bool
    reasons: tuple[str, ...]
    projected_used_bytes: int


class BackupFile(BaseModel):
    relative_path: str
    byte_length: int
    sha256: str


class BackupManifest(BaseModel):
    backup_id: str
    files: tuple[BackupFile, ...]


class RetentionPlan(BaseModel):
    delete: tuple[Path, ...]
    preserve: tuple[Path, ...]


def disk_preflight(
    path: Path, *, required_bytes: int, quota_bytes: int, used_bytes: int,
    disk_total_bytes: int, disk_free_bytes: int, pressure_percent: int,
) -> DiskPreflight:
    reasons: list[str] = []
    projected = used_bytes + required_bytes
    if projected > quota_bytes:
        reasons.append('quota')
    projected_disk_used = disk_total_bytes - disk_free_bytes + required_bytes
    if projected_disk_used * 100 >= disk_total_bytes * pressure_percent:
        reasons.append('disk-pressure')
    return DiskPreflight(ready=not reasons, reasons=tuple(reasons), projected_used_bytes=projected)


def create_backup_manifest(backup_id: str, files: tuple[Path, ...], root: Path) -> BackupManifest:
    root = root.resolve()
    entries: list[BackupFile] = []
    for file_path in files:
        resolved = file_path.resolve()
        if not resolved.is_relative_to(root) or not resolved.is_file():
            raise OperationsError('Backup file is outside approved backup storage.')
        content = resolved.read_bytes()
        entries.append(BackupFile(
            relative_path=resolved.relative_to(root).as_posix(), byte_length=len(content),
            sha256=hashlib.sha256(content).hexdigest(),
        ))
    return BackupManifest(backup_id=backup_id, files=tuple(entries))


def verify_backup_manifest(manifest: BackupManifest, root: Path) -> bool:
    root = root.resolve()
    for entry in manifest.files:
        path = (root / entry.relative_path).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise OperationsError('Backup manifest references a missing or unsafe file.')
        content = path.read_bytes()
        if len(content) != entry.byte_length or hashlib.sha256(content).hexdigest() != entry.sha256:
            raise OperationsError('Backup file checksum or byte length is invalid.')
    return True


def build_backup_commands(database_dump: Path, artifact_archive: Path) -> tuple[list[str], list[str]]:
    return (
        ['pg_dump', '--format=custom', '--file', str(database_dump)],
        ['tar', '--create', '--file', str(artifact_archive), 'data/captures', 'data/calibration'],
    )


def build_restore_dry_run_command(database_dump: Path) -> list[str]:
    return ['pg_restore', '--list', str(database_dump)]


def postgres_environment(database_url: str) -> dict[str, str]:
    parsed = urlsplit(database_url.replace('postgresql+psycopg://', 'postgresql://', 1))
    if parsed.scheme != 'postgresql' or not parsed.hostname or not parsed.path.strip('/'):
        raise OperationsError('PostgreSQL URL is invalid for backup.')
    environment = {
        'PGHOST': parsed.hostname,
        'PGPORT': str(parsed.port or 5432),
        'PGDATABASE': unquote(parsed.path.strip('/')),
    }
    if parsed.username:
        environment['PGUSER'] = unquote(parsed.username)
    if parsed.password:
        environment['PGPASSWORD'] = unquote(parsed.password)
    return environment


def retention_plan(
    artifacts: tuple[tuple[Path, str, bool], ...], *, now_timestamp: float,
    retention_seconds: dict[str, int],
) -> RetentionPlan:
    delete: list[Path] = []
    preserve: list[Path] = []
    for path, artifact_class, legal_hold in artifacts:
        maximum_age = retention_seconds.get(artifact_class)
        if legal_hold or maximum_age is None or now_timestamp - path.stat().st_mtime <= maximum_age:
            preserve.append(path)
        else:
            delete.append(path)
    return RetentionPlan(delete=tuple(delete), preserve=tuple(preserve))