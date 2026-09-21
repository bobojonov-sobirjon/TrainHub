import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

import asyncpg
from app.core.config import settings
from app.core.constants import APP_ROLES, AUD_ADMIN, AUD_APP, ROLE_ADMIN
from app.core.exceptions import AppError
from app.core.jwt import Audience, create_token, decode_token
from app.core.security import hash_password, verify_password
from app.db.connection import execute, fetchrow
from app.db.sql_loader import sql
from app.db.transactions import transaction
from app.deps.redis import get_redis
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RegisterRequest,
)
from app.schemas.common import TokenPair, UserPublic
from app.services.users import get_user_by_id, record_to_user

logger = logging.getLogger(__name__)


def _is_email(value: str) -> bool:
    return "@" in value


async def _find_user_by_login(login: str) -> asyncpg.Record | None:
    if _is_email(login):
        return await fetchrow(sql("auth/get_user_by_email.sql"), login)
    return await fetchrow(sql("auth/get_user_by_phone.sql"), login)


def _assert_can_login(row: asyncpg.Record, audience: Audience) -> None:
    if row["is_blocked"] or not row["is_active"]:
        raise AppError("USER_BLOCKED", "Аккаунт заблокирован", http_status=403)
    if row["is_shadow"]:
        raise AppError("SHADOW_USER", "Аккаунт не активирован", http_status=403)
    if not row["password_hash"]:
        raise AppError("INVALID_CREDENTIALS", "Неверный логин или пароль", http_status=401)

    roles = set(row["roles"] or [])
    if audience == AUD_ADMIN and ROLE_ADMIN not in roles:
        raise AppError("FORBIDDEN", "Требуются права администратора", http_status=403)
    if audience == AUD_APP and roles.isdisjoint(APP_ROLES):
        raise AppError("FORBIDDEN", "Требуется доступ к приложению", http_status=403)


async def _issue_tokens(row: asyncpg.Record, audience: Audience) -> TokenPair:
    roles = list(row["roles"] or [])
    access, _, _ = create_token(
        user_id=row["id"],
        roles=roles,
        audience=audience,
        token_type="access",
    )
    refresh, jti, expires = create_token(
        user_id=row["id"],
        roles=roles,
        audience=audience,
        token_type="refresh",
    )
    await execute(sql("auth/insert_refresh.sql"), row["id"], jti, audience, expires)
    await execute(sql("auth/update_last_login.sql"), row["id"])
    return TokenPair(access_token=access, refresh_token=refresh, user=record_to_user(row))


async def register(payload: RegisterRequest) -> TokenPair:
    if payload.email:
        existing = await fetchrow(sql("auth/get_user_by_email.sql"), payload.email)
        if existing:
            raise AppError("EMAIL_TAKEN", "Этот email уже зарегистрирован", http_status=409)
    if payload.phone:
        existing = await fetchrow(sql("auth/get_user_by_phone.sql"), payload.phone)
        if existing:
            raise AppError("PHONE_TAKEN", "Этот телефон уже зарегистрирован", http_status=409)

    password = hash_password(payload.password)
    try:
        async with transaction() as conn:
            user = await conn.fetchrow(
                sql("auth/insert_user.sql"),
                payload.email,
                payload.phone,
                password,
                payload.first_name.strip(),
                payload.last_name.strip(),
                payload.gender,
                payload.birth_date,
            )
            await conn.execute(sql("auth/insert_role.sql"), user["id"], payload.role)
    except asyncpg.UniqueViolationError:
        raise AppError("USER_EXISTS", "Пользователь уже существует", http_status=409) from None

    created = await get_user_by_id(user["id"])
    return await _issue_tokens(created, AUD_APP)


async def login(payload: LoginRequest, audience: Audience) -> TokenPair:
    row = await _find_user_by_login(payload.login.strip())
    if row is None or not verify_password(payload.password, row["password_hash"] or ""):
        raise AppError("INVALID_CREDENTIALS", "Неверный логин или пароль", http_status=401)
    _assert_can_login(row, audience)
    return await _issue_tokens(row, audience)


async def refresh_tokens(refresh_token: str, audience: Audience) -> TokenPair:
    try:
        payload = decode_token(refresh_token, audience=audience)
    except Exception:
        raise AppError("INVALID_TOKEN", "Недействительный refresh-токен", http_status=401) from None

    if payload.get("typ") != "refresh":
        raise AppError("INVALID_TOKEN", "Недействительный refresh-токен", http_status=401)

    jti = payload["jti"]
    stored = await fetchrow(sql("auth/get_refresh.sql"), jti)
    if stored is None or stored["revoked_at"] is not None:
        raise AppError("INVALID_TOKEN", "Refresh-токен отозван", http_status=401)
    if stored["expires_at"] < datetime.now(UTC):
        raise AppError("INVALID_TOKEN", "Срок действия refresh-токена истёк", http_status=401)

    try:
        redis = await get_redis()
        if await redis.get(f"rt:revoked:{jti}"):
            raise AppError("INVALID_TOKEN", "Refresh-токен отозван", http_status=401)
    except AppError:
        raise
    except Exception:
        logger.warning("Redis unavailable during refresh check")

    await execute(sql("auth/revoke_refresh.sql"), jti)
    user = await get_user_by_id(int(payload["sub"]))
    _assert_can_login(user, audience)
    return await _issue_tokens(user, audience)


async def logout(refresh_token: str, audience: Audience) -> None:
    try:
        payload = decode_token(refresh_token, audience=audience)
        jti = payload["jti"]
    except Exception:
        return

    await execute(sql("auth/revoke_refresh.sql"), jti)
    try:
        redis = await get_redis()
        ttl_days = settings.jwt_refresh_expire_days * 86400
        await redis.set(f"rt:revoked:{jti}", "1", ex=ttl_days)
    except Exception:
        logger.warning("Redis unavailable during logout")


async def change_password(user_id: int, payload: ChangePasswordRequest) -> None:
    user = await get_user_by_id(user_id)
    if not verify_password(payload.old_password, user["password_hash"] or ""):
        raise AppError("INVALID_PASSWORD", "Текущий пароль неверный", http_status=400)
    await execute(sql("auth/update_password.sql"), user_id, hash_password(payload.new_password))


async def request_password_reset(payload: PasswordResetRequest) -> dict:
    row = await _find_user_by_login(payload.login.strip())
    response = {"accepted": True}
    if row is None or row["is_shadow"] or not row["password_hash"]:
        return response

    raw = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    expires = datetime.now(UTC) + timedelta(hours=2)
    await execute(sql("auth/insert_password_reset.sql"), row["id"], token_hash, expires)

    if settings.app_debug and not settings.is_production:
        response["debug_token"] = raw
    else:
        logger.info("Password reset requested for user_id=%s", row["id"])
    return response


async def confirm_password_reset(payload: PasswordResetConfirmRequest) -> None:
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    row = await fetchrow(sql("auth/get_password_reset.sql"), token_hash)
    if row is None or row["used_at"] is not None:
        raise AppError("INVALID_TOKEN", "Токен сброса пароля недействителен", http_status=400)
    if row["expires_at"] < datetime.now(UTC):
        raise AppError("INVALID_TOKEN", "Срок действия токена сброса пароля истёк", http_status=400)

    async with transaction() as conn:
        await conn.execute(sql("auth/update_password.sql"), row["user_id"], hash_password(payload.new_password))
        await conn.execute(sql("auth/mark_password_reset_used.sql"), row["id"])


def to_public(user: asyncpg.Record) -> UserPublic:
    return record_to_user(user)
