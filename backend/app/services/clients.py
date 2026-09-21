from app.core.constants import CLIENT_SORT, CLIENT_STATUSES, FREE_CLIENT_LIMIT
from app.core.exceptions import AppError
from app.core.security import hash_password
from app.db.connection import execute, fetch, fetchrow
from app.db.sql_loader import sql
from app.db.transactions import transaction
from app.schemas.stage import ClientManualIn, MeasurementIn


async def _has_trainer_pro(user_id: int) -> bool:
    row = await fetchrow(
        """
        SELECT id FROM subscriptions
        WHERE user_id = $1 AND audience = 'pro_trainer' AND status = 'active'
          AND ends_at > NOW()
        LIMIT 1
        """,
        user_id,
    )
    return row is not None


async def _assert_client_limit(trainer_id: int) -> None:
    if await _has_trainer_pro(trainer_id):
        return
    row = await fetchrow(
        "SELECT COUNT(*) AS total FROM trainer_clients WHERE trainer_id = $1 AND archived_at IS NULL",
        trainer_id,
    )
    if int(row["total"]) >= FREE_CLIENT_LIMIT:
        raise AppError("TRAINER_PRO_REQUIRED", "Достигнут лимит клиентов. Нужна подписка PRO", http_status=403)


async def list_clients(
    trainer_id: int,
    *,
    q: str | None,
    gender: str | None,
    format_: str | None,
    status: str | None,
    sort: str,
    page: int,
    page_size: int,
    offset: int,
) -> tuple[list[dict], int]:
    order = CLIENT_SORT.get(sort, CLIENT_SORT["newest"])
    args: list = [trainer_id]
    where = ["tc.trainer_id = $1", "tc.archived_at IS NULL"]
    if q:
        args.append(f"%{q.strip()}%")
        where.append(
            f"(u.first_name ILIKE ${len(args)} OR u.last_name ILIKE ${len(args)} OR u.phone ILIKE ${len(args)} OR u.public_id ILIKE ${len(args)})"
        )
    if gender:
        args.append(gender)
        where.append(f"u.gender = ${len(args)}")
    if format_:
        args.append(format_)
        where.append(f"tc.training_format = ${len(args)}")
    if status:
        args.append(status)
        where.append(f"tc.status = ${len(args)}")
    where_sql = " AND ".join(where)
    total = await fetchrow(
        f"""
        SELECT COUNT(*) AS total
        FROM trainer_clients tc
        JOIN users u ON u.id = tc.client_id
        WHERE {where_sql}
        """,
        *args,
    )
    args.extend([page_size, offset])
    rows = await fetch(
        f"""
        SELECT
            tc.id, tc.client_id, tc.status, tc.training_format, tc.created_at,
            u.public_id, u.first_name, u.last_name, u.avatar_url, u.gender
        FROM trainer_clients tc
        JOIN users u ON u.id = tc.client_id
        WHERE {where_sql}
        ORDER BY {order}
        LIMIT ${len(args) - 1} OFFSET ${len(args)}
        """,
        *args,
    )
    return [dict(r) for r in rows], int(total["total"])


async def search_users(trainer_id: int, query: str) -> list[dict]:
    q = query.strip()
    if len(q) < 3:
        raise AppError("VALIDATION_ERROR", "Запрос должен содержать минимум 3 символа", http_status=422)
    rows = await fetch(
        """
        SELECT
            u.id, u.public_id, u.first_name, u.last_name, u.email, u.phone, u.avatar_url,
            EXISTS(
                SELECT 1 FROM trainer_clients tc
                WHERE tc.trainer_id = $2 AND tc.client_id = u.id AND tc.archived_at IS NULL
            ) AS already_added
        FROM users u
        WHERE u.is_shadow = FALSE
          AND (
            lower(u.email) = lower($1)
            OR u.phone = $1
            OR u.public_id = $1
            OR u.phone LIKE '%' || $1
          )
        LIMIT 20
        """,
        q,
        trainer_id,
    )
    return [dict(r) for r in rows]


async def add_existing(trainer_id: int, user_id: int) -> dict:
    target = await fetchrow("SELECT id, is_shadow FROM users WHERE id = $1", user_id)
    if target is None:
        raise AppError("USER_NOT_FOUND", "Пользователь не найден", http_status=404)
    existing = await fetchrow(
        "SELECT id FROM trainer_clients WHERE trainer_id = $1 AND client_id = $2",
        trainer_id,
        user_id,
    )
    if existing:
        raise AppError("ALREADY_ADDED", "Клиент уже добавлен", http_status=409)
    await _assert_client_limit(trainer_id)
    row = await fetchrow(
        """
        INSERT INTO trainer_clients (trainer_id, client_id, invited_via)
        VALUES ($1, $2, 'search')
        RETURNING id
        """,
        trainer_id,
        user_id,
    )
    return await get_client(trainer_id, row["id"])


