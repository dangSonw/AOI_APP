from fastapi import APIRouter

from app.auth.dependencies import CurrentUser, DatabaseSession
from app.schemas.database_schema import DatabaseSchemaResponse
from app.services.database_schema_service import inspect_database_schema


router = APIRouter(prefix='/api/database', tags=['database'])


@router.get('/schema', response_model=DatabaseSchemaResponse)
def read_database_schema(_: CurrentUser, session: DatabaseSession) -> DatabaseSchemaResponse:
    return inspect_database_schema(session.get_bind())