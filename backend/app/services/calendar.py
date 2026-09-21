from datetime import datetime

from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow


async def list_events(trainer_id: int, date_from: datetime | None, date_to: datetime | None) -> list[dict]:
    args: list = [trainer_id]
    where = ["e.trainer_id = $1"]
    if date_from:
        args.append(date_from)
        where.append(f"e.starts_at >= ${len(args)}")
    if date_to:
        args.append(date_to)
        where.append(f"e.starts_at < ${len(args)}")
    rows = await fetch(
        f"""
        SELECT
            e.id, e.client_id, e.starts_at, e.ends_at, e.duration_min, e.format,
            e.kinds, e.focus_muscles, e.status, e.note, e.reminder, e.repeat_weekly, e.session_id,
            u.first_name, u.last_name, u.phone
        FROM calendar_events e
        LEFT JOIN users u ON u.id = e.client_id
        WHERE {" AND ".join(where)}
        ORDER BY e.starts_at ASC
        """,
        *args,
    )
    return [dict(r) for r in rows]


async def create_event(trainer_id: int, payload) -> dict:
    if payload.reminder not in {"none", "1h", "3h"}:
        raise AppError("VALIDATION_ERROR", "Некорректное напоминание", http_status=422)
    duration = int((payload.ends_at - payload.starts_at).total_seconds() // 60)
    row = await fetchrow(
        """
        INSERT INTO calendar_events (
            trainer_id, client_id, starts_at, ends_at, duration_min, format,
            kinds, focus_muscles, status, note, reminder, repeat_weekly
        ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
        RETURNING id
        """,
        trainer_id,
        payload.client_id,
        payload.starts_at,
        payload.ends_at,
        duration,
        payload.format,
        payload.kinds,
        payload.focus_muscles,
        payload.status,
        payload.note,
        payload.reminder,
        payload.repeat_weekly,
    )
    if payload.repeat_weekly:
        for week in range(1, 12):
            await execute(
                """
                INSERT INTO calendar_events (
                    trainer_id, client_id, starts_at, ends_at, duration_min, format,
                    kinds, focus_muscles, status, note, reminder, repeat_weekly
                )
                SELECT trainer_id, client_id, starts_at + ($2 * INTERVAL '7 days'),
                       ends_at + ($2 * INTERVAL '7 days'), duration_min, format,
                       kinds, focus_muscles, status, note, reminder, FALSE
                FROM calendar_events WHERE id = $1
                """,
                row["id"],
                week,
            )
    return await get_event(trainer_id, row["id"])


async def get_event(trainer_id: int, event_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT e.*, u.first_name, u.last_name, u.phone
        FROM calendar_events e
        LEFT JOIN users u ON u.id = e.client_id
        WHERE e.id = $1 AND e.trainer_id = $2
        """,
        event_id,
        trainer_id,
    )
    if row is None:
        raise AppError("EVENT_NOT_FOUND", "Событие календаря не найдено", http_status=404)
    return dict(row)


async def update_event(trainer_id: int, event_id: int, payload) -> dict:
    await get_event(trainer_id, event_id)
    duration = int((payload.ends_at - payload.starts_at).total_seconds() // 60)
    await execute(
        """
        UPDATE calendar_events
        SET client_id = $3, starts_at = $4, ends_at = $5, duration_min = $6,
            format = $7, kinds = $8, focus_muscles = $9, note = $10,
            reminder = $11, status = $12
        WHERE id = $1 AND trainer_id = $2
        """,
        event_id,
        trainer_id,
        payload.client_id,
        payload.starts_at,
        payload.ends_at,
        duration,
        payload.format,
        payload.kinds,
        payload.focus_muscles,
        payload.note,
        payload.reminder,
        payload.status,
    )
    return await get_event(trainer_id, event_id)


async def cancel_event(trainer_id: int, event_id: int) -> dict:
    event = await get_event(trainer_id, event_id)
    await execute(
        "UPDATE calendar_events SET status = 'cancelled' WHERE id = $1 AND trainer_id = $2",
        event_id,
        trainer_id,
    )
    if event.get("client_id"):
        await execute(
            """
            INSERT INTO attention_items (trainer_id, client_id, reason)
            VALUES ($1, $2, 'cancelled_session')
            """,
            trainer_id,
            event["client_id"],
        )
    return await get_event(trainer_id, event_id)


async def delete_event(trainer_id: int, event_id: int) -> None:
    await get_event(trainer_id, event_id)
    await execute("DELETE FROM calendar_events WHERE id = $1 AND trainer_id = $2", event_id, trainer_id)