async def add_manual(trainer_id: int, payload: ClientManualIn) -> dict:
    if not payload.email and not payload.phone:
        raise AppError("VALIDATION_ERROR", "Укажите email или телефон", http_status=422)
    await _assert_client_limit(trainer_id)
    async with transaction() as conn:
        user = await conn.fetchrow(
            sql("auth/insert_user.sql"),
            payload.email,
            payload.phone,
            hash_password("ShadowUser12"),
            payload.first_name.strip(),
            payload.last_name.strip(),
            payload.gender,
            payload.birth_date,
        )
        await conn.execute(
            "UPDATE users SET is_shadow = TRUE WHERE id = $1",
            user["id"],
        )
        await conn.execute(sql("auth/insert_role.sql"), user["id"], "client")
        link = await conn.fetchrow(
            """
            INSERT INTO trainer_clients (trainer_id, client_id, status, training_format, goals, invited_via)
            VALUES ($1, $2, 'new', $3, $4, 'manual')
            RETURNING id
            """,
            trainer_id,
            user["id"],
            payload.training_format,
            payload.goals,
        )
        if payload.measurements:
            await _insert_measurement(conn, user["id"], trainer_id, payload.measurements)
        for note in payload.notes:
            await conn.execute(
                """
                INSERT INTO trainer_notes (trainer_client_id, text, created_by)
                VALUES ($1, $2, $3)
                """,
                link["id"],
                note,
                trainer_id,
            )
        for item in payload.contraindications:
            await conn.execute(
                "INSERT INTO contraindications (trainer_client_id, text) VALUES ($1, $2)",
                link["id"],
                item,
            )
    return await get_client(trainer_id, link["id"])


async def _insert_measurement(conn, client_id: int, recorded_by: int, m: MeasurementIn) -> None:
    await conn.execute(
        """
        INSERT INTO body_measurements (
            client_id, recorded_by, weight_kg, body_fat_pct, muscle_mass_kg, water_pct,
            chest_cm, back_cm, waist_cm, hips_cm, thigh_cm, calf_cm, neck_cm, shoulders_cm, arm_cm, forearm_cm
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
        """,
        client_id,
        recorded_by,
        m.weight_kg,
        m.body_fat_pct,
        m.muscle_mass_kg,
        m.water_pct,
        m.chest_cm,
        m.back_cm,
        m.waist_cm,
        m.hips_cm,
        m.thigh_cm,
        m.calf_cm,
        m.neck_cm,
        m.shoulders_cm,
        m.arm_cm,
        m.forearm_cm,
    )


