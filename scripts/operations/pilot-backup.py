#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from app.config.settings import PROJECT_ROOT, get_settings
from app.services.pilot_operations import build_backup_commands, create_backup_manifest, postgres_environment


def main() -> None:
    parser = argparse.ArgumentParser(description='Create AOI pilot PostgreSQL and artifact backup.')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and output.is_symlink():
        raise SystemExit('Backup output cannot be a symbolic link.')
    output.mkdir(parents=True, exist_ok=True)
    database_dump = output / 'database.dump'
    artifact_archive = output / 'artifacts.tar'
    commands = build_backup_commands(database_dump, artifact_archive)
    if args.dry_run:
        print(json.dumps({'dryRun': True, 'commands': [[command[0], *command[1:2]] for command in commands]}))
        return
    environment = os.environ.copy()
    environment.update(postgres_environment(get_settings().database_url))
    for command in commands:
        cwd = PROJECT_ROOT if command[0] == 'tar' else None
        subprocess.run(command, check=True, cwd=cwd, env=environment)
    backup_id = datetime.now(timezone.utc).strftime('pilot-%Y%m%dT%H%M%SZ')
    manifest = create_backup_manifest(backup_id, (database_dump, artifact_archive), output)
    (output / 'manifest.json').write_text(manifest.model_dump_json(indent=2), encoding='utf-8')
    print(json.dumps({'backupId': backup_id, 'manifest': str(output / 'manifest.json')}))


if __name__ == '__main__':
    main()