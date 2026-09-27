from datetime import date

from asyncpg import Record

from app.core.constants import ALLOWED_GENDERS
from app.core.exceptions import AppError
from app.db.connection import execute, fetchrow
from app.db.sql_loader import sql
from app.schemas.common import UserPublic
from app.schemas.stage import ProfilePatchIn
from app.services.storage import IMAGE_EXTENSIONS, save_bytes


def _row_get(row: Record, key: str):
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


def record_to_user(row: Record) -> UserPublic:
    roles = list(row["roles"] or [])
    birth: date | None = row["birth_date"]
    return UserPublic(
        id=row["id"],
        public_id=row["public_id"],
        email=row["email"],
        phone=row["phone"],
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
    await execute(
        """
        UPDATE users
        SET
            first_name = COALESCE($2, first_name),
            last_name = COALESCE($3, last_name),
            gender = COALESCE($4, gender),
            birth_date = COALESCE($5, birth_date),
            height_cm = COALESCE($6, height_cm),
            weight_goal_kg = COALESCE($7, weight_goal_kg),
            updated_at = NOW()
        WHERE id = $1
        """,
        user_id,
        data.get("first_name"),
        data.get("last_name"),
        data.get("gender"),
        data.get("birth_date"),
        data.get("height_cm"),
        data.get("weight_goal_kg"),
    )
    return await get_me(user_id)


async def set_avatar(user_id: int, data: bytes, filename: str) -> UserPublic:
    url = await save_bytes(data, folder=f"avatars/{user_id}", filename=filename, allowed=IMAGE_EXTENSIONS)
    await execute("UPDATE users SET avatar_url = $2, updated_at = NOW() WHERE id = $1", user_id, url)
    return await get_me(user_id)
