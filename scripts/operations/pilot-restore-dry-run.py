#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

from app.services.pilot_operations import BackupManifest, build_restore_dry_run_command, verify_backup_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description='Verify AOI pilot backup and inspect PostgreSQL restore catalog.')
    parser.add_argument('backup_directory', type=Path)
    args = parser.parse_args()
    root = args.backup_directory.resolve()
    manifest = BackupManifest.model_validate_json((root / 'manifest.json').read_text(encoding='utf-8'))
    verify_backup_manifest(manifest, root)
    database_dump = root / 'database.dump'
    result = subprocess.run(
        build_restore_dry_run_command(database_dump), check=True, capture_output=True, text=True,
    )
    if not result.stdout.strip():
        raise SystemExit('PostgreSQL restore catalog is empty.')
    print(json.dumps({'valid': True, 'backupId': manifest.backup_id,
                      'catalogLines': len(result.stdout.splitlines())}))


if __name__ == '__main__':
    main()