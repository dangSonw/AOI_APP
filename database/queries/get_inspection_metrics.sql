-- Aggregate inspection metrics for dashboard
-- Returns: total inspections, pass/fail/review counts, first-pass yield
SELECT
    COUNT(*)                                                    AS total_inspections,
    COUNT(*) FILTER (WHERE result = 'PASS')                     AS pass_count,
    COUNT(*) FILTER (WHERE result = 'FAIL')                     AS fail_count,
    COUNT(*) FILTER (WHERE result = 'REVIEW')                   AS review_count,
    ROUND(
        COUNT(*) FILTER (WHERE result = 'PASS') * 100.0
        / GREATEST(COUNT(*), 1), 1
    )                                                           AS first_pass_yield,
    COALESCE(SUM(defect_count), 0)                              AS total_defects,
    COUNT(*) FILTER (WHERE result = 'REVIEW'
                       AND review_decision IS NULL)             AS pending_review
FROM inspection_results;
