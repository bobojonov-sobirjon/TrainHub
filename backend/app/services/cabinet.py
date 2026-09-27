from datetime import date

from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow
from app.db.transactions import transaction
from app.schemas.stage import MeasurementIn, NoteIn, NotificationPrefsIn
from app.services.storage import save_bytes


async def home(user_id: int) -> dict:
    profile = await fetchrow(
        "SELECT created_at, weight_goal_kg FROM users WHERE id = $1",
        user_id,
    )
    last_m = await fetchrow(
        """
        SELECT weight_kg, body_fat_pct, recorded_at
        FROM body_measurements WHERE client_id = $1
        ORDER BY recorded_at DESC LIMIT 1
        """,
        user_id,
    )
    first_m = await fetchrow(
        """
        SELECT weight_kg FROM body_measurements
        WHERE client_id = $1 AND weight_kg IS NOT NULL
        ORDER BY recorded_at ASC LIMIT 1
        """,
        user_id,
    )
    chart = await fetch(
        """
        SELECT recorded_at::date AS date, weight_kg
        FROM body_measurements
        WHERE client_id = $1 AND weight_kg IS NOT NULL
        ORDER BY recorded_at DESC LIMIT 30
        """,
        user_id,
    )
    last_s = await fetchrow(
        """
        SELECT s.id, s.duration_sec, s.calories, s.finished_at, s.kinds,
               t.first_name AS trainer_first, t.last_name AS trainer_last,
               (
                   SELECT COUNT(*) FROM session_exercises se WHERE se.session_id = s.id
               ) AS exercises_count,
               (
                   SELECT COUNT(*) FROM session_sets ss
                   JOIN session_exercises se ON se.id = ss.session_exercise_id
                   WHERE se.session_id = s.id
               ) AS sets_count
        FROM workout_sessions s
        LEFT JOIN users t ON t.id = s.trainer_id
        WHERE s.status = 'completed' AND (s.lead_client_id = $1 OR EXISTS (
            SELECT 1 FROM workout_session_clients c WHERE c.session_id = s.id AND c.client_id = $1
        ))
        ORDER BY s.finished_at DESC NULLS LAST LIMIT 1
        """,
        user_id,
    )
    top_sets = []
    if last_s:
        top_sets = [
            dict(r)
            for r in await fetch(
                """
                SELECT e.name, MAX(ss.weight_kg) AS weight_kg, MAX(ss.reps) AS reps
                FROM session_exercises se
                JOIN exercises e ON e.id = se.exercise_id
                JOIN session_sets ss ON ss.session_exercise_id = se.id
                WHERE se.session_id = $1 AND ss.weight_kg IS NOT NULL
                GROUP BY e.name
                ORDER BY MAX(ss.weight_kg) DESC
                LIMIT 3
                """,
                last_s["id"],
            )
        ]
    attendance = await fetch(
        """
        SELECT starts_at::date AS date, status
        FROM calendar_events
        WHERE client_id = $1 AND starts_at >= NOW() - INTERVAL '30 days'
        ORDER BY starts_at
        """,
        user_id,
    )
    streak_rows = await fetch(
        """
        SELECT DISTINCT COALESCE(finished_at, created_at)::date AS day
        FROM workout_sessions
        WHERE status = 'completed'
          AND (lead_client_id = $1 OR EXISTS (
              SELECT 1 FROM workout_session_clients c
              WHERE c.session_id = workout_sessions.id AND c.client_id = $1
          ))
        ORDER BY day DESC
        LIMIT 60
        """,
        user_id,
    )
    days_done = {r["day"] for r in streak_rows}
    streak = 0
    cursor = date.today()
    if cursor not in days_done:
        cursor = date.fromordinal(cursor.toordinal() - 1)
    while cursor in days_done:
        streak += 1
        cursor = date.fromordinal(cursor.toordinal() - 1)

    days = 0
    if profile:
        days = max(0, (date.today() - profile["created_at"].date()).days)
    goal = profile["weight_goal_kg"] if profile else None
    current_w = last_m["weight_kg"] if last_m else None
    start_w = first_m["weight_kg"] if first_m else None
    progress_pct = None
    weight_delta_30d = None
    if current_w is not None and goal is not None and start_w is not None and goal != start_w:
        progress_pct = float((current_w - start_w) / (goal - start_w) * 100)
        progress_pct = max(0, min(100, round(progress_pct, 1)))
    if chart:
        oldest = chart[-1]["weight_kg"]
        newest = chart[0]["weight_kg"]
        if oldest is not None and newest is not None:
            weight_delta_30d = newest - oldest
    unread = await fetchrow(
        "SELECT COUNT(*) AS total FROM notifications WHERE user_id = $1 AND is_read = FALSE",
        user_id,
    )
    notes = await list_trainer_notes(user_id)
    last_session = dict(last_s) if last_s else None
    if last_session:
        last_session["top_sets"] = top_sets
        last_session["trainer_name"] = " ".join(
            part for part in [last_session.pop("trainer_first", None), last_session.pop("trainer_last", None)] if part
        ) or None
    return {
        "weight_kg": current_w,
        "body_fat_pct": last_m["body_fat_pct"] if last_m else None,
        "weight_goal_kg": goal,
        "progress_pct": progress_pct,
        "weight_delta_30d": weight_delta_30d,
        "streak": streak,
        "unread_count": int(unread["total"]) if unread else 0,
        "days_in_program": days,
        "weight_chart": [dict(r) for r in reversed(chart)],
        "attendance_30d": [dict(r) for r in attendance],
        "last_session": last_session,
        "trainer_notes": notes[:5],
    }


