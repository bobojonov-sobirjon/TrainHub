from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt

from app.core.constants import ROLE_ADMIN
from app.core.exceptions import AppError
from app.core.jwt import Audience, decode_token
from app.db.connection import fetchrow
from app.db.sql_loader import sql
from app.services.users import record_to_user
from app.schemas.common import UserPublic

bearer = HTTPBearer(auto_error=False)


async def _current_user(
    credentials: HTTPAuthorizationCredentials | None,
    audience: Audience,
) -> UserPublic:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("UNAUTHORIZED", "Требуется авторизация", http_status=401)
    try:
        payload = decode_token(credentials.credentials, audience=audience)
    except jwt.ExpiredSignatureError:
        raise AppError("TOKEN_EXPIRED", "Срок действия токена истёк", http_status=401) from None
    except Exception:
        raise AppError("INVALID_TOKEN", "Недействительный токен доступа", http_status=401) from None

    if payload.get("typ") != "access":
        raise AppError("INVALID_TOKEN", "Недействительный токен доступа", http_status=401)

    row = await fetchrow(sql("auth/get_user_by_id.sql"), int(payload["sub"]))
    if row is None:
        raise AppError("UNAUTHORIZED", "Требуется авторизация", http_status=401)
    if row["is_blocked"] or not row["is_active"]:
        raise AppError("USER_BLOCKED", "Аккаунт заблокирован", http_status=403)
    return record_to_user(row)


async def get_app_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> UserPublic:
    return await _current_user(credentials, "app")


async def get_admin_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> UserPublic:
    user = await _current_user(credentials, "admin")
    if ROLE_ADMIN not in user.roles:
        raise AppError("FORBIDDEN", "Требуются права администратора", http_status=403)
    return user
