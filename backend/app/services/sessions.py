from app.core.constants import SESSION_SORT
from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow
from app.db.transactions import transaction
from app.schemas.stage import SessionCreateIn, SetIn


async def create_session(actor_id: int, is_trainer: bool, payload: SessionCreateIn) -> dict:
    trainer_id = actor_id if is_trainer else None
    lead = payload.client_ids[0] if payload.client_ids else (None if is_trainer else actor_id)
    async with transaction() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO workout_sessions (
                trainer_id, lead_client_id, source, kinds, program_day_id, calendar_event_id, status, started_at
            ) VALUES ($1,$2,$3,$4,$5,$6,'in_progress', NOW())
            RETURNING id
            """,
            trainer_id,
            lead,
            payload.source,
            payload.kinds,
            payload.program_day_id,
            payload.calendar_event_id,
        )
        clients = payload.client_ids or ([actor_id] if not is_trainer else [])
        for client_id in clients:
            await conn.execute(
                "INSERT INTO workout_session_clients (session_id, client_id) VALUES ($1,$2) ON CONFLICT DO NOTHING",
                row["id"],
                client_id,
            )
        if payload.calendar_event_id:
            await conn.execute(
                "UPDATE calendar_events SET session_id = $1, status = 'in_progress' WHERE id = $2",
                row["id"],
                payload.calendar_event_id,
            )
    return await get_session(row["id"], actor_id, is_trainer)


async def get_session(session_id: int, actor_id: int, is_trainer: bool) -> dict:
    row = await fetchrow("SELECT * FROM workout_sessions WHERE id = $1", session_id)
    if row is None:
        raise AppError("SESSION_NOT_FOUND", "Тренировка не найдена", http_status=404)
    if is_trainer and row["trainer_id"] != actor_id:
        raise AppError("FORBIDDEN", "Это не ваша тренировка", http_status=403)
    if not is_trainer:
        member = await fetchrow(
            """
            SELECT 1 FROM workout_session_clients WHERE session_id = $1 AND client_id = $2
            UNION
            SELECT 1 FROM workout_sessions WHERE id = $1 AND lead_client_id = $2
            """,
            session_id,
            actor_id,
        )
        if member is None:
            raise AppError("FORBIDDEN", "Это не ваша тренировка", http_status=403)
    exercises = await fetch(
        """
        SELECT se.id, se.exercise_id, se.sort_order, se.rest_sec, se.status, e.name
        FROM session_exercises se
        JOIN exercises e ON e.id = se.exercise_id
        WHERE se.session_id = $1
        ORDER BY se.sort_order, se.id
        """,
        session_id,
    )
    data = dict(row)
    items = []
    for ex in exercises:
        sets = await fetch(
            """
            SELECT id, set_index, weight_kg, reps, is_warmup, completed_at
            FROM session_sets WHERE session_exercise_id = $1
            ORDER BY set_index, id
            """,
            ex["id"],
        )
        item = dict(ex)
        item["sets"] = [dict(s) for s in sets]
        items.append(item)
    data["exercises"] = items
    return data


async def add_exercise(session_id: int, actor_id: int, is_trainer: bool, exercise_id: int, rest_sec: int | None) -> dict:
    await get_session(session_id, actor_id, is_trainer)
    row = await fetchrow(
        """
        INSERT INTO session_exercises (session_id, exercise_id, sort_order, rest_sec)
        VALUES ($1, $2, COALESCE((SELECT MAX(sort_order)+1 FROM session_exercises WHERE session_id = $1), 1), $3)
        RETURNING id
        """,
        session_id,
        exercise_id,
        rest_sec,
    )
    return await get_session(session_id, actor_id, is_trainer) | {"added_exercise_id": row["id"]}


async def add_set(session_id: int, se_id: int, actor_id: int, is_trainer: bool, payload: SetIn) -> dict:
    await get_session(session_id, actor_id, is_trainer)
    await fetchrow(
        """
        INSERT INTO session_sets (session_exercise_id, set_index, weight_kg, reps, is_warmup)
        VALUES (
            $1,
            COALESCE((SELECT MAX(set_index)+1 FROM session_sets WHERE session_exercise_id = $1), 1),
            $2, $3, $4
        )
        RETURNING id
        """,
        se_id,
        payload.weight_kg,
        payload.reps,
        payload.is_warmup,
    )
    return await get_session(session_id, actor_id, is_trainer)


async def complete_session(session_id: int, actor_id: int, is_trainer: bool) -> dict:
    session = await get_session(session_id, actor_id, is_trainer)
    done = sum(1 for e in session["exercises"] if e["sets"])
    total = len(session["exercises"])
    await execute(
        """
        UPDATE workout_sessions
        SET status = 'completed',
            finished_at = NOW(),
            duration_sec = EXTRACT(EPOCH FROM (NOW() - COALESCE(started_at, created_at)))::INT
        WHERE id = $1
        """,
        session_id,
    )
    if session.get("calendar_event_id"):
        await execute(
            "UPDATE calendar_events SET status = 'completed' WHERE id = $1",
            session["calendar_event_id"],
        )
    result = await get_session(session_id, actor_id, is_trainer)
    result["summary"] = {
        "exercises_done": done,
        "exercises_total": total,
        "duration_sec": result["duration_sec"],
        "calories": result["calories"],
    }
    return result


async def previous_sets(session_id: int, exercise_id: int, client_id: int) -> list[dict]:
    rows = await fetch(
        """
        SELECT ss.weight_kg, ss.reps, ss.set_index, ws.finished_at
        FROM session_sets ss
        JOIN session_exercises se ON se.id = ss.session_exercise_id
        JOIN workout_sessions ws ON ws.id = se.session_id
        WHERE se.exercise_id = $1
          AND ws.status = 'completed'
          AND ws.id <> $2
          AND (ws.lead_client_id = $3 OR EXISTS (
              SELECT 1 FROM workout_session_clients c WHERE c.session_id = ws.id AND c.client_id = $3
          ))
        ORDER BY ws.finished_at DESC, ss.set_index
        LIMIT 20
        """,
        exercise_id,
        session_id,
        client_id,
    )
    return [dict(r) for r in rows]


async def client_sessions(
    client_id: int,
    *,
    kind: str | None,
    format_: str | None,
    with_trainer: bool | None,
    sort: str,
    page_size: int,
    offset: int,
) -> tuple[list[dict], int]:
    order = SESSION_SORT.get(sort, SESSION_SORT["newest"])
    args: list = [client_id]
    where = ["(s.lead_client_id = $1 OR EXISTS (SELECT 1 FROM workout_session_clients c WHERE c.session_id = s.id AND c.client_id = $1))"]
    if kind:
        args.append(kind)
        where.append(f"${len(args)} = ANY(s.kinds)")
    if with_trainer is True:
        where.append("s.trainer_id IS NOT NULL")
    if with_trainer is False:
        where.append("s.trainer_id IS NULL")
    where_sql = " AND ".join(where)
    total = await fetchrow(
        f"SELECT COUNT(*) AS total FROM workout_sessions s WHERE {where_sql}",
        *args,
    )
    args.extend([page_size, offset])
    rows = await fetch(
        f"""
        SELECT s.id, s.source, s.kinds, s.status, s.started_at, s.finished_at, s.duration_sec, s.calories
        FROM workout_sessions s
        WHERE {where_sql}
        ORDER BY {order}
        LIMIT ${len(args) - 1} OFFSET ${len(args)}
        """,
        *args,
    )
    return [dict(r) for r in rows], int(total["total"])
