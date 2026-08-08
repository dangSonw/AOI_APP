import pytest
from pydantic import ValidationError

from app.config.settings import Settings


def settings_payload() -> dict[str, str]:
    return {
        'database_url': 'postgresql+psycopg://user:password@127.0.0.1/database',
        'jwt_secret_key': 'a' * 32,
        'seed_admin_password': 'secure-password',
    }


def test_device_adapter_urls_default_to_loopback_services() -> None:
    settings = Settings(**settings_payload())

    assert settings.camera_adapter_url == 'http://127.0.0.1:9101'
    assert settings.motion_adapter_url == 'http://127.0.0.1:9102'


def test_public_registration_defaults_to_disabled() -> None:
    settings = Settings(**settings_payload())

    assert settings.allow_public_registration is False


@pytest.mark.parametrize('field', ['camera_adapter_url', 'motion_adapter_url'])
def test_device_adapter_urls_reject_non_loopback_hosts(field: str) -> None:
    with pytest.raises(ValidationError):
        Settings(**settings_payload(), **{field: 'http://example.com:9101'})