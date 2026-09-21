CREATE TABLE client_requests (
    id          BIGSERIAL PRIMARY KEY,
    trainer_id  BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    client_id   BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    status      TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (trainer_id <> client_id)
);

CREATE UNIQUE INDEX uq_client_requests_pending
    ON client_requests (trainer_id, client_id)
    WHERE status = 'pending';

CREATE INDEX idx_client_requests_trainer_status
    ON client_requests (trainer_id, status, created_at DESC);
