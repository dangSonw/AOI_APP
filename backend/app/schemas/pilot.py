from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from app.schemas.base import ApiSchema


class CalibrationMetrics(ApiSchema):
    image_count: int = Field(ge=1, le=10000)
    coverage_percent: float = Field(ge=0, le=100)
    reprojection_error_pixels: float = Field(ge=0, le=1000)


class CalibrationCreateRequest(ApiSchema):
    station_id: str = Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')
    camera_id: str = Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')
    calibration_type: Literal['intrinsic', 'extrinsic', 'flat-field']
    artifact_relative_path: str = Field(min_length=1, max_length=512)
    artifact_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    valid_until: datetime
    metrics: CalibrationMetrics


class PlcSignalMapping(ApiSchema):
    schema_version: Literal[1] = 1
    ready: str | None = Field(default=None, max_length=128)
    busy: str | None = Field(default=None, max_length=128)
    trigger: str | None = Field(default=None, max_length=128)
    result_pass: str | None = Field(default=None, max_length=128)
    result_fail: str | None = Field(default=None, max_length=128)
    fault: str | None = Field(default=None, max_length=128)


class PlcIntegrationPolicy(ApiSchema):
    enabled: bool = False
    outage_policy: Literal['block', 'fail-safe'] = 'fail-safe'


class MesIntegrationPolicy(ApiSchema):
    enabled: bool = False
    outage_policy: Literal['queue', 'block'] = 'queue'
    endpoint_reference: str | None = Field(default=None, max_length=256)


class IntegrationPolicy(ApiSchema):
    schema_version: Literal[1] = 1
    plc: PlcIntegrationPolicy = PlcIntegrationPolicy()
    mes: MesIntegrationPolicy = MesIntegrationPolicy()


class CommissioningProfileCreateRequest(ApiSchema):
    station_id: str = Field(pattern=r'^[a-zA-Z0-9][a-zA-Z0-9._-]{0,127}$')
    deployment_mode: Literal['simulation', 'hardware-pilot', 'production']
    calibration_id: str | None = Field(default=None, max_length=64)
    signal_mapping: PlcSignalMapping
    integration_policy: IntegrationPolicy

    @model_validator(mode='after')
    def validate_integration_requirements(self) -> 'CommissioningProfileCreateRequest':
        if self.integration_policy.plc.enabled:
            required = (
                self.signal_mapping.ready, self.signal_mapping.busy, self.signal_mapping.trigger,
                self.signal_mapping.result_pass, self.signal_mapping.result_fail, self.signal_mapping.fault,
            )
            if any(value is None for value in required):
                raise ValueError('Enabled PLC integration requires a complete handshake signal mapping.')
        if self.integration_policy.mes.enabled and not self.integration_policy.mes.endpoint_reference:
            raise ValueError('Enabled MES integration requires an endpoint reference.')
        return self


class CommissioningActivationRequest(ApiSchema):
    reason: str = Field(min_length=1, max_length=1000)