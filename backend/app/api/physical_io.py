from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.auth.dependencies import CurrentUser
from app.config.settings import get_settings
from app.schemas.physical_io import (
    PhysicalInputState,
    PhysicalOutputState,
    PhysicalOutputUpdate,
)
from app.services.physical_io_service import (
    PhysicalIoError,
    read_input_state,
    read_output_state,
    write_output_state,
)


router = APIRouter(prefix='/api/io', tags=['physical-io'])


@router.get('/inputs', response_model=PhysicalInputState)
def get_inputs(_: CurrentUser) -> PhysicalInputState:
    try:
        return read_input_state(get_settings().physical_io_path)
    except PhysicalIoError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.get('/outputs', response_model=PhysicalOutputState)
def get_outputs(_: CurrentUser) -> PhysicalOutputState:
    try:
        return read_output_state(get_settings().physical_io_path)
    except PhysicalIoError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.put('/outputs', response_model=PhysicalOutputState)
def update_outputs(update: PhysicalOutputUpdate, _: CurrentUser) -> PhysicalOutputState:
    settings = get_settings()
    try:
        current_state = read_output_state(settings.physical_io_path)
        next_state = PhysicalOutputState(
            revision=current_state.revision + 1,
            updated_at=datetime.now(timezone.utc),
            signals=update.signals,
        )
        write_output_state(settings.physical_io_path / 'output.json', next_state)
        return next_state
    except PhysicalIoError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error