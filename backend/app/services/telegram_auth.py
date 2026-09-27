import asyncio
import json
import logging
import random
import re
import secrets
import time

import httpx

from app.core.config import settings
from app.core.exceptions import AppError
from app.db.connection import execute, fetchrow
from app.db.sql_loader import sql
from app.deps.redis import get_redis
from app.schemas.auth import TelegramSendCodeIn, TelegramVerifyIn
from app.schemas.common import TokenPair
from app.services.social import _login_or_register

logger = logging.getLogger(__name__)
OTP_TTL_SEC = 600
OTP_MAX_ATTEMPTS = 5
_bot_username: str | None = None


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"[^\d+]", "", raw or "")
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if digits.startswith("8") and len(digits) == 11:
        digits = "+7" + digits[1:]
    if digits and not digits.startswith("+"):
        digits = "+" + digits
    if len(digits) < 10:
        raise AppError("VALIDATION_ERROR", "Некорректный номер телефона", http_status=422)
    return digits


def parse_identifier(raw: str) -> tuple[str, str]:
    value = (raw or "").strip()
    if not value:
        raise AppError("VALIDATION_ERROR", "Укажите телефон или Telegram username", http_status=422)
    if value.startswith("@") or not re.search(r"\d", value):
        username = value.lstrip("@").lower()
        if not re.fullmatch(r"[a-z][a-z0-9_]{3,31}", username):
            raise AppError("VALIDATION_ERROR", "Некорректный Telegram username", http_status=422)
        return "username", username
    return "phone", normalize_phone(value)


def _otp_key(id_type: str, value: str) -> str:
    return f"telegram_bot_otp:{id_type}:{value}"


def _id_key(id_type: str, value: str) -> str:
    return f"telegram_bot_id:{id_type}:{value}"


def _link_key(token: str) -> str:
    return f"telegram_bot_link:{token}"


async def bot_username() -> str | None:
    global _bot_username
    configured = (settings.telegram_bot_username or "").strip().lstrip("@")
    if configured:
        return configured
    if _bot_username:
        return _bot_username
    token = settings.telegram_bot_token.strip()
    if not token:
        return None
    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.get(f"https://api.telegram.org/bot{token}/getMe")
    if response.status_code != 200:
        return None
    _bot_username = (response.json().get("result") or {}).get("username")
    return _bot_username


async def _require_bot_username() -> str:
    name = await bot_username()
    if not name:
        raise AppError("SOCIAL_AUTH_NOT_CONFIGURED", "Telegram бот не настроен", http_status=501)
    return name


async def bot_info() -> dict:
    name = await bot_username()
    return {
        "bot_username": name,
        "bot_url": f"https://t.me/{name}" if name else None,
    }


async def _bot_send_message(chat_id: int, text: str) -> bool:
    token = settings.telegram_bot_token.strip()
    if not token:
        return False
    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text},
        )
    data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    if response.status_code == 200 and data.get("ok"):
        return True
    description = str(data.get("description") or response.text).lower()
    logger.warning("Telegram sendMessage failed: %s", response.text)
    if any(part in description for part in ("forbidden", "chat not found", "bot was blocked", "deactivated")):
        return False
    return False


def _new_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


async def _store_otp(id_type: str, value: str, payload: dict) -> None:
    payload = {**payload, "id_type": id_type, "value": value}
    payload.setdefault("created_at", time.time())
    redis = await get_redis()
    raw = json.dumps(payload)
    keys = [_otp_key(id_type, value)]
    if payload.get("phone"):
        keys.append(_otp_key("phone", payload["phone"]))
    if payload.get("username"):
        keys.append(_otp_key("username", str(payload["username"]).lower()))
    if payload.get("telegram_id"):
        keys.append(_otp_key("tg", str(payload["telegram_id"])))
    for key in dict.fromkeys(keys):
        await redis.set(key, raw, ex=OTP_TTL_SEC)


async def _load_otp(id_type: str, value: str) -> dict | None:
    redis = await get_redis()
    raw = await redis.get(_otp_key(id_type, value))
    if not raw:
        return None
    return json.loads(raw)


async def _delete_otp(payload: dict) -> None:
    redis = await get_redis()
    keys: list[str] = []
    if payload.get("id_type") and payload.get("value"):
        keys.append(_otp_key(str(payload["id_type"]), str(payload["value"])))
    if payload.get("phone"):
        keys.append(_otp_key("phone", payload["phone"]))
    if payload.get("username"):
        keys.append(_otp_key("username", str(payload["username"]).lower()))
    if payload.get("telegram_id"):
        keys.append(_otp_key("tg", str(payload["telegram_id"])))
    if keys:
        await redis.delete(*dict.fromkeys(keys))


