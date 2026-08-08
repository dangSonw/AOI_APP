#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from app.services.settings_backup import verify_settings_export


def main() -> None:
    parser = argparse.ArgumentParser(description='Verify an AOI portable settings export.')
    parser.add_argument('path', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify_settings_export(args.path), sort_keys=True))


if __name__ == '__main__':
    main()