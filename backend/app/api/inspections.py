from fastapi import APIRouter, HTTPException, Query, status

from app.auth.dependencies import CurrentUser, DatabaseSession
from app.models.inspection_result import InspectionResult
from app.schemas.inspection import (
    DefectResponse,
    InspectionCreateRequest,
    InspectionDetailResponse,
    InspectionImageResponse,
    InspectionListResponse,
    InspectionMetricsResponse,
    ReviewRequest,
)
from app.services.inspection_service import (
    create_inspection,
    get_inspection_detail,
    get_inspection_metrics,
    list_inspections,
    submit_review,
)


router = APIRouter(prefix='/api/inspections', tags=['inspections'])


def build_inspection_detail_response(inspection: InspectionResult) -> InspectionDetailResponse:
    return InspectionDetailResponse(
        id=inspection.id,
        board_serial=inspection.board_serial,
        lot=inspection.lot,
        recipe_name=inspection.recipe_name,
        recipe_slug=inspection.recipe.slug,
        result=inspection.result,
        defect_count=inspection.defect_count,
        score=inspection.score,
        cycle_time_ms=inspection.cycle_time_ms,
        camera_config=inspection.camera_config,
        review_decision=inspection.review_decision,
        reviewed_at=inspection.reviewed_at,
        reviewer_name=inspection.reviewer.full_name if inspection.reviewer else None,
        inspected_at=inspection.inspected_at,
        operator_name=inspection.operator.full_name,
        defects=[DefectResponse.model_validate(defect) for defect in inspection.defects],
        images=[InspectionImageResponse.model_validate(image) for image in inspection.images],
    )


@router.get('/metrics', response_model=InspectionMetricsResponse)
def get_metrics(
    _: CurrentUser,
    session: DatabaseSession,
) -> InspectionMetricsResponse:
    metrics = get_inspection_metrics(session)
    return InspectionMetricsResponse(**metrics)


@router.get('', response_model=InspectionListResponse)
def list_results(
    _: CurrentUser,
    session: DatabaseSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    result: str | None = Query(default=None),
    recipe_slug: str | None = Query(default=None),
    lot: str | None = Query(default=None),
    search: str | None = Query(default=None),
) -> InspectionListResponse:
    data = list_inspections(
        session,
        page=page,
        page_size=page_size,
        result_filter=result,
        recipe_slug=recipe_slug,
        lot=lot,
        search=search,
    )
    return InspectionListResponse(**data)


@router.get('/{result_id}', response_model=InspectionDetailResponse)
def get_detail(
    result_id: int,
    _: CurrentUser,
    session: DatabaseSession,
) -> InspectionDetailResponse:
    inspection = get_inspection_detail(session, result_id)
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Inspection result not found.',
        )
    return build_inspection_detail_response(inspection)


@router.post(
    '',
    response_model=InspectionDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_result(
    request: InspectionCreateRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> InspectionDetailResponse:
    try:
        inspection = create_inspection(
            session,
            board_serial=request.board_serial,
            lot=request.lot,
            recipe_id=request.recipe_id,
            operator_id=current_user.id,
            result=request.result,
            defect_count=request.defect_count,
            score=request.score,
            cycle_time_ms=request.cycle_time_ms,
            camera_config=request.camera_config,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error

    loaded = get_inspection_detail(session, inspection.id)
    if loaded is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='The created inspection could not be reloaded.',
        )
    return build_inspection_detail_response(loaded)


@router.patch('/{result_id}/review')
def review_result(
    result_id: int,
    request: ReviewRequest,
    current_user: CurrentUser,
    session: DatabaseSession,
) -> dict:
    inspection = submit_review(
        session, result_id, current_user.id, request.decision,
    )
    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='Inspection result not found.',
        )
    return {
        'id': inspection.id,
        'review_decision': inspection.review_decision,
        'reviewed_at': inspection.reviewed_at,
    }