async def _latest_pending_otp() -> dict | None:
    redis = await get_redis()
    latest: dict | None = None
    async for key in redis.scan_iter("telegram_bot_otp:*"):
        raw = await redis.get(key)
        if not raw:
            continue
        data = json.loads(raw)
        if data.get("telegram_id"):
            continue
        if latest is None or float(data.get("created_at") or 0) > float(latest.get("created_at") or 0):
            latest = data
    return latest


async def _deliver_code(
    *,
    telegram_id: int,
    chat_id: int,
    payload: dict,
    first_name: str | None,
    last_name: str | None,
    username: str | None,
) -> dict:
    id_type = payload["id_type"]
    value = payload["value"]
    payload = {
        **payload,
        "telegram_id": telegram_id,
        "first_name": first_name or payload.get("first_name"),
        "last_name": last_name or payload.get("last_name"),
        "username": username or payload.get("username"),
        "attempts": 0,
    }
    phone = value if id_type == "phone" else payload.get("phone")
    if phone:
        payload["phone"] = phone
    await _upsert_profile(
        telegram_id=telegram_id,
        chat_id=chat_id,
        phone=phone,
        username=username or (value if id_type == "username" else None),
        first_name=first_name,
        last_name=last_name,
    )
    await _cache_telegram_id(id_type, value, telegram_id)
    await _store_otp(id_type, value, payload)
    await _bot_send_message(chat_id, f"Код входа в TrainHub: {payload['code']}\nДействует 10 минут.")
    return payload


async def _cache_telegram_id(id_type: str, value: str, telegram_id: int) -> None:
    redis = await get_redis()
    await redis.set(_id_key(id_type, value), str(telegram_id), ex=60 * 60 * 24 * 30)


async def _upsert_profile(
    *,
    telegram_id: int,
    chat_id: int,
    phone: str | None = None,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
) -> None:
    if phone:
        await execute(
            "UPDATE telegram_profiles SET phone = NULL WHERE phone = $1 AND telegram_user_id <> $2",
            phone,
            telegram_id,
        )
    await execute(
        """
        INSERT INTO telegram_profiles (telegram_user_id, chat_id, phone, username, first_name, last_name, updated_at)
        VALUES ($1,$2,$3,$4,$5,$6,NOW())
        ON CONFLICT (telegram_user_id) DO UPDATE SET
            chat_id = EXCLUDED.chat_id,
            phone = COALESCE(EXCLUDED.phone, telegram_profiles.phone),
            username = COALESCE(EXCLUDED.username, telegram_profiles.username),
            first_name = COALESCE(EXCLUDED.first_name, telegram_profiles.first_name),
            last_name = COALESCE(EXCLUDED.last_name, telegram_profiles.last_name),
            updated_at = NOW()
        """,
        telegram_id,
        chat_id,
        phone,
        username,
        first_name,
        last_name,
    )
    if phone:
        await execute(
            """
            INSERT INTO telegram_contacts (phone, chat_id, telegram_user_id, first_name, last_name, username, updated_at)
            VALUES ($1,$2,$3,$4,$5,$6,NOW())
            ON CONFLICT (phone) DO UPDATE SET
                chat_id = EXCLUDED.chat_id,
                telegram_user_id = EXCLUDED.telegram_user_id,
                first_name = EXCLUDED.first_name,
                last_name = EXCLUDED.last_name,
                username = EXCLUDED.username,
                updated_at = NOW()
            """,
            phone,
            chat_id,
            telegram_id,
            first_name,
            last_name,
            username,
        )


async def _resolve_telegram_id(id_type: str, value: str) -> int | None:
    redis = await get_redis()
    cached = await redis.get(_id_key(id_type, value))
    if cached:
        return int(cached)
    if id_type == "phone":
        row = await fetchrow("SELECT telegram_user_id FROM telegram_profiles WHERE phone = $1", value)
        if row:
            return int(row["telegram_user_id"])
        row = await fetchrow("SELECT telegram_user_id FROM telegram_contacts WHERE phone = $1", value)
        if row:
            return int(row["telegram_user_id"])
        user = await fetchrow(sql("auth/get_user_by_phone.sql"), value)
        if user:
            ident = await fetchrow(
                "SELECT provider_user_id FROM user_identities WHERE user_id = $1 AND provider = 'telegram'",
                user["id"],
            )
            if ident and str(ident["provider_user_id"]).isdigit():
                return int(ident["provider_user_id"])
        return None
    row = await fetchrow("SELECT telegram_user_id FROM telegram_profiles WHERE lower(username) = $1", value)
    if row:
        return int(row["telegram_user_id"])
    row = await fetchrow("SELECT telegram_user_id FROM telegram_contacts WHERE lower(coalesce(username, '')) = $1", value)
    if row:
        return int(row["telegram_user_id"])
    return None


