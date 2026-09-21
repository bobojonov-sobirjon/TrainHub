from datetime import date

from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow
from app.db.transactions import transaction
from app.schemas.stage import MeasurementIn, NoteIn, NotificationPrefsIn
from app.services.storage import save_bytes


async def home(user_id: int) -> dict:
    last_m = await fetchrow(
        """
        SELECT weight_kg, body_fat_pct, recorded_at
        FROM body_measurements WHERE client_id = $1
        ORDER BY recorded_at DESC LIMIT 1
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
        SELECT id, duration_sec, calories, finished_at
        FROM workout_sessions
        WHERE status = 'completed' AND (lead_client_id = $1 OR EXISTS (
            SELECT 1 FROM workout_session_clients c WHERE c.session_id = workout_sessions.id AND c.client_id = $1
        ))
        ORDER BY finished_at DESC NULLS LAST LIMIT 1
        """,
        user_id,
    )
    attendance = await fetch(
        """
        SELECT starts_at::date AS date, status
        FROM calendar_events
        WHERE client_id = $1 AND starts_at >= NOW() - INTERVAL '30 days'
        ORDER BY starts_at
        """,
        user_id,
    )
    first = await fetchrow(
        "SELECT created_at FROM users WHERE id = $1",
        user_id,
    )
    days = 0
    if first:
        days = max(0, (date.today() - first["created_at"].date()).days)
    return {
        "weight_kg": last_m["weight_kg"] if last_m else None,
        "body_fat_pct": last_m["body_fat_pct"] if last_m else None,
        "days_in_program": days,
        "weight_chart": [dict(r) for r in reversed(chart)],
        "attendance_30d": [dict(r) for r in attendance],
        "last_session": dict(last_s) if last_s else None,
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
            chest_cm, back_cm, waist_cm, hips_cm, thigh_cm, calf_cm, neck_cm, shoulders_cm, arm_cm, forearm_cm
        ) VALUES ($1,$1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
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
        payload.forearm_cm,
    )
    return {"id": row["id"]}


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
