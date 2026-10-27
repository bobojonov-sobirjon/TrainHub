import re
from datetime import date

from asyncpg import Record
from asyncpg.exceptions import UniqueViolationError

from app.core.constants import ALLOWED_GENDERS
from app.core.exceptions import AppError
from app.db.connection import execute, fetchrow
from app.db.sql_loader import sql
from app.schemas.common import UserPublic
from app.schemas.stage import ProfilePatchIn
from app.services.storage import IMAGE_EXTENSIONS, save_bytes

_PHONE_RE = re.compile(r"^\+[1-9]\d{7,14}$")
# Telegram public username: 5–32 chars, starts with a letter.
_TG_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")


def _row_get(row: Record, key: str):
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


def _normalize_phone(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = raw.strip()
    if text == "":
        return ""
    digits = re.sub(r"\D", "", text)
    if not digits:
        raise AppError("VALIDATION_ERROR", "Некорректный телефон", http_status=422)
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if not digits.startswith("7") and len(digits) == 10:
        digits = "7" + digits
    value = f"+{digits}" if not text.startswith("+") else f"+{digits}"
    if digits.startswith("7"):
        value = f"+{digits}"
    else:
        value = f"+{digits}"
    if not _PHONE_RE.match(value):
        raise AppError("VALIDATION_ERROR", "Телефон должен быть в формате +79991234567", http_status=422)
    return value


def _normalize_whatsapp(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = raw.strip()
    if text == "":
        return ""
    return _normalize_phone(text)


def _normalize_telegram(raw: str | None) -> str | None:
    """Accept @username only (no phone). Empty clears the field."""
    if raw is None:
        return None
    text = raw.strip()
    if text == "":
        return ""
    if text.startswith("https://t.me/"):
        text = text.removeprefix("https://t.me/").split("?")[0].strip("/")
    elif text.startswith("t.me/"):
        text = text.removeprefix("t.me/").split("?")[0].strip("/")
    text = text.lstrip("@")
    if not _TG_RE.match(text):
        raise AppError(
            "VALIDATION_ERROR",
            "Telegram: укажите @username (например @nbekdev), без номера телефона",
            http_status=422,
        )
    return text


def record_to_user(row: Record) -> UserPublic:
    roles = list(row["roles"] or [])
    birth: date | None = row["birth_date"]
    return UserPublic(
        id=row["id"],
        public_id=row["public_id"],
        email=row["email"],
        phone=row["phone"],
        whatsapp=_row_get(row, "whatsapp"),
        telegram=_row_get(row, "telegram"),
        first_name=row["first_name"],
        last_name=row["last_name"],
        avatar_url=row["avatar_url"],
        gender=row["gender"],
        birth_date=birth,
        height_cm=_row_get(row, "height_cm"),
        weight_goal_kg=_row_get(row, "weight_goal_kg"),
        roles=roles,
    )


async def get_user_by_id(user_id: int) -> Record:
    row = await fetchrow(sql("auth/get_user_by_id.sql"), user_id)
    if row is None:
        raise AppError("USER_NOT_FOUND", "Пользователь не найден", http_status=404)
    return row


async def get_me(user_id: int) -> UserPublic:
    row = await fetchrow(sql("users/get_me.sql"), user_id)
    if row is None:
        raise AppError("USER_NOT_FOUND", "Пользователь не найден", http_status=404)
    return record_to_user(row)


async def patch_me(user_id: int, payload: ProfilePatchIn) -> UserPublic:
    data = payload.model_dump(exclude_unset=True)
    if "gender" in data and data["gender"] is not None and data["gender"] not in ALLOWED_GENDERS:
        raise AppError("VALIDATION_ERROR", "Некорректный пол", http_status=422)

    if "phone" in data:
        data["phone"] = _normalize_phone(data["phone"])
        if data["phone"] == "":
            raise AppError(
                "PHONE_REQUIRED",
                "Укажите телефон — тренер сможет с вами связаться",
                http_status=422,
            )
    if "whatsapp" in data:
        data["whatsapp"] = _normalize_whatsapp(data["whatsapp"])
    if "telegram" in data:
        data["telegram"] = _normalize_telegram(data["telegram"])

    # Empty string clears optional WA/TG; phone cannot be cleared.
    phone = data.get("phone")
    whatsapp = data.get("whatsapp")
    telegram = data.get("telegram")

    try:
        await execute(
            """
            UPDATE users
            SET
                first_name = COALESCE($2, first_name),
                last_name = COALESCE($3, last_name),
                phone = COALESCE($4, phone),
                whatsapp = CASE WHEN $5::boolean THEN $6 ELSE whatsapp END,
                telegram = CASE WHEN $7::boolean THEN $8 ELSE telegram END,
                gender = COALESCE($9, gender),
                birth_date = COALESCE($10, birth_date),
                height_cm = COALESCE($11, height_cm),
                weight_goal_kg = COALESCE($12, weight_goal_kg),
                updated_at = NOW()
            WHERE id = $1
            """,
            user_id,
            data.get("first_name"),
            data.get("last_name"),
            phone,
            "whatsapp" in data,
            whatsapp if whatsapp != "" else None,
            "telegram" in data,
            telegram if telegram != "" else None,
            data.get("gender"),
            data.get("birth_date"),
            data.get("height_cm"),
            data.get("weight_goal_kg"),
        )
    except UniqueViolationError as exc:
        raise AppError("PHONE_TAKEN", "Этот телефон уже используется", http_status=409) from exc
    return await get_me(user_id)


async def set_avatar(user_id: int, data: bytes, filename: str) -> UserPublic:
    url = await save_bytes(data, folder=f"avatars/{user_id}", filename=filename, allowed=IMAGE_EXTENSIONS)
    await execute("UPDATE users SET avatar_url = $2, updated_at = NOW() WHERE id = $1", user_id, url)
    return await get_me(user_id)


async def require_phone(user_id: int) -> str:
    row = await fetchrow("SELECT phone FROM users WHERE id = $1", user_id)
    phone = (row["phone"] if row else None) or ""
    phone = phone.strip()
    if not phone or not _PHONE_RE.match(phone):
        raise AppError(
            "PHONE_REQUIRED",
            "Укажите телефон в профиле — тренер сможет с вами связаться",
            http_status=422,
        )
    return phone
