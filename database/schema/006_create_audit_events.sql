CREATE TABLE IF NOT EXISTS audit_events (
    id            BIGSERIAL    PRIMARY KEY,
    actor_id      BIGINT,
    action        VARCHAR(16)  NOT NULL,
    method        VARCHAR(8)   NOT NULL,
    path          VARCHAR(512) NOT NULL,
    resource_type VARCHAR(128) NOT NULL,
    resource_id   VARCHAR(256),
    request_id    VARCHAR(128) NOT NULL UNIQUE,
    status_code   INTEGER      NOT NULL,
    result        VARCHAR(16)  NOT NULL,
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_audit_events_actor_id ON audit_events (actor_id);
CREATE INDEX IF NOT EXISTS ix_audit_events_action ON audit_events (action);
CREATE INDEX IF NOT EXISTS ix_audit_events_path ON audit_events (path);
CREATE INDEX IF NOT EXISTS ix_audit_events_resource_type ON audit_events (resource_type);
CREATE INDEX IF NOT EXISTS ix_audit_events_result ON audit_events (result);
CREATE INDEX IF NOT EXISTS ix_audit_events_created_at ON audit_events (created_at);