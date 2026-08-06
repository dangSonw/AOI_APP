-- Count matching rows for pagination
-- Same filter parameters as list_inspections.sql
SELECT COUNT(*) AS total
FROM inspection_results ir
JOIN recipes r ON r.id = ir.recipe_id
WHERE (:result IS NULL      OR ir.result = :result)
  AND (:recipe_slug IS NULL OR r.slug = :recipe_slug)
  AND (:lot IS NULL          OR ir.lot = :lot)
  AND (:search IS NULL       OR (
           ir.board_serial ILIKE '%' || :search || '%'
        OR ir.lot          ILIKE '%' || :search || '%'
        OR ir.recipe_name  ILIKE '%' || :search || '%'
  ));
