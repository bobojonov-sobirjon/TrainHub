from datetime import date

from app.core.constants import TRAINER_SORT
from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow
from app.schemas.stage import ReviewIn


async def ensure_profile(user_id: int) -> None:
    await execute(
        """
        INSERT INTO trainer_profiles (user_id)
        VALUES ($1)
        ON CONFLICT (user_id) DO NOTHING
        """,
        user_id,
    )


async def get_profile(user_id: int) -> dict:
    await ensure_profile(user_id)
    row = await fetchrow(
        """
        SELECT
            tp.user_id, tp.bio, tp.experience_years, tp.specializations, tp.work_formats,
            tp.session_price_amount, tp.session_duration_min, tp.free_first_consult,
            tp.category, tp.rating_avg, tp.reviews_count,
            (
                SELECT COUNT(*) FROM trainer_clients tc
                WHERE tc.trainer_id = tp.user_id AND tc.archived_at IS NULL
            ) AS clients_count
        FROM trainer_profiles tp
        WHERE tp.user_id = $1
        """,
        user_id,
    )
    if row is None:
        raise AppError("PROFILE_NOT_FOUND", "Профиль тренера не найден", http_status=404)
    return dict(row)


async def update_profile(user_id: int, data: dict) -> dict:
    await ensure_profile(user_id)
    await execute(
        """
        UPDATE trainer_profiles
        SET
            bio = COALESCE($2, bio),
            experience_years = COALESCE($3, experience_years),
            specializations = COALESCE($4, specializations),
            work_formats = COALESCE($5, work_formats),
            session_price_amount = COALESCE($6, session_price_amount),
            session_duration_min = COALESCE($7, session_duration_min),
            free_first_consult = COALESCE($8, free_first_consult),
            category = COALESCE($9, category),
            updated_at = NOW()
        WHERE user_id = $1
        """,
        user_id,
        data.get("bio"),
        data.get("experience_years"),
        data.get("specializations"),
        data.get("work_formats"),
        data.get("session_price_amount"),
        data.get("session_duration_min"),
        data.get("free_first_consult"),
        data.get("category"),
    )
    return await get_profile(user_id)


async def dashboard(trainer_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT
            (SELECT COUNT(*) FROM trainer_clients WHERE trainer_id = $1 AND archived_at IS NULL) AS clients_count,
            (SELECT COUNT(*) FROM calendar_events
                WHERE trainer_id = $1 AND starts_at::date = CURRENT_DATE AND status = 'completed') AS today_done,
            (SELECT COUNT(*) FROM calendar_events
                WHERE trainer_id = $1 AND starts_at::date = CURRENT_DATE
                  AND status IN ('scheduled', 'in_progress', 'completed')) AS today_planned,
            (SELECT COUNT(*) FROM workout_sessions
                WHERE trainer_id = $1 AND status = 'completed'
                  AND COALESCE(finished_at, created_at) >= date_trunc('month', NOW())) AS month_sessions,
            (SELECT COUNT(*) FROM attention_items
                WHERE trainer_id = $1 AND is_resolved = FALSE) AS attention_count
        """,
        trainer_id,
    )
    return dict(row)


async def list_marketplace(
    category: str | None,
    page: int,
    page_size: int,
    offset: int,
    *,
    q: str | None = None,
    sort: str = "rating",
) -> tuple[list[dict], int]:
    args: list = []
    where = ["ur.role = 'trainer'", "u.is_blocked = FALSE"]
    if category and category != "all":
        args.append(category)
        where.append(f"tp.category = ${len(args)}")
    if q:
        args.append(f"%{q.strip()}%")
        where.append(
            f"(u.first_name ILIKE ${len(args)} OR u.last_name ILIKE ${len(args)} OR u.public_id ILIKE ${len(args)})"
        )
    where_sql = " AND ".join(where)
    order = TRAINER_SORT.get(sort, TRAINER_SORT["rating"])
    total_row = await fetchrow(
        f"""
        SELECT COUNT(*) AS total
        FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        LEFT JOIN trainer_profiles tp ON tp.user_id = u.id
        WHERE {where_sql}
        """,
        *args,
    )
    args.extend([page_size, offset])
    rows = await fetch(
        f"""
        SELECT
            u.id, u.public_id, u.first_name, u.last_name, u.avatar_url,
            COALESCE(tp.rating_avg, 0) AS rating_avg,
            COALESCE(tp.reviews_count, 0) AS reviews_count,
            tp.category,
            (
                SELECT COUNT(*) FROM programs p
                WHERE p.author_id = u.id AND p.status = 'published'
            ) AS programs_count,
            (
                SELECT COUNT(*) FROM trainer_clients tc
                WHERE tc.trainer_id = u.id AND tc.archived_at IS NULL
            ) AS clients_count
        FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        LEFT JOIN trainer_profiles tp ON tp.user_id = u.id
        WHERE {where_sql}
        ORDER BY {order}
        LIMIT ${len(args) - 1} OFFSET ${len(args)}
        """,
        *args,
    )
    return [dict(r) for r in rows], int(total_row["total"])


async def public_trainer(trainer_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT
            u.id, u.public_id, u.first_name, u.last_name, u.avatar_url,
            tp.bio, tp.experience_years, tp.specializations, tp.work_formats,
            tp.session_price_amount, tp.session_duration_min, tp.free_first_consult,
            tp.category, tp.rating_avg, tp.reviews_count
        FROM users u
        JOIN user_roles ur ON ur.user_id = u.id AND ur.role = 'trainer'
        LEFT JOIN trainer_profiles tp ON tp.user_id = u.id
        WHERE u.id = $1
        """,
        trainer_id,
    )
    if row is None:
        raise AppError("TRAINER_NOT_FOUND", "Тренер не найден", http_status=404)
    programs = await fetch(
        """
        SELECT id, title, cover_url, level, duration_weeks, is_pro
        FROM programs
        WHERE author_id = $1 AND status = 'published'
        ORDER BY created_at DESC
        """,
        trainer_id,
    )
    data = dict(row)
    data["programs"] = [dict(p) for p in programs]
    return data


