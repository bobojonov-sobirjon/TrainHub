CREATE TABLE user_identities (
    id                BIGSERIAL PRIMARY KEY,
    user_id           BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    provider          TEXT NOT NULL CHECK (provider IN ('google', 'apple', 'telegram')),
    provider_user_id  TEXT NOT NULL,
    email             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (provider, provider_user_id)
);

CREATE INDEX idx_user_identities_user ON user_identities (user_id);

CREATE TABLE user_devices (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    platform      TEXT NOT NULL CHECK (platform IN ('ios', 'android', 'web')),
    token         TEXT NOT NULL,
    device_name   TEXT,
    app_version   TEXT,
    last_seen_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (token)
);

CREATE INDEX idx_user_devices_user ON user_devices (user_id, last_seen_at DESC);
