-- Video darslar kutubxonasi: Category → Topic → Video.
-- Mavjud programs / exercises / video_url o‘zgarmaydi.

CREATE TABLE video_categories (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL,
    description     TEXT,
    thumbnail_url   TEXT,
    sort_order      INT NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_video_categories_slug ON video_categories (slug);
CREATE INDEX idx_video_categories_active ON video_categories (is_active, sort_order, id);

CREATE TABLE video_topics (
    id              BIGSERIAL PRIMARY KEY,
    category_id     BIGINT NOT NULL REFERENCES video_categories (id),
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL,
    description     TEXT,
    thumbnail_url   TEXT,
    sort_order      INT NOT NULL DEFAULT 0,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX uq_video_topics_category_slug ON video_topics (category_id, slug);
CREATE UNIQUE INDEX uq_video_topics_category_name ON video_topics (category_id, lower(name));
CREATE INDEX idx_video_topics_category ON video_topics (category_id, is_active, sort_order, id);

CREATE TABLE video_lessons (
    id                  BIGSERIAL PRIMARY KEY,
    title               TEXT NOT NULL,
    description         TEXT,
    trainer_id          BIGINT REFERENCES users (id) ON DELETE SET NULL,
    category_id         BIGINT NOT NULL REFERENCES video_categories (id),
    topic_id            BIGINT NOT NULL REFERENCES video_topics (id),
    source_type         TEXT NOT NULL CHECK (source_type IN ('admin', 'trainer')),
    video_url           TEXT,
    thumbnail_url       TEXT,
    duration_seconds    INT,
    level               TEXT,
    exercise_id         BIGINT REFERENCES exercises (id) ON DELETE SET NULL,
    exercise_details    JSONB NOT NULL DEFAULT '{}'::jsonb,
    status              TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'processing', 'pending_review', 'published', 'rejected', 'archived')),
    rejection_reason    TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    published_at        TIMESTAMPTZ
);

CREATE INDEX idx_video_lessons_category ON video_lessons (category_id);
CREATE INDEX idx_video_lessons_topic ON video_lessons (topic_id);
CREATE INDEX idx_video_lessons_trainer ON video_lessons (trainer_id);
CREATE INDEX idx_video_lessons_status ON video_lessons (status, published_at DESC, id DESC);
CREATE INDEX idx_video_lessons_exercise ON video_lessons (exercise_id);

CREATE TABLE client_video_assignments (
    id              BIGSERIAL PRIMARY KEY,
    client_id       BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    trainer_id      BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    video_id        BIGINT NOT NULL REFERENCES video_lessons (id) ON DELETE RESTRICT,
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked')),
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (client_id, video_id)
);

CREATE INDEX idx_client_video_client ON client_video_assignments (client_id, status, assigned_at DESC);
CREATE INDEX idx_client_video_trainer ON client_video_assignments (trainer_id, status);
CREATE INDEX idx_client_video_video ON client_video_assignments (video_id, status);

CREATE TABLE video_audit_log (
    id              BIGSERIAL PRIMARY KEY,
    video_id        BIGINT NOT NULL REFERENCES video_lessons (id) ON DELETE CASCADE,
    actor_id        BIGINT REFERENCES users (id) ON DELETE SET NULL,
    action          TEXT NOT NULL,
    from_status     TEXT,
    to_status       TEXT,
    reason          TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_video_audit_video ON video_audit_log (video_id, created_at DESC);

INSERT INTO video_categories (name, slug, description, sort_order) VALUES
    ('Набор массы', 'nabor-massy', 'Силовые видеоуроки для роста мышц', 1),
    ('Похудение', 'pohudenie', 'Кардио и жиросжигающие занятия', 2),
    ('Сила и выносливость', 'sila-i-vynoslivost', 'Силовая выносливость и общая подготовка', 3),
    ('Для начинающих', 'dlya-nachinayushchih', 'Базовая техника и первые тренировки', 4);

INSERT INTO video_topics (category_id, name, slug, sort_order)
SELECT c.id, t.name, t.slug, t.sort_order
FROM video_categories c
JOIN (
    VALUES
        ('nabor-massy', 'Грудные мышцы', 'grudnye-myshcy', 1),
        ('nabor-massy', 'Плечи', 'plechi', 2),
        ('nabor-massy', 'Ноги', 'nogi', 3),
        ('pohudenie', 'Кардио', 'kardio', 1),
        ('pohudenie', 'Всё тело', 'vsyo-telo', 2),
        ('sila-i-vynoslivost', 'Силовая выносливость', 'silovaya-vynoslivost', 1),
        ('dlya-nachinayushchih', 'Базовая техника', 'bazovaya-tehnika', 1)
) AS t(cat_slug, name, slug, sort_order) ON t.cat_slug = c.slug;
