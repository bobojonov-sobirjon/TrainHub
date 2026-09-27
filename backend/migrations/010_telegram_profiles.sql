CREATE TABLE telegram_profiles (
    telegram_user_id  BIGINT PRIMARY KEY,
    chat_id           BIGINT NOT NULL,
    phone             TEXT UNIQUE,
    username          TEXT,
    first_name        TEXT,
    last_name         TEXT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_telegram_profiles_username ON telegram_profiles (lower(username));
CREATE INDEX idx_telegram_profiles_phone ON telegram_profiles (phone);
