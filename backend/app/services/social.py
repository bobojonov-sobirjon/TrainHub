import logging

import httpx
import jwt
from jwt import PyJWKClient

from app.core.config import settings
from app.core.constants import APP_ROLES, AUD_APP
from app.core.exceptions import AppError
from app.core.security import hash_password
from app.db.connection import execute, fetchrow
from app.db.sql_loader import sql
from app.db.transactions import transaction
from app.schemas.auth import AppleAuthIn, GoogleAuthIn
from app.schemas.common import TokenPair
from app.services.auth import _issue_tokens
from app.services.firebase import verify_id_token as verify_firebase_token
from app.services.users import get_user_by_id

logger = logging.getLogger(__name__)
APPLE_JWKS = PyJWKClient("https://appleid.apple.com/auth/keys")
FIREBASE_ISS_PREFIX = "https://securetoken.google.com/"


def _role_or_default(role: str) -> str:
    if role not in APP_ROLES:
        raise AppError("VALIDATION_ERROR", "Роль должна быть client или trainer", http_status=422)
    return role


async def _login_or_register(
    *,
    provider: str,
    provider_user_id: str,
    email: str | None,
    phone: str | None = None,
    first_name: str,
    last_name: str,
    avatar_url: str | None,
    role: str,
) -> TokenPair:
    role = _role_or_default(role)
    linked = await fetchrow(
        """
        SELECT user_id FROM user_identities
        WHERE provider = $1 AND provider_user_id = $2
        """,
        provider,
        provider_user_id,
    )
    if linked:
        user = await get_user_by_id(linked["user_id"])
        _assert_can_login_social(user)
        return await _issue_tokens(user, AUD_APP)

    existing = None
    if email:
        existing = await fetchrow(sql("auth/get_user_by_email.sql"), email)
    if existing is None and phone:
        existing = await fetchrow(sql("auth/get_user_by_phone.sql"), phone)
    if existing:
        await execute(
            """
            INSERT INTO user_identities (user_id, provider, provider_user_id, email)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (provider, provider_user_id) DO NOTHING
            """,
            existing["id"],
            provider,
            provider_user_id,
            email,
        )
        _assert_can_login_social(existing)
        return await _issue_tokens(existing, AUD_APP)

    async with transaction() as conn:
        user = await conn.fetchrow(
            sql("auth/insert_user.sql"),
            email,
            phone,
            hash_password(f"social-{provider}-{provider_user_id}"),
            first_name.strip() or "Пользователь",
            (last_name or "").strip(),
            None,
            None,
        )
        if avatar_url:
            await conn.execute("UPDATE users SET avatar_url = $2 WHERE id = $1", user["id"], avatar_url)
        await conn.execute(sql("auth/insert_role.sql"), user["id"], role)
        await conn.execute(
            """
            INSERT INTO user_identities (user_id, provider, provider_user_id, email)
            VALUES ($1, $2, $3, $4)
            """,
            user["id"],
            provider,
            provider_user_id,
            email,
        )
        await conn.execute(
            "INSERT INTO notification_preferences (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
            user["id"],
        )
    created = await get_user_by_id(user["id"])
    return await _issue_tokens(created, AUD_APP)


def _assert_can_login_social(row) -> None:
    if row["is_blocked"] or not row["is_active"]:
        raise AppError("USER_BLOCKED", "Аккаунт заблокирован", http_status=403)
    if row["is_shadow"]:
        raise AppError("SHADOW_USER", "Аккаунт не активирован", http_status=403)
    roles = set(row["roles"] or [])
    if roles.isdisjoint(APP_ROLES):
        raise AppError("FORBIDDEN", "Требуется доступ к приложению", http_status=403)


def _unverified_iss(token: str) -> str:
    try:
        claims = jwt.decode(token, options={"verify_signature": False, "verify_aud": False, "verify_exp": False})
    except Exception:
        return ""
    return str(claims.get("iss") or "")


def _is_firebase_token(token: str) -> bool:
    return _unverified_iss(token).startswith(FIREBASE_ISS_PREFIX)


def _names_from_claims(claims: dict, first_name: str | None = None, last_name: str | None = None) -> tuple[str, str]:
    if first_name and first_name.strip():
        return first_name.strip(), (last_name or "").strip()
    full = str(claims.get("name") or "").strip()
    parts = full.split(None, 1) if full else []
    given = str(claims.get("given_name") or (parts[0] if parts else "")).strip()
    family = str(claims.get("family_name") or (parts[1] if len(parts) > 1 else "")).strip()
    return given or "Пользователь", family


