from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow
from app.db.transactions import transaction


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


async def list_marketplace(category: str | None, page: int, page_size: int, offset: int) -> tuple[list[dict], int]:
    args: list = []
    where = ["ur.role = 'trainer'", "u.is_blocked = FALSE"]
    if category and category != "all":
        args.append(category)
        where.append(f"tp.category = ${len(args)}")
    where_sql = " AND ".join(where)
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
            ) AS programs_count
        FROM users u
        JOIN user_roles ur ON ur.user_id = u.id
        LEFT JOIN trainer_profiles tp ON tp.user_id = u.id
        WHERE {where_sql}
        ORDER BY COALESCE(tp.rating_avg, 0) DESC, u.id DESC
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


async def reports(trainer_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT
            COUNT(*) FILTER (WHERE status = 'completed') AS sessions_count,
            COALESCE(SUM(calories) FILTER (WHERE status = 'completed'), 0) AS calories_total
        FROM workout_sessions
        WHERE trainer_id = $1
          AND COALESCE(finished_at, created_at) >= date_trunc('month', NOW())
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
    return {
        "sessions_count": int(row["sessions_count"]),
        "calories_total": int(row["calories_total"]),
        "gender": dict(gender),
    }


async def attention_list(trainer_id: int) -> list[dict]:
    rows = await fetch(
        """
        SELECT a.id, a.reason, a.created_at, a.is_resolved,
               u.id AS client_id, u.first_name, u.last_name, u.phone
        FROM attention_items a
        JOIN users u ON u.id = a.client_id
        WHERE a.trainer_id = $1 AND a.is_resolved = FALSE
        ORDER BY a.created_at DESC
        """,
        trainer_id,
    )
    return [dict(r) for r in rows]


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
