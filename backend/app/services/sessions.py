from datetime import UTC, datetime, timedelta

from app.core.constants import SESSION_SORT
from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow
from app.db.transactions import transaction
from app.schemas.stage import SessionCreateIn, SetIn

# No taps / mutations for this long → session is abandoned (incomplete).
SESSION_INACTIVITY = timedelta(hours=1)


async def _touch_activity(session_id: int) -> None:
    await execute(
        """
        UPDATE workout_sessions
        SET last_activity_at = NOW()
        WHERE id = $1 AND status = 'in_progress'
        """,
        session_id,
    )


def _active_duration_sql(alias: str = "") -> str:
    """Wall time minus completed pauses and the current open pause (if any)."""
    p = f"{alias}." if alias else ""
    return (
        f"GREATEST(0, EXTRACT(EPOCH FROM (COALESCE({p}finished_at, NOW()) - COALESCE({p}started_at, {p}created_at)))::INT"
        f" - COALESCE({p}pause_sec, 0)"
        f" - CASE WHEN {p}paused_at IS NOT NULL"
        f" THEN EXTRACT(EPOCH FROM (COALESCE({p}finished_at, NOW()) - {p}paused_at))::INT ELSE 0 END)"
    )


async def abandon_session(session_id: int, *, reason: str = "inactivity") -> dict | None:
    row = await fetchrow(
        f"""
        UPDATE workout_sessions
        SET status = 'abandoned',
            finished_at = NOW(),
            paused_at = NULL,
            duration_sec = {_active_duration_sql()},
            notes = CASE
                WHEN notes IS NULL OR notes = '' THEN $2
                ELSE notes || E'\\n' || $2
            END
        WHERE id = $1 AND status = 'in_progress'
        RETURNING id, lead_client_id, calendar_event_id
        """,
        session_id,
        f"abandoned:{reason}",
    )
    if row is None:
        return None
    if row.get("calendar_event_id"):
        await execute(
            "UPDATE calendar_events SET status = 'cancelled' WHERE id = $1 AND status = 'in_progress'",
            row["calendar_event_id"],
        )
    return dict(row)


async def pause_session(session_id: int, actor_id: int, is_trainer: bool) -> dict:
    await get_session(session_id, actor_id, is_trainer)
    row = await fetchrow(
        """
        UPDATE workout_sessions
        SET paused_at = COALESCE(paused_at, NOW()),
            last_activity_at = NOW()
        WHERE id = $1 AND status = 'in_progress'
        RETURNING id
        """,
        session_id,
    )
    if row is None:
        raise AppError("SESSION_NOT_ACTIVE", "Тренировка не активна", http_status=409)
    return await get_session(session_id, actor_id, is_trainer)


async def resume_session(session_id: int, actor_id: int, is_trainer: bool) -> dict:
    await get_session(session_id, actor_id, is_trainer)
    row = await fetchrow(
        """
        UPDATE workout_sessions
        SET pause_sec = COALESCE(pause_sec, 0)
              + CASE
                  WHEN paused_at IS NULL THEN 0
                  ELSE GREATEST(0, EXTRACT(EPOCH FROM (NOW() - paused_at))::INT)
                END,
            paused_at = NULL,
            last_activity_at = NOW()
        WHERE id = $1 AND status = 'in_progress'
        RETURNING id
        """,
        session_id,
    )
    if row is None:
        raise AppError("SESSION_NOT_ACTIVE", "Тренировка не активна", http_status=409)
    return await get_session(session_id, actor_id, is_trainer)


async def abandon_stale_sessions(*, older_than: timedelta | None = None) -> int:
    """Mark in_progress sessions with no activity as abandoned.

    Paused sessions are kept — user may resume later without the 1h abandon clock.
    """
    cutoff = older_than or SESSION_INACTIVITY
    rows = await fetch(
        """
        SELECT id
        FROM workout_sessions
        WHERE status = 'in_progress'
          AND paused_at IS NULL
          AND COALESCE(last_activity_at, started_at, created_at) < NOW() - $1::interval
        """,
        cutoff,
    )
    count = 0
    for row in rows:
        if await abandon_session(int(row["id"]), reason="inactivity_1h"):
            count += 1
    return count


