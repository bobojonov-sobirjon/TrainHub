"""Idempotent demo data for TrainHub. Password for all demo users: Demo12345"""

import asyncio
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.security import hash_password
from app.db.connection import execute, fetch, fetchrow
from app.db.pool import close_pool, create_pool
from app.db.sql_loader import sql
from app.db.transactions import transaction

DEMO_PASSWORD = "Demo12345"
NOW = datetime.now(timezone.utc)


def _dt(days: int, hour: int = 10) -> datetime:
    return NOW + timedelta(days=days, hours=hour - NOW.hour)


async def _user(conn, email, phone, first, last, gender, birth, height, role, shadow=False):
    existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", email)
    if existing:
        return existing["id"]
    row = await conn.fetchrow(
        sql("auth/insert_user.sql"),
        email,
        phone,
        hash_password(DEMO_PASSWORD),
        first,
        last,
        gender,
        birth,
    )
    await conn.execute("UPDATE users SET height_cm = $2, is_shadow = $3 WHERE id = $1", row["id"], height, shadow)
    await conn.execute(sql("auth/insert_role.sql"), row["id"], role)
    await conn.execute(
        "INSERT INTO notification_preferences (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
        row["id"],
    )
    return row["id"]


async def seed() -> None:
    await create_pool()
    demo = await fetch("SELECT id FROM users WHERE email LIKE '%@trainhub.demo'")
    if demo:
        print("Demo users already exist — wiping previous demo set")
        await execute("DELETE FROM users WHERE email LIKE '%@trainhub.demo'")

    async with transaction() as conn:
        t1 = await _user(conn, "ivan.trainer@trainhub.demo", "+79001110001", "Иван", "Соколов", "male", date(1990, 3, 12), 182, "trainer")
        t2 = await _user(conn, "maria.trainer@trainhub.demo", "+79001110002", "Мария", "Орлова", "female", date(1992, 7, 8), 168, "trainer")
        t3 = await _user(conn, "alex.trainer@trainhub.demo", "+79001110003", "Алексей", "Волков", "male", date(1987, 11, 21), 178, "trainer")
        t4 = await _user(conn, "elena.trainer@trainhub.demo", "+79001110004", "Елена", "Ким", "female", date(1995, 1, 30), 165, "trainer")

        c1 = await _user(conn, "anna.client@trainhub.demo", "+79002220001", "Анна", "Смирнова", "female", date(1998, 4, 15), 164, "client")
        c2 = await _user(conn, "dmitry.client@trainhub.demo", "+79002220002", "Дмитрий", "Кузнецов", "male", date(1994, 9, 2), 181, "client")
        c3 = await _user(conn, "olga.client@trainhub.demo", "+79002220003", "Ольга", "Новикова", "female", date(2000, 6, 19), 170, "client")
        c4 = await _user(conn, "pavel.client@trainhub.demo", "+79002220004", "Павел", "Морозов", "male", date(1991, 12, 5), 176, "client")
        c5 = await _user(conn, "irina.client@trainhub.demo", "+79002220005", "Ирина", "Белова", "female", date(1996, 2, 28), 162, "client")
        c6 = await _user(conn, "sergey.client@trainhub.demo", "+79002220006", "Сергей", "Попов", "male", date(1989, 8, 14), 184, "client")
        c7 = await _user(conn, "nina.client@trainhub.demo", "+79002220007", "Нина", "Фролова", "female", date(1999, 10, 9), 158, "client")
        c8 = await _user(conn, "igor.client@trainhub.demo", "+79002220008", "Игорь", "Захаров", "male", date(1993, 5, 17), 179, "client")
        sh1 = await _user(conn, "shadow.katya@trainhub.demo", "+79003330001", "Катя", "Ручная", "female", date(2001, 3, 3), 160, "client", True)
        sh2 = await _user(conn, "shadow.oleg@trainhub.demo", "+79003330002", "Олег", "Теневой", "male", date(1988, 7, 7), 175, "client", True)

        await conn.execute(
            """
            INSERT INTO trainer_profiles (
                user_id, bio, experience_years, specializations, work_formats,
                session_price_amount, session_duration_min, free_first_consult, category,
                rating_avg, reviews_count, is_verified
            ) VALUES
                ($1, 'Силовой тренер, готовлю к жиму и массе.', 8, ARRAY['strength','gain_muscle'], ARRAY['gym','hybrid'], 3500, 60, TRUE, 'strength', 4.80, 36, TRUE),
                ($2, 'Похудение и функционал. Онлайн + зал.', 6, ARRAY['lose_weight','endurance'], ARRAY['online','gym'], 2800, 50, TRUE, 'cardio', 4.70, 22, TRUE),
                ($3, 'Реабилитация коленей и спины.', 11, ARRAY['rehab','flexibility'], ARRAY['gym','visit'], 4000, 45, FALSE, 'strength', 4.90, 18, TRUE),
                ($4, 'Женский тренинг и рельеф.', 4, ARRAY['definition','lose_weight'], ARRAY['online','home'], 2200, 40, TRUE, 'female', 4.50, 9, FALSE)
            ON CONFLICT (user_id) DO UPDATE SET bio = EXCLUDED.bio
            """,
            t1, t2, t3, t4,
        )

        links = []
        pairs = [
            (t1, c1, "permanent", "gym", ["lose_weight", "definition"], "search"),
            (t1, c2, "permanent", "gym", ["gain_muscle", "strength"], "search"),
            (t1, c3, "new", "hybrid", ["lose_weight"], "request"),
            (t1, sh1, "new", "gym", ["definition"], "manual"),
            (t2, c4, "permanent", "online", ["lose_weight"], "search"),
            (t2, c5, "paused", "online", ["endurance"], "request"),
            (t2, sh2, "new", "home", ["maintain"], "manual"),
            (t3, c6, "permanent", "gym", ["rehab"], "search"),
            (t3, c7, "new", "visit", ["flexibility"], "manual"),
            (t4, c8, "new", "online", ["definition"], "search"),
            (t4, c1, "paused", "online", ["lose_weight"], "request"),
        ]
        for trainer_id, client_id, status, fmt, goals, via in pairs:
            row = await conn.fetchrow(
                """
                INSERT INTO trainer_clients (trainer_id, client_id, status, training_format, goals, invited_via)
                VALUES ($1,$2,$3,$4,$5,$6)
                RETURNING id
                """,
                trainer_id, client_id, status, fmt, goals, via,
            )
            links.append(row["id"])

        await conn.execute(
            "INSERT INTO contraindications (trainer_client_id, text) VALUES ($1,'Боль в правом колене'), ($2,'Грыжа L4-L5')",
            links[0], links[7],
        )
        await conn.execute(
            """
            INSERT INTO trainer_notes (trainer_client_id, text, created_by) VALUES
                ($1, 'Хорошо держит технику приседа. Увеличить объём.', $2),
                ($3, 'Пропустила пятницу — перенести на субботу.', $2),
                ($4, 'Теневой клиент, пока без приложения.', $2)
            """,
            links[0], t1, links[2], links[3],
        )

        for client_id, recorder, base_w, fat in (
            (c1, t1, 68.4, 27.0),
            (c2, t1, 86.2, 18.5),
            (c3, t1, 61.0, 24.0),
            (c4, t2, 79.5, 22.0),
            (c6, t3, 92.0, 21.0),
        ):
            for week in range(6, -1, -1):
                await conn.execute(
                    """
                    INSERT INTO body_measurements (
                        client_id, recorded_by, recorded_at, weight_kg, body_fat_pct, muscle_mass_kg, water_pct,
                        chest_cm, waist_cm, hips_cm, thigh_cm
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                    """,
                    client_id,
                    recorder,
                    NOW - timedelta(days=week * 7),
                    round(base_w - week * 0.35, 2),
                    round(fat - week * 0.2, 2),
                    round(base_w * 0.42, 2),
                    54.0,
                    98.0 if client_id == c2 else 88.0,
                    round(78 - week * 0.3, 2),
                    96.0,
                    56.0,
                )

        extra_ex = [
            (None, "Жим лёжа", "bench", "chest", ["triceps", "shoulders"], "strength", True),
            (None, "Становая тяга", "plate", "back", ["thighs", "glutes"], "strength", True),
            (None, "Подтягивания", "none", "back", ["biceps"], "strength", True),
            (None, "Выпады", "dumbbells", "thighs", ["glutes"], "strength", True),
            (None, "Планка", "none", "waist", [], "strength", True),
            (None, "Берпи", "none", "other", ["chest", "thighs"], "cardio", True),
            (None, "Гребля", "machine", "back", ["shoulders"], "cardio", True),
            (None, "Разведение гантелей", "dumbbells", "chest", ["shoulders"], "strength", True),
            (None, "Тяга гантели в наклоне", "dumbbells", "back", ["biceps"], "strength", True),
            (None, "Ягодичный мост", "none", "glutes", ["thighs"], "strength", True),
            (t1, "Жим Ивана — пауза 2 сек", "bench", "chest", ["triceps"], "strength", False),
        ]
        ex_ids = []
        for owner, name, eq, muscle, secondary, kind, public in extra_ex:
            row = await conn.fetchrow(
                """
                INSERT INTO exercises (owner_id, name, equipment, primary_muscle, secondary_muscles, exercise_type, is_public)
                VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id
                """,
                owner, name, eq, muscle, secondary, kind, public,
            )
            ex_ids.append(row["id"])

        catalog = await conn.fetchrow("SELECT id FROM programs WHERE title = 'Жимы / ноги (Начальный)'")
        pub_ex = await conn.fetch("SELECT id FROM exercises WHERE is_public = TRUE ORDER BY id")
        pub_ids = [r["id"] for r in pub_ex]

        async def add_program(title, desc, level, goals, weeks, per_week, pro, author, source="catalog"):
            p = await conn.fetchrow(
                """
                INSERT INTO programs (author_id, source, title, description, level, goals, equipment, workouts_per_week, duration_weeks, is_pro, status, saves_count)
                VALUES ($1,$2,$3,$4,$5,$6,ARRAY['gym','dumbbells'],$7,$8,$9,'published',$10)
                RETURNING id
                """,
                author, source, title, desc, level, goals, per_week, weeks, pro, 12 if not pro else 4,
            )
            pid = p["id"]
            for wi in range(1, weeks + 1):
                w = await conn.fetchrow(
                    "INSERT INTO program_weeks (program_id, week_index, title, is_preview) VALUES ($1,$2,$3,$4) RETURNING id",
                    pid, wi, f"Неделя {wi}", wi == 1,
                )
                for di, day_title in enumerate(("Жимы", "Ноги", "Спина")[:per_week], start=1):
                    d = await conn.fetchrow(
                        """
                        INSERT INTO program_days (program_id, week_id, title, description, sort_order, duration_min, focus_muscles)
                        VALUES ($1,$2,$3,$4,$5,50,$6) RETURNING id
                        """,
                        pid, w["id"], f"{day_title} · нед. {wi}", f"{day_title}, неделя {wi}", di, [day_title.lower()],
                    )
                    for si, eid in enumerate(pub_ids[di - 1 : di + 2], start=1):
                        await conn.execute(
                            """
                            INSERT INTO program_day_exercises (program_day_id, exercise_id, sort_order, sets, reps_min, reps_max, note)
                            VALUES ($1,$2,$3,3,8,12,'Контроль техники')
                            """,
                            d["id"], eid, si,
                        )
            return pid

        p_fat = await add_program("Жиросжигание 8 недель", "Кардио + силовые круговые", "beginner", ["lose_weight"], 4, 3, False, t2, "trainer")
        p_mass = await add_program("Масса PRO", "Силовая программа для зала", "intermediate", ["gain_muscle", "strength"], 4, 3, True, t1, "trainer")
        await add_program("Мобильность спины", "Растяжка и rehab-фокус", "beginner", ["rehab", "flexibility"], 2, 2, False, t3, "trainer")

        for uid, pid in ((c1, p_fat), (c2, p_mass), (c4, p_fat), (c3, catalog["id"] if catalog else p_fat)):
            await conn.execute(
                "INSERT INTO user_programs (user_id, program_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                uid, pid,
            )

        day_row = await conn.fetchrow("SELECT id FROM program_days ORDER BY id LIMIT 1")

        events = []
        for i, (trainer_id, client_id, days, status, note) in enumerate(
            (
                (t1, c1, -10, "completed", "Жимовая"),
                (t1, c2, -7, "completed", "Ноги"),
                (t1, c1, -3, "completed", "Спина"),
                (t1, c3, 0, "scheduled", "Сегодня"),
                (t1, c2, 1, "scheduled", "Завтра"),
                (t2, c4, 2, "scheduled", "Онлайн Zoom"),
                (t3, c6, -1, "no_show", "Не пришёл"),
                (t1, c1, 5, "scheduled", "Повтор недели"),
            )
        ):
            start = _dt(days, 10 + (i % 3))
            ev = await conn.fetchrow(
                """
                INSERT INTO calendar_events (
                    trainer_id, client_id, starts_at, ends_at, duration_min, format, kinds, focus_muscles, status, note, reminder
                ) VALUES ($1,$2,$3,$4,60,'gym',ARRAY['strength'],ARRAY['chest'],$5,$6,'1h')
                RETURNING id
                """,
                trainer_id, client_id, start, start + timedelta(hours=1), status, note,
            )
            events.append((ev["id"], trainer_id, client_id, status, start))

        for ev_id, trainer_id, client_id, status, start in events:
            if status not in ("completed", "no_show"):
                continue
            sess_status = "completed" if status == "completed" else "cancelled"
            s = await conn.fetchrow(
                """
                INSERT INTO workout_sessions (
                    trainer_id, lead_client_id, source, kinds, program_day_id, calendar_event_id,
                    status, started_at, finished_at, duration_sec, calories
                ) VALUES ($1,$2,'calendar',ARRAY['strength'],$3,$4,$5,$6,$7,$8,$9)
                RETURNING id
                """,
                trainer_id,
                client_id,
                day_row["id"] if day_row else None,
                ev_id,
                sess_status,
                start,
                start + timedelta(minutes=55),
                3300 if sess_status == "completed" else None,
                420 if sess_status == "completed" else None,
            )
            await conn.execute(
                "INSERT INTO workout_session_clients (session_id, client_id) VALUES ($1,$2)",
                s["id"], client_id,
            )
            await conn.execute("UPDATE calendar_events SET session_id = $1 WHERE id = $2", s["id"], ev_id)
            if sess_status != "completed":
                continue
            for order, eid in enumerate(pub_ids[:3], start=1):
                se = await conn.fetchrow(
                    """
                    INSERT INTO session_exercises (session_id, exercise_id, sort_order, rest_sec, status)
                    VALUES ($1,$2,$3,90,'done') RETURNING id
                    """,
                    s["id"], eid, order,
                )
                for si in range(1, 4):
                    await conn.execute(
                        """
                        INSERT INTO session_sets (session_exercise_id, set_index, weight_kg, reps, is_warmup, completed_at)
                        VALUES ($1,$2,$3,$4,FALSE,$5)
                        """,
                        se["id"], si, 20 + si * 2.5, 10 - si, start + timedelta(minutes=order * 10),
                    )

        await conn.execute(
            """
            INSERT INTO client_requests (trainer_id, client_id, status) VALUES
                ($1,$2,'pending'),
                ($3,$4,'pending'),
                ($5,$6,'rejected')
            """,
            t1, c8, t2, c3, t4, c2,
        )

        await conn.execute(
            """
            INSERT INTO attention_items (trainer_id, client_id, reason, is_resolved) VALUES
                ($1,$2,'Пропустил тренировку 22 сентября', FALSE),
                ($3,$4,'Нет замеров 14 дней', FALSE),
                ($1,$5,'Жалоба на колено', TRUE)
            """,
            t1, c3, t2, c5, c1,
        )

        await conn.execute(
            """
            INSERT INTO notifications (user_id, type, title, body, is_read) VALUES
                ($1,'new_client_request','Новая заявка клиента','Игорь Захаров отправил(а) заявку', FALSE),
                ($1,'client_report','Отчёт по Анне','Вес -1.2 кг за месяц', TRUE),
                ($2,'workout_reminder','Тренировка сегодня','Зал, 10:00', FALSE),
                ($3,'invite','Тренер добавил вас','Иван Соколов добавил вас в базу', TRUE)
            """,
            t1, c1, c2,
        )

        plan_t = await conn.fetchrow("SELECT id FROM subscription_plans WHERE code = 'trainer_pro_month'")
        plan_c = await conn.fetchrow("SELECT id FROM subscription_plans WHERE code = 'client_pro_month'")
        sub_t = await conn.fetchrow(
            """
            INSERT INTO subscriptions (user_id, plan_id, audience, status, starts_at, ends_at, auto_renew)
            VALUES ($1,$2,'pro_trainer','active', NOW() - INTERVAL '10 days', NOW() + INTERVAL '20 days', TRUE)
            RETURNING id
            """,
            t1, plan_t["id"],
        )
        sub_c = await conn.fetchrow(
            """
            INSERT INTO subscriptions (user_id, plan_id, audience, status, starts_at, ends_at, auto_renew)
            VALUES ($1,$2,'pro_client','active', NOW() - INTERVAL '5 days', NOW() + INTERVAL '25 days', TRUE)
            RETURNING id
            """,
            c2, plan_c["id"],
        )
        await conn.execute(
            """
            INSERT INTO payments (user_id, subscription_id, amount, currency, status, provider_event_id, paid_at) VALUES
                ($1,$2,90.99,'RUB','paid','demo_evt_trainer_1', NOW() - INTERVAL '10 days'),
                ($3,$4,90.99,'RUB','paid','demo_evt_client_1', NOW() - INTERVAL '5 days'),
                ($5,NULL,90.99,'RUB','failed','demo_evt_fail_1', NULL)
            """,
            t1, sub_t["id"], c2, sub_c["id"], c4,
        )

        await conn.execute(
            """
            INSERT INTO faq_articles (slug, question, answer, audience, sort_order) VALUES
                ('cancel-sub','Как отменить подписку?','Профиль → Подписка → Отменить автопродление. Доступ до ends_at.','all',3),
                ('shadow-client','Кто такой теневой клиент?','Клиент без входа в приложение, которого тренер завёл вручную.','trainer',4),
                ('measurements','Как часто снимать замеры?','Раз в 7–14 дней, в одно и то же время.','client',5)
            ON CONFLICT (slug) DO NOTHING
            """
        )
        await conn.execute(
            """
            INSERT INTO support_tickets (user_id, subject, message, status) VALUES
                ($1,'Не приходит чек','Оплатил PRO, чек на почту не пришёл','open'),
                ($2,'Ошибка в календаре','Событие дублируется каждую неделю','in_progress'),
                ($3,'Как сменить тренера?','Хочу перейти к другому специалисту','answered')
            """,
            c2, t1, c5,
        )
        await conn.execute(
            """
            INSERT INTO personal_notes (user_id, title, body) VALUES
                ($1,'Питание','Белок 1.6 г/кг, убрать сладкое после 18:00'),
                ($2,'Самочувствие','Колено лучше после разминки')
            """,
            c1, c6,
        )
        photo = await conn.fetchrow(
            "INSERT INTO photo_progress_sets (user_id, taken_on) VALUES ($1, CURRENT_DATE - 14) RETURNING id",
            c1,
        )
        await conn.execute(
            """
            INSERT INTO photo_progress_images (set_id, angle, image_url, sort_order) VALUES
                ($1,'front','/media/demo/anna-front.jpg',1),
                ($1,'side','/media/demo/anna-side.jpg',2),
                ($1,'back','/media/demo/anna-back.jpg',3)
            """,
            photo["id"],
        )

    counts = await fetchrow(
        """
        SELECT
            (SELECT COUNT(*) FROM users WHERE email LIKE '%@trainhub.demo') AS users,
            (SELECT COUNT(*) FROM trainer_clients) AS links,
            (SELECT COUNT(*) FROM body_measurements) AS measurements,
            (SELECT COUNT(*) FROM exercises) AS exercises,
            (SELECT COUNT(*) FROM programs) AS programs,
            (SELECT COUNT(*) FROM calendar_events) AS events,
            (SELECT COUNT(*) FROM workout_sessions) AS sessions,
            (SELECT COUNT(*) FROM client_requests) AS requests
        """
    )
    print("Seeded demo data")
    print(dict(counts))
    print(f"Demo login password for all *@trainhub.demo: {DEMO_PASSWORD}")
    await close_pool()


if __name__ == "__main__":
    asyncio.run(seed())
