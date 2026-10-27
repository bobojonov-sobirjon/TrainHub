-- Live session inactivity: last activity + abandoned status.

ALTER TABLE workout_sessions
    ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ;

UPDATE workout_sessions
SET last_activity_at = COALESCE(started_at, created_at, NOW())
WHERE last_activity_at IS NULL;

ALTER TABLE workout_sessions
    DROP CONSTRAINT IF EXISTS workout_sessions_status_check;

ALTER TABLE workout_sessions
    ADD CONSTRAINT workout_sessions_status_check
    CHECK (status IN ('draft', 'in_progress', 'completed', 'cancelled', 'abandoned'));

CREATE INDEX IF NOT EXISTS idx_sessions_in_progress_activity
    ON workout_sessions (status, last_activity_at)
    WHERE status = 'in_progress';
