from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    app_name: str = 'AOI System API'
    app_environment: str = 'development'
    api_host: str = '127.0.0.1'
    api_port: int = 8000
    frontend_origin: str = 'http://127.0.0.1:5173'
    database_url: str = Field(min_length=1)
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = 'HS256'
    jwt_access_token_expire_minutes: int = 60
    physical_io_directory: str = 'io'
    projects_data_directory: str = 'data/projects'
    preferences_data_directory: str = 'data/preferences'
    seed_admin_email: str = 'operator@aoi.local'
    seed_admin_password: str = Field(min_length=8)
    seed_admin_full_name: str = 'AOI Operator'

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / '.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )

    @property
    def physical_io_path(self) -> Path:
        return PROJECT_ROOT / self.physical_io_directory

    @property
    def projects_data_path(self) -> Path:
        return PROJECT_ROOT / self.projects_data_directory

    @property
    def preferences_data_path(self) -> Path:
        return PROJECT_ROOT / self.preferences_data_directory

    @property
    def frontend_origins(self) -> list[str]:
        configured_origin = self.frontend_origin.rstrip('/')
        origins = [configured_origin]

        if self.app_environment.lower() != 'development':
            return origins

        parsed_origin = urlsplit(configured_origin)
        loopback_aliases = {
            '127.0.0.1': 'localhost',
            'localhost': '127.0.0.1',
        }
        alias_host = loopback_aliases.get(parsed_origin.hostname or '')
        if alias_host is None:
            return origins

        alias_port = f':{parsed_origin.port}' if parsed_origin.port is not None else ''
        origins.append(f'{parsed_origin.scheme}://{alias_host}{alias_port}')
        return origins


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]