async def find_active_session_for_user(user_id: int) -> dict | None:
    """Return active in_progress session for user, auto-abandoning stale ones."""
    await abandon_stale_sessions()
    row = await fetchrow(
        """
        SELECT id, trainer_id
        FROM workout_sessions
        WHERE status = 'in_progress'
          AND (
              trainer_id = $1
              OR lead_client_id = $1
              OR EXISTS (
                  SELECT 1 FROM workout_session_clients c
                  WHERE c.session_id = workout_sessions.id AND c.client_id = $1
              )
          )
        ORDER BY COALESCE(last_activity_at, started_at, created_at) DESC
        LIMIT 1
        """,
        user_id,
    )
    if row is None:
        return None
    is_trainer = row.get("trainer_id") == user_id
    return await get_session(int(row["id"]), user_id, bool(is_trainer))


async def create_session(actor_id: int, is_trainer: bool, payload: SessionCreateIn) -> dict:
    if is_trainer:
        trainer_id = actor_id
        lead = payload.client_ids[0] if payload.client_ids else None
        clients = payload.client_ids
    else:
        trainer_id = None
        lead = actor_id
        clients = [actor_id]

    # Block new workout if actor / participants still have an unfinished one
    # (includes trainer solo sessions with no clients).
    owners = {actor_id}
    if lead is not None:
        owners.add(lead)
    owners.update(clients or [])
    owners.discard(None)
    for owner_id in owners:
        active = await find_active_session_for_user(int(owner_id))
        if active is not None:
            raise AppError(
                "ACTIVE_SESSION_EXISTS",
                "Есть незавершённая тренировка — продолжите её или завершите",
                http_status=409,
                details={"session_id": active.get("id"), "status": active.get("status")},
            )

    program_day_id = payload.program_day_id
    if program_day_id is not None:
        day = await fetchrow(
            """
            SELECT pd.id, pd.program_id, p.status, p.is_pro, p.author_id
            FROM program_days pd
            JOIN programs p ON p.id = pd.program_id
            WHERE pd.id = $1
            """,
            program_day_id,
        )
        if day is None:
            raise AppError("PROGRAM_DAY_NOT_FOUND", "День программы не найден", http_status=404)
        if day["status"] != "published" and day["author_id"] != actor_id:
            assigned = await fetchrow(
                """
                SELECT 1 FROM client_program_assignments
                WHERE program_id = $1 AND client_id = $2 AND status = 'active'
                """,
                day["program_id"],
                lead or actor_id,
            )
            if assigned is None:
                raise AppError("FORBIDDEN", "Программа недоступна", http_status=403)
        if day["is_pro"] and day["author_id"] != actor_id:
            has_pro = await fetchrow(
                """
                SELECT id FROM subscriptions
                WHERE user_id = $1 AND status = 'active' AND ends_at > NOW()
                LIMIT 1
                """,
                actor_id,
            )
            # Preview days on week 1 may still start; lock is enforced on later weeks in catalog.
            # Allow start; locked content remains empty if caller picked a locked day.
            if has_pro is None:
                week = await fetchrow(
                    """
                    SELECT pw.week_index, pw.is_preview
                    FROM program_days pd
                    LEFT JOIN program_weeks pw ON pw.id = pd.week_id
                    WHERE pd.id = $1
                    """,
                    program_day_id,
                )
                week_index = int(week["week_index"] or 1) if week and week.get("week_index") is not None else 1
                is_preview = bool(week["is_preview"]) if week else False
                if not is_preview and week_index > 1:
                    raise AppError("PRO_REQUIRED", "Для этой тренировки нужна подписка Pro", http_status=403)

    async with transaction() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO workout_sessions (
                trainer_id, lead_client_id, source, kinds, program_day_id, calendar_event_id,
                status, started_at, last_activity_at
            ) VALUES ($1,$2,$3,$4,$5,$6,'in_progress', NOW(), NOW())
            RETURNING id
            """,
            trainer_id,
            lead,
            payload.source if not program_day_id else (payload.source or "program"),
            payload.kinds,
            program_day_id,
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
        # Seed session exercises from program day (reuse exercise ids, no duplicates of catalog).
        if program_day_id is not None:
            day_ex = await conn.fetch(
                """
                SELECT exercise_id, sort_order, sets, reps_min, reps_max, rest_sec
                FROM program_day_exercises
                WHERE program_day_id = $1
                ORDER BY sort_order, id
                """,
                program_day_id,
            )
            for idx, ex in enumerate(day_ex, start=1):
                se = await conn.fetchrow(
                    """
                    INSERT INTO session_exercises (session_id, exercise_id, sort_order, rest_sec)
                    VALUES ($1, $2, $3, $4)
                    RETURNING id
                    """,
                    row["id"],
                    ex["exercise_id"],
                    ex["sort_order"] if ex["sort_order"] is not None else idx,
                    ex["rest_sec"],
                )
                planned_sets = int(ex["sets"] or 0)
                for set_i in range(1, max(planned_sets, 0) + 1):
                    await conn.execute(
                        """
                        INSERT INTO session_sets (session_exercise_id, set_index, reps, is_warmup)
                        VALUES ($1, $2, $3, FALSE)
                        """,
                        se["id"],
                        set_i,
                        ex["reps_max"] or ex["reps_min"],
                    )
    return await get_session(row["id"], actor_id, is_trainer)


async def get_session(session_id: int, actor_id: int, is_trainer: bool) -> dict:
    row = await fetchrow("SELECT * FROM workout_sessions WHERE id = $1", session_id)
    if row is None:
        raise AppError("SESSION_NOT_FOUND", "Тренировка не найдена", http_status=404)
    if row["status"] == "in_progress" and row.get("paused_at") is None:
        last = row.get("last_activity_at") or row.get("started_at") or row.get("created_at")
        if last is not None:
            last_utc = last if last.tzinfo is not None else last.replace(tzinfo=UTC)
            if datetime.now(UTC) - last_utc.astimezone(UTC) > SESSION_INACTIVITY:
                await abandon_session(session_id, reason="inactivity_1h_on_open")
                row = await fetchrow("SELECT * FROM workout_sessions WHERE id = $1", session_id)
            else:
                await _touch_activity(session_id)
        else:
            await _touch_activity(session_id)
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
        SELECT se.id, se.exercise_id, se.sort_order, se.rest_sec, se.status, e.name, e.primary_muscle
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
        max_w = None
        for s in sets:
            if s.get("is_warmup"):
                continue
            w = s.get("weight_kg")
            if w is None:
                continue
            max_w = float(w) if max_w is None else max(max_w, float(w))
        if max_w is not None and data.get("lead_client_id"):
            prev = await fetchrow(
                """
                SELECT MAX(ss.weight_kg) AS max_w
                FROM session_sets ss
                JOIN session_exercises se ON se.id = ss.session_exercise_id
                JOIN workout_sessions ws ON ws.id = se.session_id
                WHERE se.exercise_id = $1
                  AND ws.status = 'completed'
                  AND ws.id <> $2
                  AND ss.is_warmup = FALSE
                  AND ss.weight_kg IS NOT NULL
                  AND (
                      ws.lead_client_id = $3
                      OR EXISTS (
                          SELECT 1 FROM workout_session_clients c
                          WHERE c.session_id = ws.id AND c.client_id = $3
                      )
                  )
                """,
                ex["exercise_id"],
                session_id,
                data["lead_client_id"],
            )
            if prev and prev["max_w"] is not None:
                item["weight_delta_kg"] = round(max_w - float(prev["max_w"]), 1)
        items.append(item)
    data["exercises"] = items
    data["sets_count"] = sum(len(ex.get("sets") or []) for ex in items)
    data["exercises_count"] = len(items)
    return data


async def add_exercise(
    session_id: int,
    actor_id: int,
    is_trainer: bool,
    exercise_id: int,
    rest_sec: int | None,
    sets: int | None = None,
    reps: int | None = None,
) -> dict:
    await get_session(session_id, actor_id, is_trainer)
    async with transaction() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO session_exercises (session_id, exercise_id, sort_order, rest_sec)
            VALUES ($1, $2, COALESCE((SELECT MAX(sort_order)+1 FROM session_exercises WHERE session_id = $1), 1), $3)
            RETURNING id
            """,
            session_id,
            exercise_id,
            rest_sec,
        )
        # Same as program-day start: seed planned sets so live UI matches trainer workouts.
        planned_sets = int(sets or 0)
        target_reps = int(reps) if reps is not None else None
        for set_i in range(1, max(planned_sets, 0) + 1):
            await conn.execute(
                """
                INSERT INTO session_sets (session_exercise_id, set_index, reps, is_warmup)
                VALUES ($1, $2, $3, FALSE)
                """,
                row["id"],
                set_i,
                target_reps,
            )
    return await get_session(session_id, actor_id, is_trainer) | {"added_exercise_id": row["id"]}