async def _pending_bot_start(id_type: str, value: str, otp_code: str) -> dict:
    name = await _require_bot_username()
    token = secrets.token_hex(16)
    redis = await get_redis()
    await redis.set(
        _link_key(token),
        json.dumps({"id_type": id_type, "value": value, "code": otp_code}),
        ex=OTP_TTL_SEC,
    )
    await _store_otp(
        id_type,
        value,
        {
            "code": otp_code,
            "telegram_id": None,
            "attempts": 0,
            "id_type": id_type,
            "value": value,
            "phone": value if id_type == "phone" else None,
            "username": value if id_type == "username" else None,
        },
    )
    return {
        "requires_bot_start": True,
        "sent": False,
        "expires_in": OTP_TTL_SEC,
        "bot_username": name,
        "bot_url": f"https://t.me/{name}?start=login_{token}",
    }


async def send_login_code(payload: TelegramSendCodeIn) -> dict:
    id_type, value = parse_identifier(payload.identifier)
    name = await _require_bot_username()
    otp_code = _new_otp()
    telegram_id = await _resolve_telegram_id(id_type, value)
    if telegram_id:
        await _store_otp(
            id_type,
            value,
            {
                "code": otp_code,
                "telegram_id": telegram_id,
                "attempts": 0,
                "id_type": id_type,
                "value": value,
                "phone": value if id_type == "phone" else None,
                "username": value if id_type == "username" else None,
            },
        )
        sent = await _bot_send_message(
            telegram_id,
            f"Код входа в TrainHub: {otp_code}\nДействует 10 минут.",
        )
        if sent:
            result = {
                "requires_bot_start": False,
                "sent": True,
                "expires_in": OTP_TTL_SEC,
                "bot_username": name,
                "bot_url": f"https://t.me/{name}",
            }
            if settings.app_debug and not settings.is_production:
                result["debug_code"] = otp_code
            return result
    return await _pending_bot_start(id_type, value, otp_code)


async def handle_webhook(update: dict) -> dict:
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if not chat_id:
        return {"ok": True}

    text = (message.get("text") or "").strip()
    from_user = message.get("from") or {}
    telegram_id = int(from_user.get("id") or chat_id)
    username = (from_user.get("username") or "").lower() or None
    first_name = from_user.get("first_name")
    last_name = from_user.get("last_name")

    if not text.startswith("/start"):
        return {"ok": True}

    parts = text.split(maxsplit=1)
    start_payload = parts[1].strip() if len(parts) > 1 else ""
    if start_payload.startswith("login_"):
        token = start_payload.removeprefix("login_")
        redis = await get_redis()
        raw = await redis.get(_link_key(token))
        if not raw:
            await _bot_send_message(int(chat_id), "Ссылка устарела. Откройте новую ссылку из приложения.")
            return {"ok": True}
        link = json.loads(raw)
        pending = await _load_otp(link["id_type"], link["value"]) or {
            "code": link["code"],
            "id_type": link["id_type"],
            "value": link["value"],
            "phone": link["value"] if link["id_type"] == "phone" else None,
            "username": link["value"] if link["id_type"] == "username" else None,
        }
        if link["id_type"] == "username" and username and username != link["value"]:
            await _bot_send_message(int(chat_id), f"Этот Telegram не совпадает с @{link['value']}. Откройте ссылку из своего аккаунта.")
            return {"ok": True}
        pending["code"] = link["code"]
        await _deliver_code(
            telegram_id=telegram_id,
            chat_id=int(chat_id),
            payload=pending,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )
        await redis.delete(_link_key(token))
        return {"ok": True}

    pending = await _latest_pending_otp()
    if pending:
        await _deliver_code(
            telegram_id=telegram_id,
            chat_id=int(chat_id),
            payload=pending,
            first_name=first_name,
            last_name=last_name,
            username=username,
        )
        return {"ok": True}

    profile = await fetchrow(
        "SELECT * FROM telegram_profiles WHERE telegram_user_id = $1",
        telegram_id,
    )
    if profile is None:
        await _bot_send_message(int(chat_id), "Сначала запросите код в приложении, затем откройте ссылку на бота.")
        return {"ok": True}
    id_type = "phone" if profile["phone"] else "username"
    value = profile["phone"] or (profile["username"] or "").lower()
    if not value:
        await _bot_send_message(int(chat_id), "Сначала запросите код в приложении TrainHub.")
        return {"ok": True}
    await _deliver_code(
        telegram_id=telegram_id,
        chat_id=int(chat_id),
        payload={
            "code": _new_otp(),
            "id_type": id_type,
            "value": value,
            "phone": profile["phone"],
            "username": profile["username"],
        },
        first_name=first_name or profile["first_name"],
        last_name=last_name or profile["last_name"],
        username=username or profile["username"],
    )
    return {"ok": True}


