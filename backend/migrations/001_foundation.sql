CREATE SEQUENCE IF NOT EXISTS user_public_id_seq START 100000000;

CREATE TABLE users (
    id              BIGSERIAL PRIMARY KEY,
    public_id       TEXT NOT NULL UNIQUE,
    email           TEXT UNIQUE,
    phone           TEXT UNIQUE,
    password_hash   TEXT,
    first_name      TEXT NOT NULL,
    last_name       TEXT NOT NULL DEFAULT '',
    avatar_url      TEXT,
    gender          TEXT CHECK (gender IS NULL OR gender IN ('male', 'female', 'other')),
    birth_date      DATE,
    height_cm       NUMERIC(5, 1),
    is_shadow       BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_blocked      BOOLEAN NOT NULL DEFAULT FALSE,
    blocked_reason  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_login_at   TIMESTAMPTZ
);

CREATE TABLE user_roles (
    user_id BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    role    TEXT NOT NULL CHECK (role IN ('client', 'trainer', 'admin')),
    PRIMARY KEY (user_id, role)
);

CREATE TABLE refresh_tokens (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    jti        TEXT NOT NULL UNIQUE,
    audience   TEXT NOT NULL CHECK (audience IN ('app', 'admin')),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE password_reset_tokens (
    id         BIGSERIAL PRIMARY KEY,
    user_id    BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at    TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE dictionaries (
    id         BIGSERIAL PRIMARY KEY,
    category   TEXT NOT NULL,
    code       TEXT NOT NULL,
    title_ru   TEXT NOT NULL,
    sort_order INT NOT NULL DEFAULT 0,
    is_active  BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (category, code)
);

CREATE INDEX idx_users_email ON users (email);
CREATE INDEX idx_users_phone ON users (phone);
CREATE INDEX idx_users_public_id ON users (public_id);
CREATE INDEX idx_user_roles_role ON user_roles (role);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens (user_id);
CREATE INDEX idx_refresh_tokens_jti ON refresh_tokens (jti);
CREATE INDEX idx_password_reset_user ON password_reset_tokens (user_id);
CREATE INDEX idx_dictionaries_category ON dictionaries (category, sort_order);
