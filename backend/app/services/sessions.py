from datetime import UTC, datetime

from app.core.constants import SESSION_SORT
from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow
from app.db.transactions import transaction
from app.schemas.stage import SessionCreateIn, SetIn


async def create_session(actor_id: int, is_trainer: bool, payload: SessionCreateIn) -> dict:
    if is_trainer:
        trainer_id = actor_id
        lead = payload.client_ids[0] if payload.client_ids else None
        clients = payload.client_ids
    else:
        trainer_id = None
        lead = actor_id
        clients = [actor_id]
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
        linked = await fetchrow(
            """
            SELECT 1 FROM trainer_clients tc
            WHERE tc.trainer_id = $1 AND tc.archived_at IS NULL
              AND (
                  tc.client_id = $2
                  OR EXISTS (
                      SELECT 1 FROM workout_session_clients c
                      WHERE c.session_id = $3 AND c.client_id = tc.client_id
                  )
              )
            """,
            actor_id,
            row["lead_client_id"],
            session_id,
        )
        if linked is None:
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
    if data.get("trainer_id"):
        trainer = await fetchrow(
            "SELECT first_name, last_name FROM users WHERE id = $1",
            data["trainer_id"],
        )
        if trainer:
            data["trainer_name"] = f"{trainer['first_name']} {trainer['last_name']}".strip()
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


async def previous_sets(
    session_id: int,
    exercise_id: int,
    actor_id: int,
    is_trainer: bool,
    client_id: int | None = None,
) -> list[dict]:
    session = await get_session(session_id, actor_id, is_trainer)
    target = actor_id if not is_trainer else (client_id or session.get("lead_client_id") or actor_id)
    if is_trainer and target != actor_id:
        linked = await fetchrow(
            """
            SELECT 1 FROM trainer_clients
            WHERE trainer_id = $1 AND client_id = $2 AND archived_at IS NULL
            UNION
            SELECT 1 FROM workout_session_clients WHERE session_id = $3 AND client_id = $2
            UNION
            SELECT 1 FROM workout_sessions WHERE id = $3 AND lead_client_id = $2
            """,
            actor_id,
            target,
            session_id,
        )
        if linked is None:
            raise AppError("FORBIDDEN", "Нет доступа к результатам клиента", http_status=403)
    rows = await fetch(
        """
        WITH last AS (
            SELECT ws.id
            FROM workout_sessions ws
            JOIN session_exercises se ON se.session_id = ws.id
            WHERE se.exercise_id = $1
              AND ws.status = 'completed'
              AND ws.id <> $2
              AND (
                  ws.lead_client_id = $3
                  OR EXISTS (
                      SELECT 1 FROM workout_session_clients c
                      WHERE c.session_id = ws.id AND c.client_id = $3
                  )
              )
            ORDER BY ws.finished_at DESC NULLS LAST
            LIMIT 1
        )
        SELECT ss.weight_kg, ss.reps, ss.set_index, ss.is_warmup, ws.finished_at
        FROM last
        JOIN workout_sessions ws ON ws.id = last.id
        JOIN session_exercises se ON se.session_id = last.id AND se.exercise_id = $1
        JOIN session_sets ss ON ss.session_exercise_id = se.id
        ORDER BY ss.set_index, ss.id
        """,
        exercise_id,
        session_id,
        target,
    )
    return [dict(r) for r in rows]


async def patch_set(session_id: int, set_id: int, actor_id: int, is_trainer: bool, payload: SetIn) -> dict:
    await get_session(session_id, actor_id, is_trainer)
    row = await fetchrow(
        """
        UPDATE session_sets ss
        SET weight_kg = COALESCE($3, ss.weight_kg),
            reps = COALESCE($4, ss.reps),
            is_warmup = $5
        FROM session_exercises se
        WHERE ss.id = $1
          AND se.id = ss.session_exercise_id
          AND se.session_id = $2
        RETURNING ss.id
        """,
        set_id,
        session_id,
        payload.weight_kg,
        payload.reps,
        payload.is_warmup,
    )
    if row is None:
        raise AppError("NOT_FOUND", "Подход не найден", http_status=404)
    return await get_session(session_id, actor_id, is_trainer)


async def strength_progress(client_id: int) -> list[dict]:
    last_rows = await fetch(
        """
        SELECT DISTINCT ON (se.exercise_id)
            se.exercise_id,
            e.name,
            ss.weight_kg AS last_weight_kg,
            ss.reps AS last_reps,
            ws.finished_at AS last_session_at
        FROM workout_sessions ws
        JOIN session_exercises se ON se.session_id = ws.id
        JOIN session_sets ss ON ss.session_exercise_id = se.id
        JOIN exercises e ON e.id = se.exercise_id
        WHERE ws.status = 'completed'
          AND ss.is_warmup = FALSE
          AND (
              ws.lead_client_id = $1
              OR EXISTS (
                  SELECT 1 FROM workout_session_clients c
                  WHERE c.session_id = ws.id AND c.client_id = $1
              )
          )
        ORDER BY se.exercise_id, ws.finished_at DESC NULLS LAST, ss.set_index DESC, ss.id DESC
        """,
        client_id,
    )
    best_rows = await fetch(
        """
        SELECT
            se.exercise_id,
            MAX(ss.weight_kg) FILTER (WHERE ss.is_warmup = FALSE) AS best_weight_kg,
            COUNT(DISTINCT ws.id) AS sessions_count
        FROM workout_sessions ws
        JOIN session_exercises se ON se.session_id = ws.id
        JOIN session_sets ss ON ss.session_exercise_id = se.id
        WHERE ws.status = 'completed'
          AND (
              ws.lead_client_id = $1
              OR EXISTS (
                  SELECT 1 FROM workout_session_clients c
                  WHERE c.session_id = ws.id AND c.client_id = $1
              )
          )
        GROUP BY se.exercise_id
        """,
        client_id,
    )
    best = {int(r["exercise_id"]): dict(r) for r in best_rows}
    items = []
    for row in last_rows:
        extra = best.get(int(row["exercise_id"]), {})
        items.append(
            {
                "exercise_id": row["exercise_id"],
                "name": row["name"],
                "last_weight_kg": row["last_weight_kg"],
                "last_reps": row["last_reps"],
                "last_session_at": row["last_session_at"],
                "best_weight_kg": extra.get("best_weight_kg"),
                "sessions_count": int(extra.get("sessions_count") or 0),
            }
        )
    items.sort(
        key=lambda item: item["last_session_at"] or datetime.min.replace(tzinfo=UTC),
        reverse=True,
    )
    return items


