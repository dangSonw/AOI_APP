#!/usr/bin/env python3
import argparse
from datetime import datetime, timezone
from pathlib import Path

from app.database.session import SessionLocal
from app.services.settings_backup import export_settings


def main() -> None:
    parser = argparse.ArgumentParser(description='Export AOI settings metadata and immutable versions.')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    with SessionLocal() as session:
        export_settings(session, args.output, exported_at=datetime.now(timezone.utc))


if __name__ == '__main__':
    main()