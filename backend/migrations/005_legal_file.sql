ALTER TABLE legal_documents
    ADD COLUMN IF NOT EXISTS file_url TEXT,
    ADD COLUMN IF NOT EXISTS file_name TEXT;

ALTER TABLE legal_documents
    ALTER COLUMN body_md SET DEFAULT '';