async def get_client(trainer_id: int, link_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT
            tc.id, tc.client_id, tc.status, tc.training_format, tc.goals, tc.created_at,
            u.public_id, u.first_name, u.last_name, u.email, u.phone, u.avatar_url,
            u.gender, u.birth_date, u.height_cm, u.is_shadow
        FROM trainer_clients tc
        JOIN users u ON u.id = tc.client_id
        WHERE tc.id = $1 AND tc.trainer_id = $2
        """,
        link_id,
        trainer_id,
    )
    if row is None:
        raise AppError("CLIENT_NOT_FOUND", "Клиент не найден", http_status=404)
    notes = await fetch(
        """
        SELECT id, text, created_at FROM trainer_notes
        WHERE trainer_client_id = $1 AND deleted_at IS NULL
        ORDER BY created_at DESC
        """,
        link_id,
    )
    limits = await fetch(
        "SELECT id, text, created_at FROM contraindications WHERE trainer_client_id = $1 ORDER BY id",
        link_id,
    )
    last_m = await fetchrow(
        """
        SELECT * FROM body_measurements
        WHERE client_id = $1
        ORDER BY recorded_at DESC
        LIMIT 1
        """,
        row["client_id"],
    )
    data = dict(row)
    data["notes"] = [dict(n) for n in notes]
    data["contraindications"] = [dict(x) for x in limits]
    data["last_measurement"] = dict(last_m) if last_m else None
    return data


async def patch_client(trainer_id: int, link_id: int, status: str | None, goals, format_) -> dict:
    await get_client(trainer_id, link_id)
    if status and status not in CLIENT_STATUSES:
        raise AppError("VALIDATION_ERROR", "Некорректный статус", http_status=422)
    await execute(
        """
        UPDATE trainer_clients
        SET status = COALESCE($3, status),
            goals = COALESCE($4, goals),
            training_format = COALESCE($5, training_format)
        WHERE id = $1 AND trainer_id = $2
        """,
        link_id,
        trainer_id,
        status,
        goals,
        format_,
    )
    return await get_client(trainer_id, link_id)


async def archive_client(trainer_id: int, link_id: int) -> None:
    await get_client(trainer_id, link_id)
    await execute(
        "UPDATE trainer_clients SET archived_at = NOW(), status = 'archived' WHERE id = $1 AND trainer_id = $2",
        link_id,
        trainer_id,
    )


async def add_measurement(trainer_id: int, link_id: int, payload: MeasurementIn) -> dict:
    card = await get_client(trainer_id, link_id)
    await execute(
        """
        INSERT INTO body_measurements (
            client_id, recorded_by, weight_kg, body_fat_pct, muscle_mass_kg, water_pct,
            chest_cm, back_cm, waist_cm, hips_cm, thigh_cm, calf_cm, neck_cm, shoulders_cm, arm_cm, forearm_cm
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)
        """,
        card["client_id"],
        trainer_id,
        payload.weight_kg,
        payload.body_fat_pct,
        payload.muscle_mass_kg,
        payload.water_pct,
        payload.chest_cm,
        payload.back_cm,
        payload.waist_cm,
        payload.hips_cm,
        payload.thigh_cm,
        payload.calf_cm,
        payload.neck_cm,
        payload.shoulders_cm,
        payload.arm_cm,
        payload.forearm_cm,
    )
    return await get_client(trainer_id, link_id)


async def add_note(trainer_id: int, link_id: int, text: str) -> dict:
    await get_client(trainer_id, link_id)
    row = await fetchrow(
        """
        INSERT INTO trainer_notes (trainer_client_id, text, created_by)
        VALUES ($1, $2, $3)
        RETURNING id, text, created_at
        """,
        link_id,
        text,
        trainer_id,
    )
    return dict(row)


async def delete_note(trainer_id: int, link_id: int, note_id: int) -> None:
    await get_client(trainer_id, link_id)
    await execute(
        "UPDATE trainer_notes SET deleted_at = NOW() WHERE id = $1 AND trainer_client_id = $2",
        note_id,
        link_id,
    )


async def admin_list(q: str | None, page_size: int, offset: int) -> tuple[list[dict], int]:
    args: list = []
    where = ["tc.archived_at IS NULL"]
    if q:
        args.append(f"%{q}%")
        where.append(f"(c.first_name ILIKE ${len(args)} OR t.first_name ILIKE ${len(args)})")
    where_sql = " AND ".join(where)
    total = await fetchrow(
        f"""
        SELECT COUNT(*) AS total
        FROM trainer_clients tc
        JOIN users c ON c.id = tc.client_id
        JOIN users t ON t.id = tc.trainer_id
        WHERE {where_sql}
        """,
        *args,
    )
    args.extend([page_size, offset])
    rows = await fetch(
        f"""
        SELECT tc.id, tc.status, tc.created_at,
               c.id AS client_id, c.first_name AS client_first, c.last_name AS client_last,
               t.id AS trainer_id, t.first_name AS trainer_first, t.last_name AS trainer_last
        FROM trainer_clients tc
        JOIN users c ON c.id = tc.client_id
        JOIN users t ON t.id = tc.trainer_id
        WHERE {where_sql}
        ORDER BY tc.created_at DESC
        LIMIT ${len(args) - 1} OFFSET ${len(args)}
        """,
        *args,
    )
    return [dict(r) for r in rows], int(total["total"])


async def admin_get(link_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT
            tc.id, tc.status, tc.training_format, tc.goals, tc.invited_via, tc.created_at, tc.archived_at,
            c.id AS client_id, c.public_id, c.first_name AS client_first, c.last_name AS client_last,
            c.email AS client_email, c.phone AS client_phone, c.gender, c.birth_date, c.height_cm, c.is_shadow,
            t.id AS trainer_id, t.first_name AS trainer_first, t.last_name AS trainer_last, t.email AS trainer_email
        FROM trainer_clients tc
        JOIN users c ON c.id = tc.client_id
        JOIN users t ON t.id = tc.trainer_id
        WHERE tc.id = $1
        """,
        link_id,
    )
    if row is None:
        raise AppError("CLIENT_NOT_FOUND", "Клиент не найден", http_status=404)
    notes = await fetch(
        """
        SELECT id, text, created_at FROM trainer_notes
        WHERE trainer_client_id = $1 AND deleted_at IS NULL
        ORDER BY created_at DESC
        """,
        link_id,
    )
    limits = await fetch(
        "SELECT id, text, created_at FROM contraindications WHERE trainer_client_id = $1 ORDER BY id",
        link_id,
    )
    last_m = await fetchrow(
        """
        SELECT * FROM body_measurements
        WHERE client_id = $1
        ORDER BY recorded_at DESC
        LIMIT 1
        """,
        row["client_id"],
    )
    data = dict(row)
    data["notes"] = [dict(n) for n in notes]
    data["contraindications"] = [dict(x) for x in limits]
    data["last_measurement"] = dict(last_m) if last_m else None
    return data
