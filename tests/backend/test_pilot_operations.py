import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.services.pilot_operations import (
    BackupManifest,
    OperationsError,
    create_backup_manifest,
    disk_preflight,
    verify_backup_manifest,
    build_backup_commands,
    build_restore_dry_run_command,
    retention_plan,
    postgres_environment,
)
from app.schemas.pilot import CommissioningProfileCreateRequest


def test_disk_preflight_blocks_when_quota_or_pressure_policy_would_be_crossed(tmp_path: Path) -> None:
    ready = disk_preflight(
        tmp_path, required_bytes=10, quota_bytes=1000, used_bytes=100,
        disk_total_bytes=1000, disk_free_bytes=800, pressure_percent=85,
    )
    blocked = disk_preflight(
        tmp_path, required_bytes=200, quota_bytes=1000, used_bytes=900,
        disk_total_bytes=1000, disk_free_bytes=100, pressure_percent=85,
    )

    assert ready.ready is True
    assert blocked.ready is False
    assert {'quota', 'disk-pressure'} <= set(blocked.reasons)


def test_backup_manifest_detects_tampering_and_never_contains_database_credentials(tmp_path: Path) -> None:
    database_dump = tmp_path / 'database.dump'
    artifacts = tmp_path / 'artifacts.tar'
    database_dump.write_bytes(b'postgres-backup')
    artifacts.write_bytes(b'artifact-backup')

    manifest = create_backup_manifest('backup-1', (database_dump, artifacts), tmp_path)
    assert isinstance(manifest, BackupManifest)
    assert verify_backup_manifest(manifest, tmp_path) is True
    assert 'password' not in manifest.model_dump_json().lower()

    artifacts.write_bytes(b'tampered')
    with pytest.raises(OperationsError, match='checksum'):
        verify_backup_manifest(manifest, tmp_path)


def test_backup_and_restore_dry_run_commands_keep_credentials_out_of_argv(tmp_path: Path) -> None:
    commands = build_backup_commands(tmp_path / 'database.dump', tmp_path / 'artifacts.tar')
    restore = build_restore_dry_run_command(tmp_path / 'database.dump')
    flattened = ' '.join(argument for command in (*commands, restore) for argument in command)

    assert commands[0][0] == 'pg_dump'
    assert '--format=custom' in commands[0]
    assert restore[:2] == ['pg_restore', '--list']
    assert 'password' not in flattened.lower()
    assert 'postgresql://' not in flattened
    environment = postgres_environment('postgresql+psycopg://aoi:secret%20value@127.0.0.1:5432/aoi_app')
    assert environment == {
        'PGHOST': '127.0.0.1', 'PGPORT': '5432', 'PGDATABASE': 'aoi_app',
        'PGUSER': 'aoi', 'PGPASSWORD': 'secret value',
    }


def test_retention_plan_is_dry_run_and_preserves_legal_hold_and_recent_evidence(tmp_path: Path) -> None:
    old_preview = tmp_path / 'preview-old.png'
    old_preview.write_bytes(b'preview')
    old_evidence = tmp_path / 'evidence-old.png'
    old_evidence.write_bytes(b'evidence')
    import os
    old = 1_700_000_000
    os.utime(old_preview, (old, old))
    os.utime(old_evidence, (old, old))

    plan = retention_plan(
        ((old_preview, 'preview', False), (old_evidence, 'evidence', True)),
        now_timestamp=1_800_000_000,
        retention_seconds={'preview': 10, 'evidence': 10},
    )

    assert plan.delete == (old_preview,)
    assert plan.preserve == (old_evidence,)
    assert old_preview.exists()


def test_enabled_integrations_require_complete_versioned_contracts() -> None:
    with pytest.raises(ValidationError, match='PLC'):
        CommissioningProfileCreateRequest(
            station_id='station-01', deployment_mode='hardware-pilot',
            signal_mapping={'ready': 'DO0'}, integration_policy={'plc': {'enabled': True}},
        )
    with pytest.raises(ValidationError, match='MES'):
        CommissioningProfileCreateRequest(
            station_id='station-01', deployment_mode='hardware-pilot', signal_mapping={},
            integration_policy={'mes': {'enabled': True}},
        )