from datetime import date

from asyncpg import Record

from app.core.exceptions import AppError
from app.db.connection import fetchrow
from app.db.sql_loader import sql
from app.schemas.common import UserPublic


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