async def delete_exercise(session_id: int, se_id: int, actor_id: int, is_trainer: bool) -> dict:
    await get_session(session_id, actor_id, is_trainer)
    row = await fetchrow(
        """
        DELETE FROM session_exercises
        WHERE id = $1 AND session_id = $2
        RETURNING id
        """,
        se_id,
        session_id,
    )
    if row is None:
        raise AppError("SESSION_EXERCISE_NOT_FOUND", "Упражнение сессии не найдено", http_status=404)
    return await get_session(session_id, actor_id, is_trainer)


async def add_set(session_id: int, se_id: int, actor_id: int, is_trainer: bool, payload: SetIn) -> dict:
    await get_session(session_id, actor_id, is_trainer)
    client_op_id = getattr(payload, "client_op_id", None)
    if client_op_id:
        existing = await fetchrow(
            """
            SELECT id FROM session_sets
            WHERE session_exercise_id = $1 AND client_op_id = $2
            """,
            se_id,
            client_op_id,
        )
        if existing is not None:
            return await get_session(session_id, actor_id, is_trainer)
    # Fill next planned (empty) set first — avoids "#1 —" leftover while #2/#3 get values.
    pending = await fetchrow(
        """
        SELECT id FROM session_sets
        WHERE session_exercise_id = $1 AND completed_at IS NULL
        ORDER BY set_index, id
        LIMIT 1
        """,
        se_id,
    )
    if pending is not None:
        await execute(
            """
            UPDATE session_sets
            SET weight_kg = $2, reps = $3, is_warmup = $4, completed_at = NOW(), client_op_id = $5
            WHERE id = $1
            """,
            pending["id"],
            payload.weight_kg,
            payload.reps,
            payload.is_warmup,
            client_op_id,
        )
    else:
        await fetchrow(
            """
            INSERT INTO session_sets (session_exercise_id, set_index, weight_kg, reps, is_warmup, completed_at, client_op_id)
            VALUES (
                $1,
                COALESCE((SELECT MAX(set_index)+1 FROM session_sets WHERE session_exercise_id = $1), 1),
                $2, $3, $4, NOW(), $5
            )
            RETURNING id
            """,
            se_id,
            payload.weight_kg,
            payload.reps,
            payload.is_warmup,
            client_op_id,
        )
    await _touch_activity(session_id)
    return await get_session(session_id, actor_id, is_trainer)


