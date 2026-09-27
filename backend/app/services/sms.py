import logging
import re

import httpx

from app.core.config import settings
from app.core.exceptions import AppError

logger = logging.getLogger(__name__)
_eskiz_token: str | None = None


def _digits(phone: str) -> str:
    return re.sub(r"\D", "", phone)


async def send_otp(phone: str, code: str) -> None:
    text = f"Код входа в TrainHub: {code}. Действует 5 минут."
    if settings.telegram_gateway_token.strip():
        await _send_gateway(phone, code)
        return
    if settings.sms_eskiz_email.strip() and settings.sms_eskiz_password.strip():
        await _send_eskiz(phone, text)
        return
    if settings.app_debug and not settings.is_production:
        logger.info("SMS debug phone=%s code=%s", phone, code)
        return
    raise AppError("SMS_NOT_CONFIGURED", "SMS-шлюз не настроен", http_status=501)


async def _send_gateway(phone: str, code: str) -> None:
    token = settings.telegram_gateway_token.strip()
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.post(
            "https://gatewayapi.telegram.org/sendVerificationMessage",
            headers={"Authorization": f"Bearer {token}"},
            json={"phone_number": phone, "code": code, "ttl": 300},
        )
    data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    if response.status_code >= 400 or not data.get("ok"):
        logger.warning("Telegram Gateway failed: %s", response.text)
        raise AppError("SMS_SEND_FAILED", "Не удалось отправить SMS", http_status=502)


async def _eskiz_login() -> str:
    global _eskiz_token
    if _eskiz_token:
        return _eskiz_token
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.post(
            "https://notify.eskiz.uz/api/auth/login",
            json={
                "email": settings.sms_eskiz_email.strip(),
                "password": settings.sms_eskiz_password.strip(),
            },
        )
    data = response.json() if response.status_code < 500 else {}
    token = ((data.get("data") or {}).get("token")) if isinstance(data, dict) else None
    if not token:
        logger.warning("Eskiz login failed: %s", response.text)
        raise AppError("SMS_SEND_FAILED", "Не удалось отправить SMS", http_status=502)
    _eskiz_token = token
    return token


async def _send_eskiz(phone: str, text: str) -> None:
    global _eskiz_token
    token = await _eskiz_login()
    payload = {
        "mobile_phone": _digits(phone),
        "message": text,
        "from": settings.sms_eskiz_from.strip() or "4546",
    }
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.post(
            "https://notify.eskiz.uz/api/message/sms/send",
            headers={"Authorization": f"Bearer {token}"},
            data=payload,
        )
    if response.status_code == 401:
        _eskiz_token = None
        token = await _eskiz_login()
        async with httpx.AsyncClient(timeout=12) as client:
            response = await client.post(
                "https://notify.eskiz.uz/api/message/sms/send",
                headers={"Authorization": f"Bearer {token}"},
                data=payload,
            )
    data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
    status = str(data.get("status") or "").upper()
    if response.status_code >= 400 or status not in {"", "WAITING", "SUCCESS", "OK"}:
        logger.warning("Eskiz send failed: %s", response.text)
        raise AppError("SMS_SEND_FAILED", "Не удалось отправить SMS", http_status=502)
