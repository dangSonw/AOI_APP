import math
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.defect import Defect
from app.models.inspection_image import InspectionImage
from app.models.inspection_result import InspectionResult
from app.models.inspection_run import InspectionReviewEvent
from app.models.recipe import Recipe
from app.models.user import User


def get_inspection_metrics(session: Session) -> dict:
    total = session.scalar(select(func.count(InspectionResult.id))) or 0
    pass_count = session.scalar(
        select(func.count(InspectionResult.id)).where(InspectionResult.result == 'PASS'),
    ) or 0
    fail_count = session.scalar(
        select(func.count(InspectionResult.id)).where(InspectionResult.result == 'FAIL'),
    ) or 0
    review_count = session.scalar(
        select(func.count(InspectionResult.id)).where(InspectionResult.result == 'REVIEW'),
    ) or 0
    total_defects = session.scalar(
        select(func.coalesce(func.sum(InspectionResult.defect_count), 0)),
    ) or 0
    pending_review = session.scalar(
        select(func.count(InspectionResult.id)).where(
            InspectionResult.result == 'REVIEW',
            InspectionResult.review_decision.is_(None),
        ),
    ) or 0
    first_pass_yield = round(pass_count * 100.0 / max(total, 1), 1)

    return {
        'total_inspections': total,
        'pass_count': pass_count,
        'fail_count': fail_count,
        'review_count': review_count,
        'first_pass_yield': first_pass_yield,
        'total_defects': total_defects,
        'pending_review': pending_review,
    }


def list_inspections(
    session: Session,
    *,
    page: int = 1,
    page_size: int = 25,
    result_filter: str | None = None,
    recipe_slug: str | None = None,
    lot: str | None = None,
    search: str | None = None,
) -> dict:
    query = (
        select(InspectionResult, Recipe.slug, User.full_name)
        .join(Recipe, Recipe.id == InspectionResult.recipe_id)
        .join(User, User.id == InspectionResult.operator_id)
    )

    count_query = (
        select(func.count(InspectionResult.id))
        .join(Recipe, Recipe.id == InspectionResult.recipe_id)
    )

    if result_filter:
        query = query.where(InspectionResult.result == result_filter)
        count_query = count_query.where(InspectionResult.result == result_filter)
    if recipe_slug:
        query = query.where(Recipe.slug == recipe_slug)
        count_query = count_query.where(Recipe.slug == recipe_slug)
    if lot:
        query = query.where(InspectionResult.lot == lot)
        count_query = count_query.where(InspectionResult.lot == lot)
    if search:
        search_pattern = f'%{search}%'
        search_filter = (
            InspectionResult.board_serial.ilike(search_pattern)
            | InspectionResult.lot.ilike(search_pattern)
            | InspectionResult.recipe_name.ilike(search_pattern)
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = session.scalar(count_query) or 0
    total_pages = max(math.ceil(total / page_size), 1)

    offset = (page - 1) * page_size
    query = query.order_by(InspectionResult.inspected_at.desc())
    query = query.limit(page_size).offset(offset)

    rows = session.execute(query).all()

    items = []
    for inspection_result, slug, operator_name in rows:
        items.append({
            'id': inspection_result.id,
            'board_serial': inspection_result.board_serial,
            'lot': inspection_result.lot,
            'recipe_name': inspection_result.recipe_name,
            'recipe_slug': slug,
            'result': inspection_result.result,
            'defect_count': inspection_result.defect_count,
            'score': inspection_result.score,
            'cycle_time_ms': inspection_result.cycle_time_ms,
            'review_decision': inspection_result.review_decision,
            'inspected_at': inspection_result.inspected_at,
            'operator_name': operator_name,
        })

    return {
        'items': items,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
    }


def get_inspection_detail(session: Session, result_id: int) -> InspectionResult | None:
    return session.scalar(
        select(InspectionResult)
        .options(
            joinedload(InspectionResult.recipe),
            joinedload(InspectionResult.operator),
            joinedload(InspectionResult.reviewer),
            joinedload(InspectionResult.defects),
            joinedload(InspectionResult.images),
        )
        .where(InspectionResult.id == result_id),
    )


def create_inspection(
    session: Session,
    *,
    board_serial: str,
    lot: str,
    recipe_id: int,
    operator_id: int,
    result: str,
    defect_count: int = 0,
    score: float | None = None,
    cycle_time_ms: int | None = None,
    camera_config: dict | None = None,
) -> InspectionResult:
    recipe = session.get(Recipe, recipe_id)
    if recipe is None:
        raise ValueError('The recipe does not exist.')

    inspection = InspectionResult(
        board_serial=board_serial,
        lot=lot,
        recipe_id=recipe_id,
        recipe_name=recipe.name,
        operator_id=operator_id,
        result=result,
        defect_count=defect_count,
        score=score,
        cycle_time_ms=cycle_time_ms,
        camera_config=camera_config,
    )
    session.add(inspection)
    session.commit()
    session.refresh(inspection)
    return inspection


def submit_review(
    session: Session,
    result_id: int,
    reviewer_id: int,
    decision: str,
    reason: str = '',
) -> InspectionResult | None:
    inspection = session.get(InspectionResult, result_id)
    if inspection is None:
        return None
    inspection.review_decision = decision
    inspection.reviewed_by = reviewer_id
    inspection.reviewed_at = datetime.now(timezone.utc)
    session.add(InspectionReviewEvent(
        result_id=result_id,
        actor_id=reviewer_id,
        decision=decision,
        reason=reason,
    ))
    session.commit()
    session.refresh(inspection)
    return inspection


def get_recipes(session: Session) -> list[Recipe]:
    return list(session.scalars(
        select(Recipe).where(Recipe.is_active.is_(True)).order_by(Recipe.name),
    ).all())


def create_recipe(
    session: Session,
    slug: str,
    name: str,
    description: str = '',
) -> Recipe:
    recipe = Recipe(slug=slug, name=name, description=description)
    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    return recipe
