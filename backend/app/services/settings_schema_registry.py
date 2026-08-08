from collections.abc import Mapping
from typing import Any

from pydantic import ValidationError

from app.schemas.base import ApiSchema
from app.schemas.workstation_preferences import WorkstationPreferenceContentSchema


class UnknownSettingsSchema(ValueError):
    pass


SETTINGS_SCHEMA_REGISTRY: dict[tuple[str, int], type[ApiSchema]] = {
    ('workstation-preferences', 1): WorkstationPreferenceContentSchema,
}


def validate_settings_payload(
    document_key: str,
    schema_version: int,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    schema = SETTINGS_SCHEMA_REGISTRY.get((document_key, schema_version))
    if schema is None:
        raise UnknownSettingsSchema('The settings schema is not supported.')
    return schema.model_validate(payload).model_dump(mode='json', by_alias=True)