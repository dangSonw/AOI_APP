CREATE TABLE IF NOT EXISTS inspection_results (
    id               BIGSERIAL    PRIMARY KEY,
    board_serial     VARCHAR(128) NOT NULL,
    lot              VARCHAR(128) NOT NULL DEFAULT '',
    recipe_id        BIGINT       NOT NULL REFERENCES recipes (id),
    recipe_name      VARCHAR(255) NOT NULL,
    operator_id      BIGINT       NOT NULL REFERENCES users (id),
    result           VARCHAR(10)  NOT NULL CHECK (result IN ('PASS', 'FAIL', 'REVIEW')),
    defect_count     INTEGER      NOT NULL DEFAULT 0,
    score            REAL,
    cycle_time_ms    INTEGER,
    camera_config    JSONB,
    review_decision  VARCHAR(10)  CHECK (review_decision IN ('PASS', 'FAIL')),
    reviewed_by      BIGINT       REFERENCES users (id),
    reviewed_at      TIMESTAMPTZ,
    inspected_at     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_inspection_results_board_serial ON inspection_results (board_serial);
CREATE INDEX IF NOT EXISTS ix_inspection_results_lot ON inspection_results (lot);
CREATE INDEX IF NOT EXISTS ix_inspection_results_result ON inspection_results (result);
CREATE INDEX IF NOT EXISTS ix_inspection_results_recipe_id ON inspection_results (recipe_id);
CREATE INDEX IF NOT EXISTS ix_inspection_results_operator_id ON inspection_results (operator_id);
CREATE INDEX IF NOT EXISTS ix_inspection_results_inspected_at ON inspection_results (inspected_at DESC);
