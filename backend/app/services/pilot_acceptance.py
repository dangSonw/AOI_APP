import json
from pathlib import Path

from pydantic import ConfigDict, Field, ValidationError

from app.schemas.base import ApiSchema


class PilotAcceptanceError(RuntimeError):
    pass


class PilotMeasurements(ApiSchema):
    model_config = ConfigDict(
        alias_generator=ApiSchema.model_config['alias_generator'],
        populate_by_name=True,
        extra='forbid',
    )
    cycle_time_p95_ms: float = Field(gt=0)
    false_call_rate_percent: float = Field(ge=0, le=100)
    escape_rate_percent: float = Field(ge=0, le=100)
    uptime_percent: float = Field(gt=0, le=100)
    recovery_time_seconds: float = Field(ge=0)
    inspected_board_count: int = Field(ge=1)


class PilotAcceptanceReport(ApiSchema):
    model_config = ConfigDict(
        alias_generator=ApiSchema.model_config['alias_generator'],
        populate_by_name=True,
        extra='forbid',
    )
    schema_version: int = Field(ge=1, le=1)
    station_id: str = Field(min_length=1, max_length=128)
    target_hardware: str = Field(min_length=1, max_length=256)
    measurements: PilotMeasurements
    hardware_interlocks_authoritative: bool
    calibration_lineage_verified: bool
    integration_outage_policy_verified: bool
    backup_restore_dry_run_verified: bool
    status: str


def verify_pilot_acceptance(path: Path) -> PilotAcceptanceReport:
    try:
        report = PilotAcceptanceReport.model_validate_json(path.read_text(encoding='utf-8'))
    except (OSError, ValidationError) as error:
        raise PilotAcceptanceError('Pilot acceptance report is missing or invalid.') from error
    gates = (
        report.hardware_interlocks_authoritative,
        report.calibration_lineage_verified,
        report.integration_outage_policy_verified,
        report.backup_restore_dry_run_verified,
    )
    if report.status != 'passed' or not all(gates):
        raise PilotAcceptanceError('Pilot acceptance report has incomplete or failed gates.')
    return report