-- Sample inspection data for development and demonstration
-- Requires: seed_recipes.sql and at least one user in the users table

-- Insert sample inspection results
-- Uses recipe_id = 1 (rev-c-mainboard) and operator_id = 1 (default operator)
INSERT INTO inspection_results
    (board_serial, lot, recipe_id, recipe_name, operator_id, result, defect_count, score, cycle_time_ms, inspected_at)
VALUES
    ('PCB-24-08192', 'MFG-2408-C', 1, 'Rev C · Mainboard', 1, 'PASS',   0, 0.02,  1250, '2026-08-06 14:32:18+07'),
    ('PCB-24-08191', 'MFG-2408-C', 1, 'Rev C · Mainboard', 1, 'REVIEW', 2, 0.67,  1480, '2026-08-06 14:31:42+07'),
    ('PCB-24-08190', 'MFG-2408-B', 2, 'Rev B · Power',     1, 'FAIL',   5, 0.91,  1320, '2026-08-06 14:29:07+07'),
    ('PCB-24-08189', 'MFG-2408-C', 1, 'Rev C · Mainboard', 1, 'PASS',   0, 0.01,  1190, '2026-08-06 14:27:55+07'),
    ('PCB-24-08188', 'MFG-2408-A', 3, 'Rev A · Sensor',    1, 'PASS',   0, 0.03,  1310, '2026-08-06 14:26:11+07'),
    ('PCB-24-08187', 'MFG-2408-B', 2, 'Rev B · Power',     1, 'REVIEW', 1, 0.54,  1400, '2026-08-06 14:24:39+07')
ON CONFLICT DO NOTHING;

-- Insert sample defects for REVIEW and FAIL boards
INSERT INTO defects (result_id, defect_type, severity, location_x, location_y, width, height, confidence, description)
SELECT ir.id, v.defect_type, v.severity, v.lx, v.ly, v.w, v.h, v.conf, v.descr
FROM inspection_results ir
CROSS JOIN (VALUES
    ('missing_component', 'high',     120.5, 340.2, 24.0, 18.0, 0.89, 'Missing capacitor C12'),
    ('solder_bridge',     'medium',   455.1, 128.7, 12.0, 10.0, 0.72, 'Solder bridge between pins 3-4')
) AS v(defect_type, severity, lx, ly, w, h, conf, descr)
WHERE ir.board_serial = 'PCB-24-08191'
ON CONFLICT DO NOTHING;
