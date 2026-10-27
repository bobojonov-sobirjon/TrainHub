-- Rest day status + reminder dedupe for background jobs
ALTER TABLE calendar_events DROP CONSTRAINT IF EXISTS calendar_events_status_check;
ALTER TABLE calendar_events
    ADD CONSTRAINT calendar_events_status_check
    CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled', 'no_show', 'rest'));

ALTER TABLE calendar_events
    ADD COLUMN IF NOT EXISTS reminder_sent_at TIMESTAMPTZ;
