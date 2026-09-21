CREATE TABLE trainer_profiles (
    user_id                 BIGINT PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    bio                     TEXT,
    experience_years        INT,
    specializations         TEXT[] NOT NULL DEFAULT '{}',
    work_formats            TEXT[] NOT NULL DEFAULT '{}',
    session_price_amount    NUMERIC(12, 2),
    session_price_currency  TEXT NOT NULL DEFAULT 'RUB',
    session_duration_min    INT NOT NULL DEFAULT 60,
    free_first_consult      BOOLEAN NOT NULL DEFAULT FALSE,
    category                TEXT,
    rating_avg              NUMERIC(3, 2) NOT NULL DEFAULT 0,
    reviews_count           INT NOT NULL DEFAULT 0,
    is_verified             BOOLEAN NOT NULL DEFAULT FALSE,
    cover_url               TEXT,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE trainer_clients (
    id               BIGSERIAL PRIMARY KEY,
    trainer_id       BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    client_id        BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    status           TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new', 'permanent', 'paused', 'archived')),
    training_format  TEXT,
    goals            TEXT[] NOT NULL DEFAULT '{}',
    invited_via      TEXT NOT NULL DEFAULT 'manual',
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at      TIMESTAMPTZ,
    UNIQUE (trainer_id, client_id)
);

CREATE TABLE contraindications (
    id                 BIGSERIAL PRIMARY KEY,
    trainer_client_id  BIGINT NOT NULL REFERENCES trainer_clients (id) ON DELETE CASCADE,
    text               TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE trainer_notes (
    id                 BIGSERIAL PRIMARY KEY,
    trainer_client_id  BIGINT NOT NULL REFERENCES trainer_clients (id) ON DELETE CASCADE,
    text               TEXT NOT NULL,
    created_by         BIGINT NOT NULL REFERENCES users (id),
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at         TIMESTAMPTZ
);

CREATE TABLE body_measurements (
    id              BIGSERIAL PRIMARY KEY,
    client_id       BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    recorded_by     BIGINT REFERENCES users (id),
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    weight_kg       NUMERIC(6, 2),
    body_fat_pct    NUMERIC(5, 2),
    muscle_mass_kg  NUMERIC(6, 2),
    water_pct       NUMERIC(5, 2),
    chest_cm        NUMERIC(6, 2),
    back_cm         NUMERIC(6, 2),
    waist_cm        NUMERIC(6, 2),
    hips_cm         NUMERIC(6, 2),
    thigh_cm        NUMERIC(6, 2),
    calf_cm         NUMERIC(6, 2),
    neck_cm         NUMERIC(6, 2),
    shoulders_cm    NUMERIC(6, 2),
    arm_cm          NUMERIC(6, 2),
    forearm_cm      NUMERIC(6, 2)
);

CREATE TABLE exercises (
    id                  BIGSERIAL PRIMARY KEY,
    owner_id            BIGINT REFERENCES users (id),
    name                TEXT NOT NULL,
    photo_url           TEXT,
    video_url           TEXT,
    equipment           TEXT,
    primary_muscle      TEXT,
    secondary_muscles   TEXT[] NOT NULL DEFAULT '{}',
    exercise_type       TEXT NOT NULL DEFAULT 'strength',
    is_public           BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE programs (
    id                  BIGSERIAL PRIMARY KEY,
    author_id           BIGINT REFERENCES users (id),
    source              TEXT NOT NULL DEFAULT 'catalog' CHECK (source IN ('catalog', 'trainer', 'user_copy')),
    title               TEXT NOT NULL,
    cover_url           TEXT,
    description         TEXT,
    level               TEXT,
    goals               TEXT[] NOT NULL DEFAULT '{}',
    equipment           TEXT[] NOT NULL DEFAULT '{}',
    workouts_per_week   INT,
    duration_weeks      INT,
    is_pro              BOOLEAN NOT NULL DEFAULT FALSE,
    status              TEXT NOT NULL DEFAULT 'published' CHECK (status IN ('draft', 'published', 'archived')),
    saves_count         INT NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE program_weeks (
    id           BIGSERIAL PRIMARY KEY,
    program_id   BIGINT NOT NULL REFERENCES programs (id) ON DELETE CASCADE,
    week_index   INT NOT NULL,
    title        TEXT,
    is_preview   BOOLEAN NOT NULL DEFAULT FALSE,
    UNIQUE (program_id, week_index)
);

CREATE TABLE program_days (
    id              BIGSERIAL PRIMARY KEY,
    program_id      BIGINT NOT NULL REFERENCES programs (id) ON DELETE CASCADE,
    week_id         BIGINT REFERENCES program_weeks (id) ON DELETE SET NULL,
    title           TEXT NOT NULL,
    description     TEXT,
    sort_order      INT NOT NULL DEFAULT 0,
    duration_min    INT,
    focus_muscles   TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE program_day_exercises (
    id              BIGSERIAL PRIMARY KEY,
    program_day_id  BIGINT NOT NULL REFERENCES program_days (id) ON DELETE CASCADE,
    exercise_id     BIGINT NOT NULL REFERENCES exercises (id),
    sort_order      INT NOT NULL DEFAULT 0,
    sets            INT,
    reps_min        INT,
    reps_max        INT,
    note            TEXT
);

CREATE TABLE user_programs (
    user_id     BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    program_id  BIGINT NOT NULL REFERENCES programs (id) ON DELETE CASCADE,
    saved_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, program_id)
);

CREATE TABLE calendar_events (
    id              BIGSERIAL PRIMARY KEY,
    trainer_id      BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    client_id       BIGINT REFERENCES users (id),
    session_id      BIGINT,
    starts_at       TIMESTAMPTZ NOT NULL,
    ends_at         TIMESTAMPTZ NOT NULL,
    duration_min    INT,
    format          TEXT,
    kinds           TEXT[] NOT NULL DEFAULT '{}',
    focus_muscles   TEXT[] NOT NULL DEFAULT '{}',
    status          TEXT NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled', 'no_show')),
    note            TEXT,
    reminder        TEXT NOT NULL DEFAULT 'none' CHECK (reminder IN ('none', '1h', '3h')),
    repeat_weekly   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE workout_sessions (
    id                  BIGSERIAL PRIMARY KEY,
    trainer_id          BIGINT REFERENCES users (id),
    lead_client_id      BIGINT REFERENCES users (id),
    source              TEXT NOT NULL DEFAULT 'new',
    kinds               TEXT[] NOT NULL DEFAULT '{}',
    program_day_id      BIGINT REFERENCES program_days (id),
    calendar_event_id   BIGINT REFERENCES calendar_events (id),
    status              TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'in_progress', 'completed', 'cancelled')),
    started_at          TIMESTAMPTZ,
    finished_at         TIMESTAMPTZ,
    duration_sec        INT,
    calories            INT,
    distance_km         NUMERIC(6, 2),
    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE calendar_events
    ADD CONSTRAINT calendar_events_session_fk
    FOREIGN KEY (session_id) REFERENCES workout_sessions (id) ON DELETE SET NULL;

CREATE TABLE workout_session_clients (
    session_id  BIGINT NOT NULL REFERENCES workout_sessions (id) ON DELETE CASCADE,
    client_id   BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    PRIMARY KEY (session_id, client_id)
);

CREATE TABLE session_exercises (
    id           BIGSERIAL PRIMARY KEY,
    session_id   BIGINT NOT NULL REFERENCES workout_sessions (id) ON DELETE CASCADE,
    exercise_id  BIGINT NOT NULL REFERENCES exercises (id),
    sort_order   INT NOT NULL DEFAULT 0,
    rest_sec     INT,
    status       TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'active', 'done', 'skipped'))
);

CREATE TABLE session_sets (
    id                   BIGSERIAL PRIMARY KEY,
    session_exercise_id  BIGINT NOT NULL REFERENCES session_exercises (id) ON DELETE CASCADE,
    set_index            INT NOT NULL,
    weight_kg            NUMERIC(6, 2),
    reps                 INT,
    is_warmup            BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at         TIMESTAMPTZ
);

CREATE TABLE personal_notes (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    body        TEXT NOT NULL DEFAULT '',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at  TIMESTAMPTZ
);

CREATE TABLE photo_progress_sets (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    taken_on    DATE NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE photo_progress_images (
    id          BIGSERIAL PRIMARY KEY,
    set_id      BIGINT NOT NULL REFERENCES photo_progress_sets (id) ON DELETE CASCADE,
    angle       TEXT NOT NULL CHECK (angle IN ('front', 'side', 'back')),
    image_url   TEXT NOT NULL,
    sort_order  INT NOT NULL DEFAULT 0
);

CREATE TABLE notification_preferences (
    user_id              BIGINT PRIMARY KEY REFERENCES users (id) ON DELETE CASCADE,
    push_enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    email_enabled        BOOLEAN NOT NULL DEFAULT FALSE,
    workout_reminder     BOOLEAN NOT NULL DEFAULT TRUE,
    new_client_request   BOOLEAN NOT NULL DEFAULT TRUE,
    client_report        BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE notifications (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    type          TEXT NOT NULL,
    title         TEXT NOT NULL,
    body          TEXT,
    payload_json  JSONB,
    is_read       BOOLEAN NOT NULL DEFAULT FALSE,
    scheduled_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE attention_items (
    id           BIGSERIAL PRIMARY KEY,
    trainer_id   BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    client_id    BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    reason       TEXT NOT NULL,
    is_resolved  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE subscription_plans (
    id            BIGSERIAL PRIMARY KEY,
    audience      TEXT NOT NULL CHECK (audience IN ('pro_client', 'pro_trainer')),
    code          TEXT NOT NULL UNIQUE,
    period        TEXT NOT NULL CHECK (period IN ('month', 'year')),
    price_amount  NUMERIC(12, 2) NOT NULL,
    currency      TEXT NOT NULL DEFAULT 'RUB',
    discount_pct  INT NOT NULL DEFAULT 0,
    is_active     BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE subscriptions (
    id                    BIGSERIAL PRIMARY KEY,
    user_id               BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    plan_id               BIGINT NOT NULL REFERENCES subscription_plans (id),
    audience              TEXT NOT NULL,
    status                TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('active', 'expired', 'cancelled', 'pending')),
    starts_at             TIMESTAMPTZ,
    ends_at               TIMESTAMPTZ,
    auto_renew            BOOLEAN NOT NULL DEFAULT TRUE,
    cancel_at_period_end  BOOLEAN NOT NULL DEFAULT FALSE,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE payments (
    id               BIGSERIAL PRIMARY KEY,
    user_id          BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    subscription_id  BIGINT REFERENCES subscriptions (id),
    amount           NUMERIC(12, 2) NOT NULL,
    currency         TEXT NOT NULL DEFAULT 'RUB',
    status           TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'refunded', 'failed')),
    provider_event_id TEXT UNIQUE,
    paid_at          TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE faq_articles (
    id            BIGSERIAL PRIMARY KEY,
    slug          TEXT NOT NULL UNIQUE,
    question      TEXT NOT NULL,
    answer        TEXT NOT NULL,
    audience      TEXT NOT NULL DEFAULT 'all',
    sort_order    INT NOT NULL DEFAULT 0,
    is_published  BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE legal_documents (
    id            BIGSERIAL PRIMARY KEY,
    type          TEXT NOT NULL UNIQUE CHECK (type IN ('terms', 'privacy')),
    version       TEXT NOT NULL DEFAULT '1.0',
    body_md       TEXT NOT NULL,
    published_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE support_tickets (
    id          BIGSERIAL PRIMARY KEY,
    user_id     BIGINT NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    subject     TEXT NOT NULL,
    message     TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'answered', 'closed')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_trainer_clients_trainer ON trainer_clients (trainer_id);
CREATE INDEX idx_trainer_clients_client ON trainer_clients (client_id);
CREATE INDEX idx_measurements_client ON body_measurements (client_id, recorded_at DESC);
CREATE INDEX idx_calendar_trainer_start ON calendar_events (trainer_id, starts_at);
CREATE INDEX idx_sessions_trainer ON workout_sessions (trainer_id, created_at DESC);
CREATE INDEX idx_sessions_client ON workout_sessions (lead_client_id, created_at DESC);
CREATE INDEX idx_programs_source ON programs (source, status);
CREATE INDEX idx_exercises_owner ON exercises (owner_id);
CREATE INDEX idx_notifications_user ON notifications (user_id, created_at DESC);
CREATE INDEX idx_subscriptions_user ON subscriptions (user_id, status);
CREATE INDEX idx_payments_user ON payments (user_id, created_at DESC);

INSERT INTO subscription_plans (audience, code, period, price_amount, currency, discount_pct) VALUES
    ('pro_client', 'client_pro_month', 'month', 90.99, 'RUB', 0),
    ('pro_client', 'client_pro_year', 'year', 15000, 'RUB', 40),
    ('pro_trainer', 'trainer_pro_month', 'month', 90.99, 'RUB', 0),
    ('pro_trainer', 'trainer_pro_year', 'year', 15000, 'RUB', 25);

INSERT INTO exercises (owner_id, name, equipment, primary_muscle, exercise_type, is_public) VALUES
    (NULL, 'Жим гантелей', 'dumbbells', 'chest', 'strength', TRUE),
    (NULL, 'Приседания', 'none', 'thighs', 'strength', TRUE),
    (NULL, 'Тяга верхнего блока', 'machine', 'back', 'strength', TRUE);

INSERT INTO programs (author_id, source, title, description, level, goals, equipment, workouts_per_week, duration_weeks, is_pro, status)
VALUES (NULL, 'catalog', 'Жимы / ноги (Начальный)', 'Базовый комплекс из 3 тренировок в неделю', 'beginner', ARRAY['gain_muscle'], ARRAY['gym'], 3, 4, FALSE, 'published');

INSERT INTO program_days (program_id, title, description, sort_order, duration_min)
SELECT id, 'Жимы', 'Первая тренировка недели', 1, 45 FROM programs WHERE title = 'Жимы / ноги (Начальный)';

INSERT INTO faq_articles (slug, question, answer, audience, sort_order) VALUES
    ('add-client', 'Как добавить нового клиента?', 'Откройте список клиентов и нажмите +.', 'trainer', 1),
    ('pro', 'Как работает подписка PRO?', 'Месячный и годовой тариф. Функции активны до ends_at.', 'all', 2);

INSERT INTO legal_documents (type, version, body_md) VALUES
    ('terms', '1.0', '1. Общие положения. Использование TrainHub.'),
    ('privacy', '1.0', 'Какие данные мы собираем и как используем.');

INSERT INTO dictionaries (category, code, title_ru, sort_order) VALUES
    ('muscle_group', 'neck', 'Шея', 1),
    ('muscle_group', 'shoulders', 'Плечи', 2),
    ('muscle_group', 'chest', 'Грудь', 3),
    ('muscle_group', 'back', 'Спина', 4),
    ('muscle_group', 'waist', 'Талия', 5),
    ('muscle_group', 'glutes', 'Ягодицы', 6),
    ('muscle_group', 'thighs', 'Бёдра', 7),
    ('muscle_group', 'calves', 'Икры', 8),
    ('muscle_group', 'biceps', 'Бицепс', 9),
    ('muscle_group', 'triceps', 'Трицепс', 10),
    ('muscle_group', 'forearms', 'Предплечья', 11),
    ('muscle_group', 'other', 'Другое', 12),
    ('workout_kind', 'strength', 'Силовая', 1),
    ('workout_kind', 'functional', 'Функциональный', 2),
    ('workout_kind', 'cardio', 'Кардио', 3),
    ('workout_kind', 'stretching', 'Растяжка', 4),
    ('workout_kind', 'circuit', 'Круговая', 5),
    ('workout_kind', 'interval', 'Интервальная', 6),
    ('workout_kind', 'rehab', 'Реабилитация', 7),
    ('workout_kind', 'endurance', 'Выносливость', 8)
ON CONFLICT (category, code) DO NOTHING;
