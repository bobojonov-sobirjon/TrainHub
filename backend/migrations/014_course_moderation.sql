-- Course-level moderation, week wiring, client course assignments, exercise↔video_lesson link.
-- Reuses programs / program_weeks / program_days / video_lessons.

-- 1) Expand program status for course moderation
ALTER TABLE programs DROP CONSTRAINT IF EXISTS programs_status_check;
ALTER TABLE programs
    ADD CONSTRAINT programs_status_check
    CHECK (status IN ('draft', 'pending_review', 'published', 'rejected', 'archived'));

ALTER TABLE programs
    ADD COLUMN IF NOT EXISTS reject_reason TEXT,
    ADD COLUMN IF NOT EXISTS submitted_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reviewed_by BIGINT REFERENCES users (id);

CREATE INDEX IF NOT EXISTS idx_programs_status ON programs (status);
CREATE INDEX IF NOT EXISTS idx_programs_author_status ON programs (author_id, status);

-- 2) Day exercise may reference a library video lesson (reuse, no duplicate file)
ALTER TABLE program_day_exercises
    ADD COLUMN IF NOT EXISTS video_lesson_id BIGINT REFERENCES video_lessons (id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS rest_sec INT,
    ADD COLUMN IF NOT EXISTS weight_kg NUMERIC(8, 2);

CREATE INDEX IF NOT EXISTS idx_pde_video_lesson ON program_day_exercises (video_lesson_id);

-- 3) Trainer assigns a published/owned course to a linked client
CREATE TABLE IF NOT EXISTS client_program_assignments (
    id              BIGSERIAL PRIMARY KEY,
    program_id      BIGINT NOT NULL REFERENCES programs (id) ON DELETE CASCADE,
    trainer_id      BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    client_id       BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    link_id         BIGINT REFERENCES trainer_clients (id) ON DELETE SET NULL,
    status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active', 'completed', 'revoked')),
    note            TEXT,
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at      TIMESTAMPTZ,
    UNIQUE (program_id, client_id)
);

CREATE INDEX IF NOT EXISTS idx_cpa_client ON client_program_assignments (client_id, status);
CREATE INDEX IF NOT EXISTS idx_cpa_trainer ON client_program_assignments (trainer_id, status);

-- 4) Moderation audit (course-level)
CREATE TABLE IF NOT EXISTS program_audit_log (
    id              BIGSERIAL PRIMARY KEY,
    program_id      BIGINT NOT NULL REFERENCES programs (id) ON DELETE CASCADE,
    actor_id        BIGINT REFERENCES users (id),
    action          TEXT NOT NULL,
    detail          JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_program_audit_program ON program_audit_log (program_id, created_at DESC);
