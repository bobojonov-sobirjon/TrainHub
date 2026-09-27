import json
import logging

from app.db.connection import execute, fetch, fetchrow
from app.services import firebase as fb

logger = logging.getLogger(__name__)

PREF_BY_TYPE = {
    "new_client_request": "new_client_request",
    "request_accepted": "new_client_request",
    "request_rejected": "new_client_request",
    "workout": "workout_reminder",
    "workout_cancelled": "workout_reminder",
    "client_report": "client_report",
}


async def _may_push(user_id: int, ntype: str) -> bool:
    prefs = await fetchrow(
        """
        SELECT push_enabled, workout_reminder, new_client_request, client_report
        FROM notification_preferences
        WHERE user_id = $1
        """,
        user_id,
    )
    if prefs is None:
        return True
    if not prefs["push_enabled"]:
        return False
    field = PREF_BY_TYPE.get(ntype)
    if field and prefs[field] is False:
        return False
    return True


async def _send_user_push(user_id: int, title: str, body: str, data: dict | None) -> None:
    rows = await fetch("SELECT token FROM user_devices WHERE user_id = $1", user_id)
    tokens = [row["token"] for row in rows if row["token"]]
    if not tokens:
        return
    stale = await fb.send_push(tokens, title, body, data)
    if stale:
        await execute("DELETE FROM user_devices WHERE token = ANY($1::text[])", stale)


async def create_notification(
    user_id: int,
    *,
    ntype: str,
    title: str,
    body: str,
    payload: dict | None = None,
) -> dict:
    row = await fetchrow(
        """
        INSERT INTO notifications (user_id, type, title, body, payload_json)
        VALUES ($1, $2, $3, $4, $5::jsonb)
        RETURNING id, user_id, type, title, body, payload_json, is_read, scheduled_at, created_at
        """,
        user_id,
        ntype,
        title,
        body,
        json.dumps(payload or {}),
    )
    item = dict(row)
    if await _may_push(user_id, ntype):
        try:
            await _send_user_push(user_id, title, body, {"type": ntype, **(payload or {})})
        except Exception as exc:
            logger.exception("Push after notification %s failed: %s", item["id"], exc)
    return item