async def client_sessions(
    client_id: int,
    *,
    kind: str | None,
    format_: str | None,
    with_trainer: bool | None,
    sort: str,
    page_size: int,
    offset: int,
    q: str | None = None,
    date_from=None,
    date_to=None,
    duration_min: int | None = None,
    duration_max: int | None = None,
    with_records: bool | None = None,
    muscle: str | None = None,
) -> tuple[list[dict], int]:
    order = SESSION_SORT.get(sort, SESSION_SORT["newest"])
    args: list = [client_id]
    where = ["(s.lead_client_id = $1 OR EXISTS (SELECT 1 FROM workout_session_clients c WHERE c.session_id = s.id AND c.client_id = $1))"]
    if kind:
        args.append(kind)
        where.append(f"${len(args)} = ANY(s.kinds)")
    if muscle:
        args.append(muscle)
        where.append(
            f"""EXISTS (
                SELECT 1 FROM session_exercises se
                JOIN exercises e ON e.id = se.exercise_id
                WHERE se.session_id = s.id
                  AND (e.primary_muscle = ${len(args)} OR ${len(args)} = ANY(e.secondary_muscles))
            )"""
        )
    if with_trainer is True:
        where.append("s.trainer_id IS NOT NULL")
    if with_trainer is False:
        where.append("s.trainer_id IS NULL")
    if date_from:
        args.append(date_from)
        where.append(f"COALESCE(s.finished_at, s.started_at, s.created_at) >= ${len(args)}")
    if date_to:
        args.append(date_to)
        where.append(f"COALESCE(s.finished_at, s.started_at, s.created_at) < ${len(args)}")
    if duration_min is not None:
        args.append(duration_min * 60)
        where.append(f"s.duration_sec >= ${len(args)}")
    if duration_max is not None:
        args.append(duration_max * 60)
        where.append(f"s.duration_sec <= ${len(args)}")
    if q:
        args.append(f"%{q.strip()}%")
        where.append(
            f"""(
                EXISTS (
                    SELECT 1 FROM session_exercises se
                    JOIN exercises e ON e.id = se.exercise_id
                    WHERE se.session_id = s.id AND e.name ILIKE ${len(args)}
                )
                OR EXISTS (SELECT 1 FROM unnest(s.kinds) k WHERE k ILIKE ${len(args)})
            )"""
        )
    if with_records:
        where.append(
            """EXISTS (
                SELECT 1 FROM session_sets ss
                JOIN session_exercises se ON se.id = ss.session_exercise_id
                WHERE se.session_id = s.id AND ss.weight_kg IS NOT NULL
                  AND ss.weight_kg >= COALESCE((
                      SELECT MAX(ss2.weight_kg)
                      FROM session_sets ss2
                      JOIN session_exercises se2 ON se2.id = ss2.session_exercise_id
                      JOIN workout_sessions ws2 ON ws2.id = se2.session_id
                      WHERE se2.exercise_id = se.exercise_id
                        AND ws2.status = 'completed'
                        AND (ws2.lead_client_id = $1 OR EXISTS (
                            SELECT 1 FROM workout_session_clients c2
                            WHERE c2.session_id = ws2.id AND c2.client_id = $1
                        ))
                  ), 0)
            )"""
        )
    _ = format_
    where_sql = " AND ".join(where)
    total = await fetchrow(
        f"SELECT COUNT(*) AS total FROM workout_sessions s WHERE {where_sql}",
        *args,
    )
    args.extend([page_size, offset])
    rows = await fetch(
        f"""
        SELECT
            s.id, s.source, s.kinds, s.status, s.started_at, s.finished_at, s.duration_sec, s.calories,
            s.trainer_id,
            t.first_name AS trainer_first, t.last_name AS trainer_last,
            (
                SELECT COUNT(*) FROM session_sets ss
                JOIN session_exercises se ON se.id = ss.session_exercise_id
                WHERE se.session_id = s.id
            ) AS sets_count
        FROM workout_sessions s
        LEFT JOIN users t ON t.id = s.trainer_id
        WHERE {where_sql}
        ORDER BY {order}
        LIMIT ${len(args) - 1} OFFSET ${len(args)}
        """,
        *args,
    )
    items = []
    for row in rows:
        item = dict(row)
        item["trainer_name"] = " ".join(
            part for part in [item.pop("trainer_first", None), item.pop("trainer_last", None)] if part
        ) or None
        items.append(item)
    return items, int(total["total"])
