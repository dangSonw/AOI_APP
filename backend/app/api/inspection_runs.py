from threading import Thread

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import FileResponse

from app.auth.dependencies import CurrentUser, DatabaseSession
from app.clients.camera_client import CameraClient
from app.clients.motion_client import MotionClient
from app.config.settings import get_settings
from app.database.session import SessionLocal
from app.models.inspection_run import InspectionRun
from app.schemas.inspection_run import (
    InspectionNodeRunResponse,
    InspectionReplayResponse,
    InspectionRunCreateRequest,
    InspectionRunResponse,
)
from app.services.inspection_runtime_service import (
    InspectionRunError,
    create_run,
    execute_run,
    get_preview_artifact,
    get_latest_active_run,
    get_latest_run,
    get_run,
    replay_run,
    request_cancellation,
)


router = APIRouter(prefix='/api/inspection-runs', tags=['inspection-runs'])


def build_run_response(run: InspectionRun) -> InspectionRunResponse:
    return InspectionRunResponse(
        id=run.id,
        board_serial=run.board_serial,
        lot=run.lot,
        recipe_id=run.recipe_id,
        station_id=run.station_id,
        work_order_id=run.work_order_id,
        commissioning_snapshot=run.commissioning_snapshot,
        result_id=run.result_id,
        status=run.status,
        current_step=run.current_step,
        progress_percent=run.progress_percent,
        cancel_requested=run.cancel_requested,
        workflow_sha256=run.workflow_sha256,
        effective_versions=run.effective_versions,
        parameters=run.parameters,
        input_artifact=run.input_artifact,
        decision=run.decision,
        evidence_sha256=run.evidence_sha256,
        error_code=run.error_code,
        error_message=run.error_message,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        node_runs=[InspectionNodeRunResponse.model_validate(node) for node in run.node_runs],
    )


def _execute_in_background(run_id: str) -> None:
    settings = get_settings()
    camera = CameraClient(settings.camera_adapter_url)
    motion = MotionClient(settings.motion_adapter_url)
    try:
        with SessionLocal() as session:
            execute_run(session, run_id, camera, motion, settings.captures_data_path)
    finally:
        camera.close()
        motion.close()


@router.get('/active', response_model=InspectionRunResponse | None)
def read_active_run(_: CurrentUser, session: DatabaseSession) -> InspectionRunResponse | None:
    run = get_latest_active_run(session)
    return build_run_response(run) if run is not None else None


@router.get('/latest', response_model=InspectionRunResponse | None)
def read_latest_run(_: CurrentUser, session: DatabaseSession) -> InspectionRunResponse | None:
    run = get_latest_run(session)
    return build_run_response(run) if run is not None else None


@router.post('', response_model=InspectionRunResponse, status_code=status.HTTP_201_CREATED)
def start_run(
    request: InspectionRunCreateRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> InspectionRunResponse:
    try:
        run = create_run(session, request, current_user.id, get_settings().projects_data_path)
    except InspectionRunError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error

    Thread(
        target=_execute_in_background,
        args=(run.id,),
        name=f'inspection-run-{run.id}',
        daemon=True,
    ).start()
    return build_run_response(run)


@router.get('/{run_id}', response_model=InspectionRunResponse)
def read_run(run_id: str, _: CurrentUser, session: DatabaseSession) -> InspectionRunResponse:
    run = get_run(session, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Inspection run not found.')
    return build_run_response(run)


@router.get('/{run_id}/preview', response_class=FileResponse)
def read_run_preview(run_id: str, _: CurrentUser, session: DatabaseSession) -> FileResponse:
    try:
        artifact = get_preview_artifact(session, run_id, get_settings().captures_data_path)
    except InspectionRunError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    if artifact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Inspection preview not found.')
    path, media_type = artifact
    return FileResponse(path, media_type=media_type, headers={'Cache-Control': 'private, no-store'})


@router.post('/{run_id}/cancel', response_model=InspectionRunResponse)
def cancel_run(run_id: str, _: CurrentUser, session: DatabaseSession) -> InspectionRunResponse:
    run = request_cancellation(session, run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Inspection run not found.')
    return build_run_response(run)


@router.post('/{run_id}/replay', response_model=InspectionReplayResponse)
def replay_completed_run(run_id: str, _: CurrentUser, session: DatabaseSession) -> InspectionReplayResponse:
    try:
        decision, evidence_sha256, matches = replay_run(
            session, run_id, get_settings().captures_data_path,
        )
    except (InspectionRunError, OSError) as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    return InspectionReplayResponse(
        run_id=run_id,
        decision=decision,
        evidence_sha256=evidence_sha256,
        matches_original=matches,
    )