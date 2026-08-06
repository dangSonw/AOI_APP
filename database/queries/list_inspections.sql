-- Paginated listing of inspection results with optional filters
-- Bind parameters: :result, :recipe_slug, :lot, :search, :limit, :offset
SELECT
    ir.id,
    ir.board_serial,
    ir.lot,
    ir.recipe_name,
    r.slug          AS recipe_slug,
    ir.result,
    ir.defect_count,
    ir.score,
    ir.cycle_time_ms,
    ir.review_decision,
    ir.inspected_at,
    u.full_name     AS operator_name
FROM inspection_results ir
JOIN recipes r ON r.id = ir.recipe_id
JOIN users  u ON u.id = ir.operator_id
WHERE (:result IS NULL     OR ir.result = :result)
  AND (:recipe_slug IS NULL OR r.slug = :recipe_slug)
  AND (:lot IS NULL         OR ir.lot = :lot)
  AND (:search IS NULL      OR (
           ir.board_serial ILIKE '%' || :search || '%'
        OR ir.lot          ILIKE '%' || :search || '%'
        OR ir.recipe_name  ILIKE '%' || :search || '%'
  ))
ORDER BY ir.inspected_at DESC
LIMIT :limit
OFFSET :offset;
