from app.core.constants import DEVICE_PLATFORMS
from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow
from app.schemas.auth import DeviceIn


async def list_devices(user_id: int) -> list[dict]:
    rows = await fetch(
        """
        SELECT id, platform, token, device_name, app_version, last_seen_at, created_at
        FROM user_devices
        WHERE user_id = $1
        ORDER BY last_seen_at DESC
        """,
        user_id,
    )
    return [dict(r) for r in rows]


async def upsert_device(user_id: int, payload: DeviceIn) -> dict:
    if payload.platform not in DEVICE_PLATFORMS:
        raise AppError("VALIDATION_ERROR", "Платформа: ios, android или web", http_status=422)
    token = payload.token.strip()
    row = await fetchrow(
        """
        INSERT INTO user_devices (user_id, platform, token, device_name, app_version, last_seen_at)
        VALUES ($1, $2, $3, $4, $5, NOW())
        ON CONFLICT (token) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            platform = EXCLUDED.platform,
            device_name = COALESCE(EXCLUDED.device_name, user_devices.device_name),
            app_version = COALESCE(EXCLUDED.app_version, user_devices.app_version),
            last_seen_at = NOW()
        RETURNING id, platform, token, device_name, app_version, last_seen_at, created_at
        """,
        user_id,
        payload.platform,
        token,
        payload.device_name,
        payload.app_version,
    )
    return dict(row)


async def delete_device(user_id: int, device_id: int) -> None:
    row = await fetchrow(
        "DELETE FROM user_devices WHERE id = $1 AND user_id = $2 RETURNING id",
        device_id,
        user_id,
    )
    if row is None:
        raise AppError("DEVICE_NOT_FOUND", "Устройство не найдено", http_status=404)