def _provider_uid(claims: dict, provider: str) -> str:
    identities = (claims.get("firebase") or {}).get("identities") or {}
    key = "google.com" if provider == "google" else "apple.com"
    values = identities.get(key) or []
    if values:
        return str(values[0])
    return str(claims.get("uid") or claims.get("sub") or "")


async def _claims_from_firebase(token: str, expected_provider: str) -> dict:
    claims = await verify_firebase_token(token)
    sign_in = str((claims.get("firebase") or {}).get("sign_in_provider") or "")
    expected = "google.com" if expected_provider == "google" else "apple.com"
    if sign_in and sign_in != expected:
        raise AppError("INVALID_TOKEN", f"Firebase token не от {expected_provider}", http_status=401)
    return claims


async def login_google(payload: GoogleAuthIn) -> TokenPair:
    if _is_firebase_token(payload.id_token):
        claims = await _claims_from_firebase(payload.id_token, "google")
        first_name, last_name = _names_from_claims(claims)
        sub = _provider_uid(claims, "google")
        if not sub:
            raise AppError("INVALID_TOKEN", "Firebase Google token недействителен", http_status=401)
        return await _login_or_register(
            provider="google",
            provider_user_id=sub,
            email=claims.get("email"),
            phone=claims.get("phone_number"),
            first_name=first_name,
            last_name=last_name,
            avatar_url=claims.get("picture"),
            role=payload.role,
        )

    async with httpx.AsyncClient(timeout=8) as client:
        response = await client.get(
            "https://oauth2.googleapis.com/tokeninfo",
            params={"id_token": payload.id_token},
        )
    if response.status_code != 200:
        raise AppError("INVALID_TOKEN", "Google ID token недействителен", http_status=401)
    data = response.json()
    audiences = settings.google_audiences
    if audiences and data.get("aud") not in audiences:
        raise AppError("INVALID_TOKEN", "Google client_id не совпадает", http_status=401)
    sub = str(data.get("sub") or "")
    email = data.get("email")
    if not sub:
        raise AppError("INVALID_TOKEN", "Google ID token недействителен", http_status=401)
    return await _login_or_register(
        provider="google",
        provider_user_id=sub,
        email=email,
        first_name=str(data.get("given_name") or data.get("name") or "Пользователь"),
        last_name=str(data.get("family_name") or ""),
        avatar_url=data.get("picture"),
        role=payload.role,
    )


async def login_apple(payload: AppleAuthIn) -> TokenPair:
    if _is_firebase_token(payload.identity_token):
        claims = await _claims_from_firebase(payload.identity_token, "apple")
        first_name, last_name = _names_from_claims(claims, payload.first_name, payload.last_name)
        sub = _provider_uid(claims, "apple")
        if not sub:
            raise AppError("INVALID_TOKEN", "Firebase Apple token недействителен", http_status=401)
        return await _login_or_register(
            provider="apple",
            provider_user_id=sub,
            email=claims.get("email"),
            first_name=first_name,
            last_name=last_name,
            avatar_url=None,
            role=payload.role,
        )

    try:
        key = APPLE_JWKS.get_signing_key_from_jwt(payload.identity_token)
        decode_kwargs: dict = {
            "algorithms": ["RS256"],
            "issuer": "https://appleid.apple.com",
            "options": {"verify_aud": bool(settings.apple_audiences)},
        }
        if settings.apple_audiences:
            decode_kwargs["audience"] = settings.apple_audiences
        decoded = jwt.decode(payload.identity_token, key.key, **decode_kwargs)
    except Exception as exc:
        logger.info("Apple token rejected: %s", exc)
        raise AppError("INVALID_TOKEN", "Apple identity token недействителен", http_status=401) from None
    sub = str(decoded.get("sub") or "")
    if not sub:
        raise AppError("INVALID_TOKEN", "Apple identity token недействителен", http_status=401)
    email = decoded.get("email")
    return await _login_or_register(
        provider="apple",
        provider_user_id=sub,
        email=email,
        first_name=(payload.first_name or "Пользователь").strip(),
        last_name=(payload.last_name or "").strip(),
        avatar_url=None,
        role=payload.role,
    )


