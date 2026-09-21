from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import uuid4

import jwt

from app.core.config import settings

Audience = Literal["app", "admin"]
TokenType = Literal["access", "refresh"]


def _now() -> datetime:
    return datetime.now(UTC)


def create_token(
    *,
    user_id: int,
    roles: list[str],
    audience: Audience,
    token_type: TokenType,
    jti: str | None = None,
) -> tuple[str, str, datetime]:
    issued = _now()
    if token_type == "access":
        expires = issued + timedelta(minutes=settings.jwt_access_expire_minutes)
    else:
        expires = issued + timedelta(days=settings.jwt_refresh_expire_days)

    token_jti = jti or uuid4().hex
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "roles": roles,
        "aud": audience,
        "typ": token_type,
        "jti": token_jti,
        "iat": int(issued.timestamp()),
        "exp": int(expires.timestamp()),
    }
    encoded = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return encoded, token_jti, expires


def decode_token(token: str, audience: Audience) -> dict[str, Any]:
    return jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        audience=audience,
    )
