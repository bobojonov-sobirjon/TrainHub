-- Offline sync idempotency for session sets (§41).
ALTER TABLE session_sets
    ADD COLUMN IF NOT EXISTS client_op_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS uq_session_sets_client_op
    ON session_sets (session_exercise_id, client_op_id)
    WHERE client_op_id IS NOT NULL;
