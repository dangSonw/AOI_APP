from datetime import datetime, timezone
from typing import Literal, Self

from pydantic import Field, model_validator

from app.schemas.base import ApiSchema


class DashboardPanelSchema(ApiSchema):
    is_collapsed: bool = False


class ViewerPanelSchema(DashboardPanelSchema):
    width_units: int = Field(default=6, ge=3, le=12)
    height_units: int = Field(default=5, ge=3, le=12)


class DashboardPanelsSchema(ApiSchema):
    state: DashboardPanelSchema = DashboardPanelSchema()
    optical_2d: ViewerPanelSchema = ViewerPanelSchema()
    heightmap_3d: ViewerPanelSchema = ViewerPanelSchema()
    physical_io: DashboardPanelSchema = DashboardPanelSchema()
    inspection_flow: DashboardPanelSchema = DashboardPanelSchema()


class DashboardPreferencesSchema(ApiSchema):
    panels: DashboardPanelsSchema = DashboardPanelsSchema()


class LocalePreferencesSchema(ApiSchema):
    language: Literal['en-US', 'en-GB'] = 'en-US'
    region: Literal['vi-VN', 'en-SG', 'de-DE'] = 'vi-VN'
    timezone: Literal['Asia/Ho_Chi_Minh', 'Asia/Singapore', 'Europe/Berlin'] = 'Asia/Ho_Chi_Minh'
    measurement_system: Literal['metric', 'imperial'] = 'metric'
    clock_format: Literal['24-hour', '12-hour'] = '24-hour'


class PhotometricLightSchema(ApiSchema):
    id: int = Field(ge=1)
    azimuth: int = Field(ge=0, le=359)
    elevation: int = Field(ge=0, le=90)
    intensity: int = Field(ge=0, le=100)


class PhotometricPreferencesSchema(ApiSchema):
    light_count: int = Field(default=4, ge=1, le=64)
    lights: tuple[PhotometricLightSchema, ...]

    @model_validator(mode='after')
    def validate_light_count(self) -> Self:
        if len(self.lights) != self.light_count:
            raise ValueError('Photometric light count must match the configured lights.')
        if len({light.id for light in self.lights}) != len(self.lights):
            raise ValueError('Photometric light IDs must be unique.')
        return self


class WorkstationPreferenceContentSchema(ApiSchema):
    dashboard: DashboardPreferencesSchema = DashboardPreferencesSchema()
    locale: LocalePreferencesSchema = LocalePreferencesSchema()
    photometric: PhotometricPreferencesSchema

    @classmethod
    def create_default(cls) -> Self:
        lights = tuple(
            PhotometricLightSchema(
                id=index + 1,
                azimuth=round(index * 360 / 4) % 360,
                elevation=25,
                intensity=82,
            )
            for index in range(4)
        )
        return cls(
            photometric=PhotometricPreferencesSchema(lights=lights),
        )


class WorkstationPreferencesSchema(WorkstationPreferenceContentSchema):
    version: int = Field(default=1, ge=1)
    revision: int = Field(default=0, ge=0)
    user_id: int = Field(ge=1)
    workstation_id: str
    updated_at: datetime

    @classmethod
    def create_default(cls, user_id: int, workstation_id: str) -> Self:
        content = WorkstationPreferenceContentSchema.create_default()
        return cls(
            user_id=user_id,
            workstation_id=workstation_id,
            updated_at=datetime.now(timezone.utc),
            **content.model_dump(),
        )