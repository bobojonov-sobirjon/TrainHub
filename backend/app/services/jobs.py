"""Lightweight in-process background jobs (reminders, auto no-show, subscription expire)."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from app.db.connection import execute, fetch, fetchrow
from app.services.notify import create_notification

logger = logging.getLogger(__name__)

_REMINDER_OFFSET = {
    "15m": timedelta(minutes=15),
    "1h": timedelta(hours=1),
    "3h": timedelta(hours=3),
    "1d": timedelta(days=1),
}

_task: asyncio.Task | None = None
_INTERVAL_SEC = 60


async def run_once() -> dict:
    """Run all job batches once. Safe to call from tests."""
    from app.services import sessions as sess

    stats = {
        "reminders": await send_workout_reminders(),
        "no_shows": await auto_mark_no_shows(),
        "expired_subs": await expire_subscriptions(),
        "abandoned_sessions": await sess.abandon_stale_sessions(),
    }
    return stats


async def send_workout_reminders() -> int:
    rows = await fetch(
        """
        SELECT e.id, e.client_id, e.trainer_id, e.starts_at, e.reminder, e.note,
               u.first_name AS trainer_first, u.last_name AS trainer_last
        FROM calendar_events e
        LEFT JOIN users u ON u.id = e.trainer_id
        WHERE e.status = 'scheduled'
          AND e.reminder IS NOT NULL AND e.reminder <> 'none'
          AND e.reminder_sent_at IS NULL
          AND e.client_id IS NOT NULL
          AND e.starts_at > NOW()
          AND e.starts_at <= NOW() + INTERVAL '1 day 5 minutes'
        """
    )
    sent = 0
    for row in rows:
        offset = _REMINDER_OFFSET.get((row["reminder"] or "").strip())
        if offset is None:
            continue
        window_start = row["starts_at"] - offset - timedelta(minutes=2)
        window_end = row["starts_at"] - offset + timedelta(minutes=3)
        now_row = await fetchrow("SELECT NOW() AS now")
        now = now_row["now"]
        if not (window_start <= now <= window_end):
            continue
        trainer_name = " ".join(
            part for part in [row.get("trainer_first"), row.get("trainer_last")] if part
        ).strip() or "Тренер"
        when = row["starts_at"].strftime("%H:%M")
        await create_notification(
            int(row["client_id"]),
            ntype="workout",
            title="Напоминание о тренировке",
            body=f"Занятие с {trainer_name} в {when}",
            payload={"event_id": int(row["id"]), "trainer_id": row.get("trainer_id")},
        )
        await execute(
            "UPDATE calendar_events SET reminder_sent_at = NOW() WHERE id = $1 AND reminder_sent_at IS NULL",
            row["id"],
        )
        sent += 1
    return sent


async def auto_mark_no_shows() -> int:
    """Past scheduled events (ended > 30 min ago) → no_show + attention item."""
    rows = await fetch(
        """
        SELECT id, trainer_id, client_id
        FROM calendar_events
        WHERE status = 'scheduled'
          AND ends_at < NOW() - INTERVAL '30 minutes'
          AND ends_at > NOW() - INTERVAL '14 days'
        """
    )
    count = 0
    for row in rows:
        await execute(
            "UPDATE calendar_events SET status = 'no_show' WHERE id = $1 AND status = 'scheduled'",
            row["id"],
        )
        if row.get("client_id") and row.get("trainer_id"):
            await execute(
                """
                INSERT INTO attention_items (trainer_id, client_id, reason)
                VALUES ($1, $2, 'no_show')
                """,
                row["trainer_id"],
                row["client_id"],
            )
        count += 1
    return count


async def expire_subscriptions() -> int:
    result = await execute(
        """
        UPDATE subscriptions
        SET status = 'expired'
        WHERE status = 'active'
          AND ends_at IS NOT NULL
          AND ends_at < NOW()
        """
    )
    # asyncpg returns e.g. "UPDATE 3"
    try:
        return int(str(result).split()[-1])
    except (ValueError, IndexError):
        return 0


async def _loop() -> None:
    await asyncio.sleep(5)
    while True:
        try:
            stats = await run_once()
            if any(stats.values()):
                logger.info("jobs tick %s", stats)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("background jobs failed")
        await asyncio.sleep(_INTERVAL_SEC)


async def start_jobs() -> asyncio.Task:
    global _task
    if _task and not _task.done():
        return _task
    _task = asyncio.create_task(_loop(), name="trainhub-jobs")
    logger.info("background jobs started")
    return _task


async def stop_jobs() -> None:
    global _task
    if _task is None:
        return
    _task.cancel()
    try:
        await _task
    except asyncio.CancelledError:
        pass
    _task = None
