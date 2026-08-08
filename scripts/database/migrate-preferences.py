#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

from app.database.session import SessionLocal
from app.services.settings_file_migration import migrate_preference_files


def main() -> int:
    parser = argparse.ArgumentParser(description='Migrate legacy workstation preference JSON into PostgreSQL.')
    parser.add_argument('--root', type=Path, default=Path('data/preferences'))
    parser.add_argument('--actor-id', type=int, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    with SessionLocal() as session:
        report = migrate_preference_files(session, args.root, actor_id=args.actor_id, apply=args.apply)
        if args.apply and not report.invalid and not report.conflicts:
            session.commit()
        else:
            session.rollback()
    print(json.dumps(report.__dict__, sort_keys=True))
    return 1 if report.invalid or report.conflicts else 0


if __name__ == '__main__':
    sys.exit(main())