ALTER TABLE users
    ADD COLUMN IF NOT EXISTS weight_goal_kg NUMERIC(6, 2);

ALTER TABLE trainer_clients
    ADD COLUMN IF NOT EXISTS target_weight_kg NUMERIC(6, 2);

ALTER TABLE body_measurements
    ADD COLUMN IF NOT EXISTS arm_left_cm NUMERIC(6, 2),
    ADD COLUMN IF NOT EXISTS arm_right_cm NUMERIC(6, 2);

ALTER TABLE programs
    ADD COLUMN IF NOT EXISTS share_token TEXT UNIQUE;

CREATE TABLE IF NOT EXISTS trainer_reviews (
    id          BIGSERIAL PRIMARY KEY,
    trainer_id  BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    client_id   BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    rating      NUMERIC(2, 1) NOT NULL CHECK (rating >= 1 AND rating <= 5),
    text        TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (trainer_id, client_id)
);

CREATE INDEX IF NOT EXISTS idx_trainer_reviews_trainer ON trainer_reviews (trainer_id, created_at DESC);

CREATE TABLE IF NOT EXISTS trainer_bookmarks (
    user_id     BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    trainer_id  BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, trainer_id)
);

CREATE TABLE IF NOT EXISTS payment_methods (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    brand       TEXT NOT NULL DEFAULT 'card',
    last4       TEXT NOT NULL,
    is_default  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_payment_methods_user ON payment_methods (user_id);
