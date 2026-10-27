-- Contact channels for trainer↔client (phone mandatory in app flows; WA/TG optional).
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS whatsapp TEXT,
    ADD COLUMN IF NOT EXISTS telegram TEXT;

COMMENT ON COLUMN users.whatsapp IS 'WhatsApp number E.164 or digits; empty = hide in UI';
COMMENT ON COLUMN users.telegram IS 'Telegram username without @; empty = hide in UI';