async def complete_session(session_id: int, actor_id: int, is_trainer: bool) -> dict:
    session = await get_session(session_id, actor_id, is_trainer)
    done = sum(1 for e in session["exercises"] if e["sets"])
    total = len(session["exercises"])
    if session.get("status") != "completed":
        await execute(
            f"""
            UPDATE workout_sessions
            SET status = 'completed',
                finished_at = NOW(),
                paused_at = NULL,
                duration_sec = {_active_duration_sql()}
            WHERE id = $1 AND status <> 'completed'
            """,
            session_id,
        )
        if session.get("calendar_event_id"):
            await execute(
                "UPDATE calendar_events SET status = 'completed' WHERE id = $1",
                session["calendar_event_id"],
            )
        else:
            # Solo/program sessions still count as attendance for a same-day planned visit.
            client_id = session.get("lead_client_id") or (actor_id if not is_trainer else None)
            if client_id:
                await execute(
                    """
                    UPDATE calendar_events
                    SET status = 'completed',
                        session_id = COALESCE(session_id, $1)
                    WHERE client_id = $2
                      AND starts_at::date = CURRENT_DATE
                      AND status IN ('scheduled', 'in_progress')
                    """,
                    session_id,
                    client_id,
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


async def volume_progress(client_id: int, *, days: int = 30) -> dict:
    """Daily tonnage (weight×reps) + per-exercise volume for the last N days."""
    days = max(7, min(int(days or 30), 90))
    daily = await fetch(
        """
        SELECT COALESCE(ws.finished_at, ws.started_at, ws.created_at)::date AS day,
               COALESCE(SUM(ss.weight_kg * ss.reps) FILTER (WHERE ss.is_warmup = FALSE), 0) AS volume_kg
        FROM workout_sessions ws
        JOIN session_exercises se ON se.session_id = ws.id
        JOIN session_sets ss ON ss.session_exercise_id = se.id
        WHERE ws.status = 'completed'
          AND COALESCE(ws.finished_at, ws.started_at, ws.created_at) >= CURRENT_DATE - ($2 * INTERVAL '1 day')
          AND (
              ws.lead_client_id = $1
              OR EXISTS (
                  SELECT 1 FROM workout_session_clients c
                  WHERE c.session_id = ws.id AND c.client_id = $1
              )
          )
        GROUP BY day
        ORDER BY day
        """,
        client_id,
        days,
    )
    by_exercise = await fetch(
        """
        SELECT e.id AS exercise_id,
               e.name,
               COALESCE(SUM(ss.weight_kg * ss.reps) FILTER (WHERE ss.is_warmup = FALSE), 0) AS volume_kg,
               MAX(ss.weight_kg) FILTER (WHERE ss.is_warmup = FALSE) AS best_weight_kg,
               COUNT(DISTINCT ws.id) AS sessions_count
        FROM workout_sessions ws
        JOIN session_exercises se ON se.session_id = ws.id
        JOIN session_sets ss ON ss.session_exercise_id = se.id
        JOIN exercises e ON e.id = se.exercise_id
        WHERE ws.status = 'completed'
          AND COALESCE(ws.finished_at, ws.started_at, ws.created_at) >= CURRENT_DATE - ($2 * INTERVAL '1 day')
          AND (
              ws.lead_client_id = $1
              OR EXISTS (
                  SELECT 1 FROM workout_session_clients c
                  WHERE c.session_id = ws.id AND c.client_id = $1
              )
          )
        GROUP BY e.id, e.name
        HAVING COALESCE(SUM(ss.weight_kg * ss.reps) FILTER (WHERE ss.is_warmup = FALSE), 0) > 0
        ORDER BY volume_kg DESC
        LIMIT 12
        """,
        client_id,
        days,
    )
    series = [
        {
            "date": row["day"].isoformat() if hasattr(row["day"], "isoformat") else str(row["day"]),
            "volume_kg": float(row["volume_kg"] or 0),
        }
        for row in daily
    ]
    total = sum(item["volume_kg"] for item in series)
    return {
        "days": days,
        "total_volume_kg": round(total, 1),
        "series": series,
        "by_exercise": [
            {
                "exercise_id": row["exercise_id"],
                "name": row["name"],
                "volume_kg": float(row["volume_kg"] or 0),
                "best_weight_kg": float(row["best_weight_kg"]) if row["best_weight_kg"] is not None else None,
                "sessions_count": int(row["sessions_count"] or 0),
            }
            for row in by_exercise
        ],
    }


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
            ) AS sets_count,
            (
                SELECT COUNT(*) FROM session_exercises se WHERE se.session_id = s.id
            ) AS exercises_count,
            (
                SELECT COALESCE(
                    array_agg(DISTINCT e.primary_muscle) FILTER (WHERE e.primary_muscle IS NOT NULL),
                    '{{}}'::text[]
                )
                FROM session_exercises se
                JOIN exercises e ON e.id = se.exercise_id
                WHERE se.session_id = s.id
            ) AS focus_muscles,
            (
                SELECT e.name
                FROM session_exercises se
                JOIN exercises e ON e.id = se.exercise_id
                JOIN session_sets ss ON ss.session_exercise_id = se.id
                WHERE se.session_id = s.id
                  AND ss.is_warmup = FALSE
                  AND ss.weight_kg IS NOT NULL
                  AND ss.weight_kg >= COALESCE((
                      SELECT MAX(ss2.weight_kg)
                      FROM session_sets ss2
                      JOIN session_exercises se2 ON se2.id = ss2.session_exercise_id
                      JOIN workout_sessions ws2 ON ws2.id = se2.session_id
                      WHERE se2.exercise_id = se.exercise_id
                        AND ws2.status = 'completed'
                        AND ws2.id <> s.id
                        AND (
                            ws2.lead_client_id = $1
                            OR EXISTS (
                                SELECT 1 FROM workout_session_clients c2
                                WHERE c2.session_id = ws2.id AND c2.client_id = $1
                            )
                        )
                  ), 0)
                ORDER BY ss.weight_kg DESC
                LIMIT 1
            ) AS record_exercise
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
        muscles = item.pop("focus_muscles", None) or []
        item["focus_muscles"] = list(muscles) if not isinstance(muscles, list) else muscles
        record = item.pop("record_exercise", None)
        if record:
            item["personal_record"] = f"Личный рекорд в {record}"
        items.append(item)
    return items, int(total["total"])
