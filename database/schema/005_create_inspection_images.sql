CREATE TABLE IF NOT EXISTS inspection_images (
    id              BIGSERIAL    PRIMARY KEY,
    result_id       BIGINT       NOT NULL REFERENCES inspection_results (id) ON DELETE CASCADE,
    defect_id       BIGINT       REFERENCES defects (id) ON DELETE SET NULL,
    image_type      VARCHAR(32)  NOT NULL
                                 CHECK (image_type IN ('original', 'annotated', 'evidence', 'thumbnail')),
    relative_path   VARCHAR(512) NOT NULL,
    file_size_bytes BIGINT,
    width_px        INTEGER,
    height_px       INTEGER,
    sha256_hash     VARCHAR(64),
    media_type      VARCHAR(64)  NOT NULL DEFAULT 'image/png',
    captured_at     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_inspection_images_result_id ON inspection_images (result_id);
CREATE INDEX IF NOT EXISTS ix_inspection_images_defect_id ON inspection_images (defect_id);
CREATE INDEX IF NOT EXISTS ix_inspection_images_image_type ON inspection_images (image_type);
