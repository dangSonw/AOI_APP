-- Full detail for a single inspection result including defects and images
-- Bind parameter: :result_id

-- 1) Main result
SELECT
    ir.id,
    ir.board_serial,
    ir.lot,
    ir.recipe_name,
    r.slug             AS recipe_slug,
    ir.result,
    ir.defect_count,
    ir.score,
    ir.cycle_time_ms,
    ir.camera_config,
    ir.review_decision,
    ir.reviewed_at,
    ir.inspected_at,
    op.full_name       AS operator_name,
    rv.full_name       AS reviewer_name
FROM inspection_results ir
JOIN recipes r  ON r.id = ir.recipe_id
JOIN users  op ON op.id = ir.operator_id
LEFT JOIN users rv ON rv.id = ir.reviewed_by
WHERE ir.id = :result_id;

-- 2) Defects for this result
SELECT
    d.id,
    d.defect_type,
    d.severity,
    d.location_x,
    d.location_y,
    d.width,
    d.height,
    d.confidence,
    d.description,
    d.detected_at
FROM defects d
WHERE d.result_id = :result_id
ORDER BY d.detected_at;

-- 3) Images for this result
SELECT
    img.id,
    img.image_type,
    img.relative_path,
    img.file_size_bytes,
    img.width_px,
    img.height_px,
    img.sha256_hash,
    img.media_type,
    img.defect_id,
    img.captured_at
FROM inspection_images img
WHERE img.result_id = :result_id
ORDER BY img.captured_at;