async def verify_login_code(payload: TelegramVerifyIn) -> TokenPair:
    id_type, value = parse_identifier(payload.identifier)
    otp = await _load_otp(id_type, value)
    if otp is None and id_type == "phone":
        profile = await fetchrow("SELECT telegram_user_id FROM telegram_profiles WHERE phone = $1", value)
        if profile:
            otp = await _load_otp("tg", str(profile["telegram_user_id"]))
    if otp is None and id_type == "username":
        profile = await fetchrow(
            "SELECT telegram_user_id FROM telegram_profiles WHERE lower(username) = $1",
            value,
        )
        if profile:
            otp = await _load_otp("tg", str(profile["telegram_user_id"]))
    if otp is None:
        raise AppError("INVALID_CODE", "Сначала запросите код", http_status=400)
    if int(otp.get("attempts") or 0) >= OTP_MAX_ATTEMPTS:
        raise AppError("INVALID_CODE", "Слишком много попыток. Запросите код снова", http_status=400)
    if not otp.get("telegram_id"):
        raise AppError(
            "BOT_START_REQUIRED",
            "Откройте ссылку на бота из приложения и дождитесь кода",
            http_status=409,
        )
    if str(otp.get("code") or "") != payload.code.strip():
        otp["attempts"] = int(otp.get("attempts") or 0) + 1
        await _store_otp(id_type, value, otp)
        raise AppError("INVALID_CODE", "Неверный код", http_status=400)

    profile = await fetchrow(
        "SELECT * FROM telegram_profiles WHERE telegram_user_id = $1",
        int(otp["telegram_id"]),
    )
    await _delete_otp(otp)
    phone = (profile["phone"] if profile else None) or otp.get("phone") or (value if id_type == "phone" else None)
    return await _login_or_register(
        provider="telegram",
        provider_user_id=str(otp["telegram_id"]),
        email=None,
        phone=phone,
        first_name=(profile["first_name"] if profile else None) or otp.get("first_name") or "Пользователь",
        last_name=(profile["last_name"] if profile else None) or otp.get("last_name") or "",
        avatar_url=None,
        role=payload.role,
    )


async def ensure_webhook() -> None:
    token = settings.telegram_bot_token.strip()
    if not token:
        return
    url = settings.public_base_url.rstrip("/") + "/api/v1/app/auth/telegram/webhook"
    payload = {"url": url}
    if settings.telegram_webhook_secret:
        payload["secret_token"] = settings.telegram_webhook_secret
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            await client.post(f"https://api.telegram.org/bot{token}/setWebhook", json=payload)
    except Exception:
        logger.warning("Failed to set Telegram webhook")


async def _poll_updates() -> None:
    token = settings.telegram_bot_token.strip()
    if not token:
        return
    offset = 0
    async with httpx.AsyncClient(timeout=40) as client:
        while True:
            try:
                response = await client.get(
                    f"https://api.telegram.org/bot{token}/getUpdates",
                    params={"timeout": 25, "offset": offset},
                )
                for update in response.json().get("result") or []:
                    offset = max(offset, int(update["update_id"]) + 1)
                    try:
                        await handle_webhook(update)
                    except Exception:
                        logger.exception("Telegram update failed")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.warning("Telegram polling failed")
                await asyncio.sleep(3)


async def start_telegram_listener() -> asyncio.Task | None:
    token = settings.telegram_bot_token.strip()
    if not token:
        return None
    if settings.public_base_url.startswith("https://"):
        await ensure_webhook()
        return None
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            await client.post(f"https://api.telegram.org/bot{token}/deleteWebhook")
    except Exception:
        logger.warning("Failed to delete Telegram webhook before polling")
    return asyncio.create_task(_poll_updates())
