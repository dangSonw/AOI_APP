CREATE TABLE IF NOT EXISTS recipes (
    id          BIGSERIAL    PRIMARY KEY,
    slug        VARCHAR(128) NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    description TEXT         NOT NULL DEFAULT '',
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_recipes_slug ON recipes (slug);
CREATE INDEX IF NOT EXISTS ix_recipes_is_active ON recipes (is_active);
