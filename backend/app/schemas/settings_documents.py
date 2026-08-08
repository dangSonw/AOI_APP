from typing import Literal

from pydantic import ConfigDict, Field

from app.schemas.base import ApiSchema
from core.devices.camera import CameraConfiguration
from core.devices.motion import MotionConfiguration


class StrictSettingsSchema(ApiSchema):
    model_config = ConfigDict(
        alias_generator=ApiSchema.model_config['alias_generator'],
        populate_by_name=True,
        from_attributes=True,
        extra='forbid',
        protected_namespaces=(),
    )


class CalibrationReferenceSchema(StrictSettingsSchema):
    calibration_id: str | None = Field(default=None, max_length=128)
    artifact_sha256: str | None = Field(default=None, pattern=r'^[0-9a-f]{64}$')
    valid_until: str | None = Field(default=None, max_length=64)
    block_production_when_invalid: bool = True


class WorkstationProfileSchema(StrictSettingsSchema):
    station_display_name: str = Field(default='AOI Station 01', min_length=1, max_length=128)
    deployment_mode: Literal['research', 'simulation', 'hardware-pilot', 'production'] = 'simulation'
    camera_profile_name: str = Field(default='Default camera', min_length=1, max_length=128)
    camera: CameraConfiguration | None = None
    motion_profile_name: str = Field(default='Default motion', min_length=1, max_length=128)
    motion: MotionConfiguration | None = None
    calibration: CalibrationReferenceSchema = CalibrationReferenceSchema()
    pose_tolerance_millimeters: float = Field(default=0.05, gt=0, le=100)
    trigger_timeout_milliseconds: int = Field(default=5000, ge=100, le=600_000)


class RecipeDefaultsSchema(StrictSettingsSchema):
    active_recipe_slug: str = Field(default='rev-c-mainboard', pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    serial_required: bool = True
    lot_required: bool = True
    run_timeout_seconds: int = Field(default=120, ge=1, le=86_400)
    maximum_retries: int = Field(default=1, ge=0, le=10)
    decision_policy: Literal['strict', 'review-borderline', 'research'] = 'review-borderline'
    evidence_required: bool = True
    result_export_format: Literal['json', 'csv', 'ipc-cfx'] = 'json'
    defect_taxonomy: str = Field(default='ipc-a-610', min_length=1, max_length=128)


class ComputePolicySchema(StrictSettingsSchema):
    execution_target: Literal['cpu', 'cuda', 'jetson', 'remote-worker'] = 'cpu'
    maximum_concurrent_inspections: int = Field(default=1, ge=1, le=64)
    maximum_research_jobs: int = Field(default=1, ge=0, le=64)
    memory_limit_megabytes: int = Field(default=4096, ge=512, le=1_048_576)
    gpu_memory_limit_megabytes: int = Field(default=0, ge=0, le=1_048_576)
    deterministic_execution: bool = True
    random_seed: int = Field(default=42, ge=0, le=2_147_483_647)


class ResearchPolicySchema(StrictSettingsSchema):
    artifact_storage_policy: Literal['filesystem', 'object-storage'] = 'filesystem'
    tracking_backend: Literal['internal', 'mlflow'] = 'internal'
    registry_backend: Literal['internal', 'mlflow'] = 'internal'
    checkpoint_retention_count: int = Field(default=5, ge=1, le=1000)
    production_alias: Literal['champion'] = 'champion'
    require_validation_evidence: bool = True


class RetentionPolicySchema(StrictSettingsSchema):
    preview_days: int = Field(default=7, ge=0, le=3650)
    raw_capture_days: int = Field(default=30, ge=0, le=3650)
    result_evidence_days: int = Field(default=365, ge=1, le=36_500)
    audit_days: int = Field(default=2555, ge=365, le=36_500)
    storage_quota_gigabytes: int = Field(default=500, ge=1, le=10_000_000)
    disk_pressure_percent: int = Field(default=85, ge=50, le=99)
    legal_hold: bool = False


class IntegrationPolicySchema(StrictSettingsSchema):
    plc_enabled: bool = False
    mes_enabled: bool = False
    mes_endpoint: str = Field(default='', max_length=2048)
    mes_secret_reference: str | None = Field(default=None, max_length=256)
    ipc_cfx_enabled: bool = False
    opc_ua_enabled: bool = False
    time_sync_required: bool = True


class NotificationPolicySchema(StrictSettingsSchema):
    machine_faults: bool = True
    adapter_degradation: bool = True
    calibration_expiry: bool = True
    storage_pressure: bool = True
    research_jobs: bool = False
    model_drift: bool = True
    minimum_interval_seconds: int = Field(default=60, ge=1, le=86_400)


class SecurityUpdatePolicySchema(StrictSettingsSchema):
    session_minutes: int = Field(default=480, ge=5, le=1440)
    audit_export_enabled: bool = True
    signed_updates_required: bool = True
    update_channel: Literal['stable', 'pilot', 'disabled'] = 'stable'
    maintenance_window: str = Field(default='Sunday 02:00-04:00', max_length=128)


class SystemPolicySchema(StrictSettingsSchema):
    compute: ComputePolicySchema = ComputePolicySchema()
    research: ResearchPolicySchema = ResearchPolicySchema()
    retention: RetentionPolicySchema = RetentionPolicySchema()
    integrations: IntegrationPolicySchema = IntegrationPolicySchema()
    notifications: NotificationPolicySchema = NotificationPolicySchema()
    security_updates: SecurityUpdatePolicySchema = SecurityUpdatePolicySchema()


SETTINGS_DOCUMENT_SCHEMAS: dict[str, type[ApiSchema]] = {
    'workstation-profile': WorkstationProfileSchema,
    'recipe-defaults': RecipeDefaultsSchema,
    'system-policy': SystemPolicySchema,
}


def default_settings_payload(document_key: str) -> dict:
    schema = SETTINGS_DOCUMENT_SCHEMAS.get(document_key)
    if schema is None:
        raise ValueError('The settings document does not have a default payload.')
    return schema().model_dump(mode='json', by_alias=True)