async def measurements(user_id: int) -> list[dict]:
    rows = await fetch(
        "SELECT * FROM body_measurements WHERE client_id = $1 ORDER BY recorded_at DESC",
        user_id,
    )
    return [dict(r) for r in rows]


async def add_own_measurement(user_id: int, payload: MeasurementIn) -> dict:
    row = await fetchrow(
        """
        INSERT INTO body_measurements (
            client_id, recorded_by, weight_kg, body_fat_pct, muscle_mass_kg, water_pct,
            chest_cm, back_cm, waist_cm, hips_cm, thigh_cm, calf_cm, neck_cm, shoulders_cm,
            arm_cm, arm_left_cm, arm_right_cm, forearm_cm
        ) VALUES ($1,$1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
        RETURNING id
        """,
        user_id,
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
        payload.arm_left_cm,
        payload.arm_right_cm,
        payload.forearm_cm,
    )
    return {"id": row["id"]}


async def patch_measurement(user_id: int, measurement_id: int, payload: MeasurementIn) -> dict:
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise AppError("VALIDATION_ERROR", "Нет полей для обновления", http_status=422)
    row = await fetchrow(
        "SELECT id FROM body_measurements WHERE id = $1 AND client_id = $2",
        measurement_id,
        user_id,
    )
    if row is None:
        raise AppError("MEASUREMENT_NOT_FOUND", "Замер не найден", http_status=404)
    sets = []
    args: list = [measurement_id, user_id]
    for key, value in data.items():
        args.append(value)
        sets.append(f"{key} = ${len(args)}")
    await execute(
        f"UPDATE body_measurements SET {', '.join(sets)} WHERE id = $1 AND client_id = $2",
        *args,
    )
    updated = await fetchrow("SELECT * FROM body_measurements WHERE id = $1", measurement_id)
    return dict(updated)


async def measurements_chart(user_id: int, metric: str) -> dict:
    from app.core.constants import MEASUREMENT_METRICS

    if metric not in MEASUREMENT_METRICS:
        raise AppError("VALIDATION_ERROR", "Некорректная метрика", http_status=422)
    rows = await fetch(
        f"""
        SELECT recorded_at::date AS date, {metric} AS value
        FROM body_measurements
        WHERE client_id = $1 AND {metric} IS NOT NULL
        ORDER BY recorded_at ASC
        """,
        user_id,
    )
    return {"metric": metric, "points": [dict(r) for r in rows]}


async def list_trainer_notes(user_id: int) -> list[dict]:
    rows = await fetch(
        """
        SELECT tn.id, tn.text, tn.created_at, tc.trainer_id,
               u.first_name AS trainer_first, u.last_name AS trainer_last
        FROM trainer_notes tn
        JOIN trainer_clients tc ON tc.id = tn.trainer_client_id
        JOIN users u ON u.id = tc.trainer_id
        WHERE tc.client_id = $1 AND tn.deleted_at IS NULL
        ORDER BY tn.created_at DESC
        LIMIT 50
        """,
        user_id,
    )
    items = []
    for row in rows:
        item = dict(row)
        item["trainer_name"] = " ".join(
            part for part in [item.pop("trainer_first", None), item.pop("trainer_last", None)] if part
        )
        items.append(item)
    return items


async def unread_count(user_id: int) -> dict:
    row = await fetchrow(
        "SELECT COUNT(*) AS total FROM notifications WHERE user_id = $1 AND is_read = FALSE",
        user_id,
    )
    return {"unread_count": int(row["total"]) if row else 0}


async def progress(user_id: int) -> dict:
    current = await fetchrow(
        "SELECT * FROM body_measurements WHERE client_id = $1 ORDER BY recorded_at DESC LIMIT 1",
        user_id,
    )
    prev = await fetchrow(
        """
        SELECT * FROM body_measurements WHERE client_id = $1
        ORDER BY recorded_at DESC OFFSET 1 LIMIT 1
        """,
        user_id,
    )
    photos = await fetch(
        """
        SELECT s.id, s.taken_on,
               (SELECT COUNT(*) FROM photo_progress_images i WHERE i.set_id = s.id) AS images_count
        FROM photo_progress_sets s
        WHERE s.user_id = $1
        ORDER BY s.taken_on DESC
        LIMIT 12
        """,
        user_id,
    )
    return {
        "current": dict(current) if current else None,
        "previous": dict(prev) if prev else None,
        "photo_sets": [dict(p) for p in photos],
    }


