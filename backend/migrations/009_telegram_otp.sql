CREATE TABLE telegram_contacts (
    phone             TEXT PRIMARY KEY,
    chat_id           BIGINT NOT NULL,
    telegram_user_id  BIGINT NOT NULL,
    first_name        TEXT,
    last_name         TEXT,
    username          TEXT,
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_telegram_contacts_chat ON telegram_contacts (chat_id);

CREATE TABLE telegram_otps (
    phone       TEXT PRIMARY KEY,
    code_hash   TEXT NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    attempts    INT NOT NULL DEFAULT 0,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
