CREATE TABLE token_store (
    token      TEXT        PRIMARY KEY,
    prefix     TEXT        NOT NULL,
    value      TEXT        NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_token_store_expires_at ON token_store (expires_at);
