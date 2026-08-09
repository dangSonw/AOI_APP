#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

from app.services.pilot_acceptance import PilotAcceptanceError, verify_pilot_acceptance


def main() -> None:
    parser = argparse.ArgumentParser(description='Verify measured AOI target-hardware pilot acceptance.')
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    try:
        report = verify_pilot_acceptance(args.report)
    except PilotAcceptanceError as error:
        raise SystemExit(str(error)) from error
    print(json.dumps({'valid': True, 'stationId': report.station_id,
                      'inspectedBoardCount': report.measurements.inspected_board_count}))


if __name__ == '__main__':
    main()