from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow


async def list_users(q: str | None, role: str | None, page_size: int, offset: int) -> tuple[list[dict], int]:
    args: list = []
    where = ["TRUE"]
    if q:
        args.append(f"%{q}%")
        where.append(
            f"(u.email ILIKE ${len(args)} OR u.first_name ILIKE ${len(args)} OR u.last_name ILIKE ${len(args)} OR u.public_id ILIKE ${len(args)})"
        )
    if role:
        args.append(role)
        where.append(f"EXISTS (SELECT 1 FROM user_roles r WHERE r.user_id = u.id AND r.role = ${len(args)})")
    where_sql = " AND ".join(where)
    total = await fetchrow(f"SELECT COUNT(*) AS total FROM users u WHERE {where_sql}", *args)
    args.extend([page_size, offset])
    rows = await fetch(
        f"""
        SELECT
            u.id, u.public_id, u.email, u.phone, u.first_name, u.last_name,
            u.is_blocked, u.is_shadow, u.created_at,
            COALESCE(array_agg(ur.role) FILTER (WHERE ur.role IS NOT NULL), ARRAY[]::text[]) AS roles
        FROM users u
        LEFT JOIN user_roles ur ON ur.user_id = u.id
        WHERE {where_sql}
        GROUP BY u.id
        ORDER BY u.created_at DESC
        LIMIT ${len(args) - 1} OFFSET ${len(args)}
        """,
        *args,
    )
    return [dict(r) for r in rows], int(total["total"])


async def block_user(user_id: int, is_blocked: bool, reason: str | None) -> dict:
    row = await fetchrow(
        """
        UPDATE users
        SET is_blocked = $2, blocked_reason = $3, updated_at = NOW()
        WHERE id = $1
        RETURNING id, is_blocked, blocked_reason
        """,
        user_id,
        is_blocked,
        reason,
    )
    if row is None:
        raise AppError("USER_NOT_FOUND", "Пользователь не найден", http_status=404)
    return dict(row)


async def get_user(user_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT
            u.id, u.public_id, u.email, u.phone, u.first_name, u.last_name,
            u.avatar_url, u.gender, u.birth_date, u.height_cm, u.is_shadow,
            u.is_active, u.is_blocked, u.blocked_reason, u.created_at, u.last_login_at,
            COALESCE(array_agg(ur.role) FILTER (WHERE ur.role IS NOT NULL), ARRAY[]::text[]) AS roles
        FROM users u
        LEFT JOIN user_roles ur ON ur.user_id = u.id
        WHERE u.id = $1
        GROUP BY u.id
        """,
        user_id,
    )
    if row is None:
        raise AppError("USER_NOT_FOUND", "Пользователь не найден", http_status=404)
    data = dict(row)
    profile = await fetchrow(
        """
        SELECT bio, experience_years, specializations, work_formats, session_price_amount,
               session_duration_min, free_first_consult, category, rating_avg, reviews_count, is_verified
        FROM trainer_profiles WHERE user_id = $1
        """,
        user_id,
    )
    subscription = await fetchrow(
        """
        SELECT s.id, s.audience, s.status, s.starts_at, s.ends_at, s.auto_renew, p.code
        FROM subscriptions s
        JOIN subscription_plans p ON p.id = s.plan_id
        WHERE s.user_id = $1
        ORDER BY s.created_at DESC
        LIMIT 1
        """,
        user_id,
    )
    clients = await fetchrow(
        "SELECT COUNT(*) AS total FROM trainer_clients WHERE trainer_id = $1 AND archived_at IS NULL",
        user_id,
    )
    data["trainer_profile"] = dict(profile) if profile else None
    data["subscription"] = dict(subscription) if subscription else None
    data["clients_count"] = int(clients["total"]) if clients else 0
    return data


async def set_trainer_verified(user_id: int, is_verified: bool) -> dict:
    user = await get_user(user_id)
    if "trainer" not in (user.get("roles") or []):
        raise AppError("VALIDATION_ERROR", "Пользователь не является тренером", http_status=422)
    await execute(
        """
        INSERT INTO trainer_profiles (user_id, is_verified)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO UPDATE SET is_verified = EXCLUDED.is_verified, updated_at = NOW()
        """,
        user_id,
        is_verified,
    )
    return await get_user(user_id)


async def dashboard() -> dict:
    row = await fetchrow(
        """
        SELECT
            (SELECT COUNT(*) FROM users) AS users,
            (SELECT COUNT(*) FROM user_roles WHERE role = 'trainer') AS trainers,
            (SELECT COUNT(*) FROM user_roles WHERE role = 'client') AS clients,
            (SELECT COUNT(*) FROM workout_sessions WHERE status = 'in_progress') AS active_sessions,
            (SELECT COUNT(*) FROM subscriptions WHERE status = 'active' AND ends_at > NOW()) AS active_subscriptions
        """
    )
    return dict(row)
