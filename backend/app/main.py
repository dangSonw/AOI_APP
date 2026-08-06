from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.devices import router as devices_router
from app.api.physical_io import router as physical_io_router
from app.api.workflows import router as workflows_router
from app.api.workstation_preferences import router as workstation_preferences_router
from app.config.settings import get_settings
from app.database.bootstrap import initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    initialize_database()
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)
app.include_router(auth_router)
app.include_router(devices_router)
app.include_router(physical_io_router)
app.include_router(workflows_router)
app.include_router(workstation_preferences_router)


@app.get('/health')
def health_check() -> dict[str, str]:
    return {'status': 'ok', 'environment': settings.app_environment}