async def list_notes(user_id: int, q: str | None) -> list[dict]:
    if q:
        rows = await fetch(
            """
            SELECT id, title, body, created_at, updated_at
            FROM personal_notes
            WHERE user_id = $1 AND deleted_at IS NULL
              AND (title ILIKE $2 OR body ILIKE $2)
            ORDER BY created_at DESC
            """,
            user_id,
            f"%{q}%",
        )
    else:
        rows = await fetch(
            """
            SELECT id, title, body, created_at, updated_at
            FROM personal_notes
            WHERE user_id = $1 AND deleted_at IS NULL
            ORDER BY created_at DESC
            """,
            user_id,
        )
    return [dict(r) for r in rows]


async def create_note(user_id: int, payload: NoteIn) -> dict:
    row = await fetchrow(
        """
        INSERT INTO personal_notes (user_id, title, body)
        VALUES ($1,$2,$3)
        RETURNING id, title, body, created_at, updated_at
        """,
        user_id,
        payload.title,
        payload.body,
    )
    return dict(row)


async def update_note(user_id: int, note_id: int, payload: NoteIn) -> dict:
    row = await fetchrow(
        """
        UPDATE personal_notes
        SET title = $3, body = $4, updated_at = NOW()
        WHERE id = $1 AND user_id = $2 AND deleted_at IS NULL
        RETURNING id, title, body, created_at, updated_at
        """,
        note_id,
        user_id,
        payload.title,
        payload.body,
    )
    if row is None:
        raise AppError("NOTE_NOT_FOUND", "Заметка не найдена", http_status=404)
    return dict(row)


async def delete_note(user_id: int, note_id: int) -> None:
    await execute(
        "UPDATE personal_notes SET deleted_at = NOW() WHERE id = $1 AND user_id = $2",
        note_id,
        user_id,
    )


async def notifications(user_id: int, tab: str) -> list[dict]:
    if tab == "later":
        rows = await fetch(
            """
            SELECT id, type, title, body, is_read, scheduled_at, created_at
            FROM notifications
            WHERE user_id = $1 AND scheduled_at IS NOT NULL AND scheduled_at > NOW()
            ORDER BY scheduled_at
            """,
            user_id,
        )
    else:
        rows = await fetch(
            """
            SELECT id, type, title, body, is_read, scheduled_at, created_at
            FROM notifications
            WHERE user_id = $1 AND (scheduled_at IS NULL OR scheduled_at <= NOW())
            ORDER BY created_at DESC
            """,
            user_id,
        )
    return [dict(r) for r in rows]


async def read_notification(user_id: int, note_id: int) -> None:
    await execute(
        "UPDATE notifications SET is_read = TRUE WHERE id = $1 AND user_id = $2",
        note_id,
        user_id,
    )


async def read_all(user_id: int) -> None:
    await execute("UPDATE notifications SET is_read = TRUE WHERE user_id = $1", user_id)


async def get_prefs(user_id: int) -> dict:
    await execute(
        "INSERT INTO notification_preferences (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
        user_id,
    )
    row = await fetchrow("SELECT * FROM notification_preferences WHERE user_id = $1", user_id)
    return dict(row)


async def update_prefs(user_id: int, payload: NotificationPrefsIn) -> dict:
    await get_prefs(user_id)
    await execute(
        """
        UPDATE notification_preferences
        SET push_enabled = COALESCE($2, push_enabled),
            email_enabled = COALESCE($3, email_enabled),
            workout_reminder = COALESCE($4, workout_reminder),
            new_client_request = COALESCE($5, new_client_request),
            client_report = COALESCE($6, client_report)
        WHERE user_id = $1
        """,
        user_id,
        payload.push_enabled,
        payload.email_enabled,
        payload.workout_reminder,
        payload.new_client_request,
        payload.client_report,
    )
    return await get_prefs(user_id)


async def add_photo_set(user_id: int, taken_on: date, files: list[tuple[str, bytes, str]]) -> dict:
    async with transaction() as conn:
        aset = await conn.fetchrow(
            "INSERT INTO photo_progress_sets (user_id, taken_on) VALUES ($1,$2) RETURNING id, taken_on",
            user_id,
            taken_on,
        )
        images = []
        for index, (angle, data, filename) in enumerate(files):
            url = await save_bytes(data, folder=f"progress/{user_id}", filename=filename)
            img = await conn.fetchrow(
                """
                INSERT INTO photo_progress_images (set_id, angle, image_url, sort_order)
                VALUES ($1,$2,$3,$4) RETURNING id, angle, image_url
                """,
                aset["id"],
                angle,
                url,
                index,
            )
            images.append(dict(img))
    return {"id": aset["id"], "taken_on": aset["taken_on"], "images": images}


async def list_photo_sets(user_id: int) -> list[dict]:
    sets = await fetch(
        "SELECT id, taken_on, created_at FROM photo_progress_sets WHERE user_id = $1 ORDER BY taken_on DESC",
        user_id,
    )
    result = []
    for s in sets:
        images = await fetch(
            "SELECT id, angle, image_url, sort_order FROM photo_progress_images WHERE set_id = $1 ORDER BY sort_order",
            s["id"],
        )
        item = dict(s)
        item["images"] = [dict(i) for i in images]
        result.append(item)
    return result
