-- Group workouts: every client gets own exercises and sets.
ALTER TABLE session_exercises
    ADD COLUMN IF NOT EXISTS client_id BIGINT REFERENCES users (id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_session_exercises_session_client
    ON session_exercises (session_id, client_id);

COMMENT ON COLUMN session_exercises.client_id IS 'Owner client; NULL = shared by all participants (solo and older sessions).';
