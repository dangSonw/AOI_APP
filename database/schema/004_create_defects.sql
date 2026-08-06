CREATE TABLE IF NOT EXISTS defects (
    id          BIGSERIAL    PRIMARY KEY,
    result_id   BIGINT       NOT NULL REFERENCES inspection_results (id) ON DELETE CASCADE,
    defect_type VARCHAR(64)  NOT NULL,
    severity    VARCHAR(20)  NOT NULL DEFAULT 'medium'
                             CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    location_x  REAL,
    location_y  REAL,
    width       REAL,
    height      REAL,
    confidence  REAL,
    description TEXT         NOT NULL DEFAULT '',
    detected_at TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_defects_result_id ON defects (result_id);
CREATE INDEX IF NOT EXISTS ix_defects_defect_type ON defects (defect_type);
CREATE INDEX IF NOT EXISTS ix_defects_severity ON defects (severity);
