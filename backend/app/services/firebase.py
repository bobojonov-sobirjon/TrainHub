import asyncio
import logging

from app.core.config import settings
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)

_initialized = False


def _normalize_private_key(raw: str) -> str:
    key = raw.strip().strip('"').strip("'").replace("\\n", "\n")
    key = key.replace("----END PRIVATE KEY-----", "-----END PRIVATE KEY-----")
    key = key.replace("----BEGIN PRIVATE KEY-----", "-----BEGIN PRIVATE KEY-----")
    return key


def is_configured() -> bool:
    return bool(settings.firebase_project_id.strip() and settings.firebase_private_key.strip())


def init_firebase() -> bool:
    global _initialized
    if _initialized:
        return True
    if not is_configured():
        logger.warning("Firebase is not configured — social verify and FCM are off")
        return False
    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._apps:
        _initialized = True
        return True
    cred = credentials.Certificate(
        {
            "type": settings.firebase_type or "service_account",
            "project_id": settings.firebase_project_id,
            "private_key_id": settings.firebase_private_key_id,
            "private_key": _normalize_private_key(settings.firebase_private_key),
            "client_email": settings.firebase_client_email,
            "client_id": settings.firebase_client_id,
            "auth_uri": settings.firebase_auth_uri,
            "token_uri": settings.firebase_token_uri,
            "auth_provider_x509_cert_url": settings.firebase_auth_provider_x509_cert_url,
            "client_x509_cert_url": settings.firebase_client_x509_cert_url,
            "universe_domain": settings.firebase_universe_domain,
        }
    )
    try:
        firebase_admin.initialize_app(cred)
    except Exception as exc:
        logger.exception("Firebase Admin init failed: %s", exc)
        return False
    _initialized = True
    logger.info("Firebase Admin initialized for project %s", settings.firebase_project_id)
    return True


async def verify_id_token(id_token: str) -> dict:
    if not init_firebase():
        raise AppError("FIREBASE_NOT_CONFIGURED", "Firebase не настроен", http_status=503)
    from firebase_admin import auth as fb_auth

    try:
        return await asyncio.to_thread(fb_auth.verify_id_token, id_token)
    except Exception as exc:
        logger.info("Firebase ID token rejected: %s", exc)
        raise AppError("INVALID_TOKEN", "Firebase ID token недействителен", http_status=401) from None


def _data_payload(payload: dict | None) -> dict[str, str]:
    data = payload or {}
    return {str(key): str(value) for key, value in data.items() if value is not None}


async def send_push(tokens: list[str], title: str, body: str, data: dict | None = None) -> list[str]:
    """Send FCM to device tokens. Returns tokens that must be dropped."""
    if not tokens or not init_firebase():
        return []
    from firebase_admin import messaging

    messages = [
        messaging.Message(
            token=token,
            notification=messaging.Notification(title=title, body=body),
            data=_data_payload(data),
            android=messaging.AndroidConfig(priority="high"),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(aps=messaging.Aps(sound="default", badge=1)),
            ),
        )
        for token in tokens
    ]
    try:
        response = await asyncio.to_thread(messaging.send_each, messages)
    except Exception as exc:
        logger.exception("FCM send failed: %s", exc)
        return []
    stale: list[str] = []
    for token, item in zip(tokens, response.responses, strict=False):
        if item.success:
            continue
        error = item.exception
        name = type(error).__name__ if error else ""
        message_text = str(error or "")
        if name in {"UnregisteredError", "SenderIdMismatchError"} or "not a valid FCM" in message_text:
            stale.append(token)
        else:
            logger.info("FCM token failed (%s): %s", name, message_text)
    return stale
