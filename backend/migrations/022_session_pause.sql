-- Live workout pause/resume: freeze wall-clock while user rests mid-session.
ALTER TABLE workout_sessions
    ADD COLUMN IF NOT EXISTS paused_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS pause_sec INT NOT NULL DEFAULT 0;

COMMENT ON COLUMN workout_sessions.paused_at IS 'When set, session timer is paused; inactivity abandon is skipped.';
COMMENT ON COLUMN workout_sessions.pause_sec IS 'Accumulated completed pause intervals in seconds.';