async def reports(trainer_id: int, period: str = "month") -> dict:
    if period not in {"week", "month"}:
        raise AppError("VALIDATION_ERROR", "period: week или month", http_status=422)
    trunc = "week" if period == "week" else "month"
    row = await fetchrow(
        f"""
        SELECT
            COUNT(*) FILTER (WHERE status = 'completed') AS sessions_count,
            COALESCE(SUM(calories) FILTER (WHERE status = 'completed'), 0) AS calories_total,
            COALESCE(SUM(duration_sec) FILTER (WHERE status = 'completed'), 0) AS duration_sec
        FROM workout_sessions
        WHERE trainer_id = $1
          AND COALESCE(finished_at, created_at) >= date_trunc('{trunc}', NOW())
        """,
        trainer_id,
    )
    kinds = await fetch(
        f"""
        SELECT kind, COUNT(*) AS total
        FROM workout_sessions s
        CROSS JOIN LATERAL unnest(COALESCE(s.kinds, ARRAY[]::text[])) AS kind
        WHERE s.trainer_id = $1 AND s.status = 'completed'
          AND COALESCE(s.finished_at, s.created_at) >= date_trunc('{trunc}', NOW())
        GROUP BY kind
        ORDER BY total DESC
        """,
        trainer_id,
    )
    gender = await fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE u.gender = 'male') AS male_count,
            COUNT(*) FILTER (WHERE u.gender = 'female') AS female_count,
            COUNT(*) AS total
        FROM trainer_clients tc
        JOIN users u ON u.id = tc.client_id
        WHERE tc.trainer_id = $1 AND tc.archived_at IS NULL
        """,
        trainer_id,
    )
    movement = await fetchrow(
        f"""
        SELECT
            COUNT(*) FILTER (WHERE archived_at IS NULL AND created_at >= date_trunc('{trunc}', NOW())) AS new_clients,
            COUNT(*) FILTER (WHERE archived_at IS NOT NULL AND archived_at >= date_trunc('{trunc}', NOW())) AS left_clients
        FROM trainer_clients
        WHERE trainer_id = $1
        """,
        trainer_id,
    )
    hours = round(int(row["duration_sec"] or 0) / 3600, 1)
    return {
        "period": period,
        "sessions_count": int(row["sessions_count"]),
        "calories_total": int(row["calories_total"]),
        "hours_total": hours,
        "by_kind": [dict(r) for r in kinds],
        "gender": dict(gender),
        "new_clients": int(movement["new_clients"]),
        "left_clients": int(movement["left_clients"]),
    }


async def attention_list(trainer_id: int) -> list[dict]:
    rows = await fetch(
        """
        SELECT a.id, a.reason, a.created_at, a.is_resolved,
               u.id AS client_id, u.first_name, u.last_name, u.phone, u.avatar_url,
               tc.training_format,
               (
                   SELECT MAX(COALESCE(s.finished_at, s.created_at))
                   FROM workout_sessions s
                   WHERE s.status = 'completed'
                     AND (s.lead_client_id = u.id OR EXISTS (
                         SELECT 1 FROM workout_session_clients c
                         WHERE c.session_id = s.id AND c.client_id = u.id
                     ))
               ) AS last_session_at
        FROM attention_items a
        JOIN users u ON u.id = a.client_id
        LEFT JOIN trainer_clients tc ON tc.trainer_id = a.trainer_id AND tc.client_id = a.client_id
        WHERE a.trainer_id = $1 AND a.is_resolved = FALSE
        ORDER BY a.created_at DESC
        """,
        trainer_id,
    )
    items = []
    for row in rows:
        item = dict(row)
        last = item.get("last_session_at")
        if last:
            item["days_inactive"] = max(0, (date.today() - last.date()).days)
        else:
            item["days_inactive"] = None
        items.append(item)
    return items


async def list_reviews(trainer_id: int) -> list[dict]:
    rows = await fetch(
        """
        SELECT r.id, r.rating, r.text, r.created_at,
               u.id AS client_id, u.first_name, u.last_name, u.avatar_url
        FROM trainer_reviews r
        JOIN users u ON u.id = r.client_id
        WHERE r.trainer_id = $1
        ORDER BY r.created_at DESC
        """,
        trainer_id,
    )
    return [dict(r) for r in rows]


async def upsert_review(trainer_id: int, client_id: int, payload: ReviewIn) -> dict:
    trainer = await fetchrow(
        "SELECT user_id FROM user_roles WHERE user_id = $1 AND role = 'trainer'",
        trainer_id,
    )
    if trainer is None:
        raise AppError("TRAINER_NOT_FOUND", "Тренер не найден", http_status=404)
    await execute(
        """
        INSERT INTO trainer_reviews (trainer_id, client_id, rating, text)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (trainer_id, client_id)
        DO UPDATE SET rating = EXCLUDED.rating, text = EXCLUDED.text, created_at = NOW()
        """,
        trainer_id,
        client_id,
        payload.rating,
        payload.text,
    )
    stats = await fetchrow(
        """
        SELECT COALESCE(AVG(rating), 0) AS rating_avg, COUNT(*) AS reviews_count
        FROM trainer_reviews WHERE trainer_id = $1
        """,
        trainer_id,
    )
    await execute(
        """
        INSERT INTO trainer_profiles (user_id, rating_avg, reviews_count)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id) DO UPDATE
        SET rating_avg = EXCLUDED.rating_avg, reviews_count = EXCLUDED.reviews_count, updated_at = NOW()
        """,
        trainer_id,
        stats["rating_avg"],
        stats["reviews_count"],
    )
    row = await fetchrow(
        "SELECT id, rating, text, created_at FROM trainer_reviews WHERE trainer_id = $1 AND client_id = $2",
        trainer_id,
        client_id,
    )
    return dict(row)


async def list_bookmarks(user_id: int) -> list[dict]:
    rows = await fetch(
        """
        SELECT
            u.id, u.public_id, u.first_name, u.last_name, u.avatar_url,
            COALESCE(tp.rating_avg, 0) AS rating_avg, tp.category
        FROM trainer_bookmarks b
        JOIN users u ON u.id = b.trainer_id
        LEFT JOIN trainer_profiles tp ON tp.user_id = u.id
        WHERE b.user_id = $1
        ORDER BY b.created_at DESC
        """,
        user_id,
    )
    return [dict(r) for r in rows]


async def bookmark_trainer(user_id: int, trainer_id: int) -> None:
    await public_trainer(trainer_id)
    await execute(
        """
        INSERT INTO trainer_bookmarks (user_id, trainer_id)
        VALUES ($1, $2)
        ON CONFLICT DO NOTHING
        """,
        user_id,
        trainer_id,
    )


async def unbookmark_trainer(user_id: int, trainer_id: int) -> None:
    await execute(
        "DELETE FROM trainer_bookmarks WHERE user_id = $1 AND trainer_id = $2",
        user_id,
        trainer_id,
    )


async def resolve_attention(trainer_id: int, item_id: int) -> None:
    row = await fetchrow(
        "SELECT id FROM attention_items WHERE id = $1 AND trainer_id = $2",
        item_id,
        trainer_id,
    )
    if row is None:
        raise AppError("NOT_FOUND", "Элемент внимания не найден", http_status=404)
    await execute(
        "UPDATE attention_items SET is_resolved = TRUE WHERE id = $1",
        item_id,
    )
