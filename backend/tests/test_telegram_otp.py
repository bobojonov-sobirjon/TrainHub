import json

import pytest
from httpx import AsyncClient

from app.core.exceptions import AppError
from app.deps.redis import get_redis
from app.services.telegram_auth import normalize_phone, parse_identifier


def test_normalize_phone() -> None:
    assert normalize_phone("+7 900 123-45-67") == "+79001234567"
    assert normalize_phone("89001234567") == "+79001234567"
    assert normalize_phone("79001234567") == "+79001234567"
    with pytest.raises(AppError) as exc:
        normalize_phone("123")
    assert exc.value.code == "VALIDATION_ERROR"


def test_parse_identifier() -> None:
    assert parse_identifier("+998901234567") == ("phone", "+998901234567")
    assert parse_identifier("@john_doe") == ("username", "john_doe")
    assert parse_identifier("john_doe") == ("username", "john_doe")


@pytest.mark.asyncio
async def test_telegram_send_code_requires_bot_start(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/app/auth/telegram/send-code",
        json={"identifier": "+79001234567"},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["requires_bot_start"] is True
    assert data["sent"] is False
    assert "start=login_" in data["bot_url"]
    assert data["bot_username"] == "trainhub_bot"


@pytest.mark.asyncio
async def test_telegram_first_login_via_deeplink(client: AsyncClient) -> None:
    phone = "+79990001122"
    requested = await client.post(
        "/api/v1/app/auth/telegram/send-code",
        json={"identifier": phone},
    )
    assert requested.status_code == 200, requested.text
    bot_url = requested.json()["data"]["bot_url"]
    start_payload = bot_url.split("start=", 1)[1]
    webhook = await client.post(
        "/api/v1/app/auth/telegram/webhook",
        json={
            "message": {
                "chat": {"id": 555001},
                "from": {"id": 555001, "first_name": "Ivan", "username": "ivan_th"},
                "text": f"/start {start_payload}",
            }
        },
    )
    assert webhook.status_code == 200, webhook.text
    redis = await get_redis()
    raw = await redis.get(f"telegram_bot_otp:phone:{phone}")
    assert raw
    code = json.loads(raw)["code"]
    confirmed = await client.post(
        "/api/v1/app/auth/telegram/verify",
        json={"identifier": phone, "code": code, "role": "client"},
    )
    assert confirmed.status_code == 200, confirmed.text
    tokens = confirmed.json()["data"]
    assert tokens["access_token"]
    assert tokens["user"]["phone"] == phone


@pytest.mark.asyncio
async def test_telegram_plain_start_binds_pending(client: AsyncClient) -> None:
    phone = "+79993334455"
    requested = await client.post(
        "/api/v1/app/auth/telegram/send-code",
        json={"identifier": phone},
    )
    assert requested.status_code == 200, requested.text
    webhook = await client.post(
        "/api/v1/app/auth/telegram/webhook",
        json={
            "message": {
                "chat": {"id": 777001},
                "from": {"id": 777001, "first_name": "Ali", "username": "ali_th"},
                "text": "/start",
            }
        },
    )
    assert webhook.status_code == 200, webhook.text
    redis = await get_redis()
    raw = await redis.get(f"telegram_bot_otp:phone:{phone}")
    assert raw
    data = json.loads(raw)
    assert data["telegram_id"] == 777001
    confirmed = await client.post(
        "/api/v1/app/auth/telegram/verify",
        json={"identifier": phone, "code": data["code"], "role": "client"},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["data"]["user"]["phone"] == phone


@pytest.mark.asyncio
async def test_telegram_verify_before_bot_start(client: AsyncClient) -> None:
    phone = "+79001230001"
    requested = await client.post(
        "/api/v1/app/auth/telegram/send-code",
        json={"identifier": phone},
    )
    assert requested.status_code == 200
    redis = await get_redis()
    raw = await redis.get(f"telegram_bot_otp:phone:{phone}")
    code = json.loads(raw)["code"]
    response = await client.post(
        "/api/v1/app/auth/telegram/verify",
        json={"identifier": phone, "code": code},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BOT_START_REQUIRED"


@pytest.mark.asyncio
async def test_telegram_verify_without_code(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/app/auth/telegram/verify",
        json={"identifier": "+79005550000", "code": "123456"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_CODE"


@pytest.mark.asyncio
async def test_telegram_openapi_tags(client: AsyncClient) -> None:
    spec = await client.get("/openapi.json")
    paths = spec.json()["paths"]
    assert paths["/api/v1/app/auth/google"]["post"]["tags"] == ["Shared - Auth Google"]
    assert paths["/api/v1/app/auth/apple"]["post"]["tags"] == ["Shared - Auth Apple"]
    assert paths["/api/v1/app/auth/telegram/send-code"]["post"]["tags"] == ["Shared - Auth Telegram"]
    assert paths["/api/v1/app/auth/telegram/verify"]["post"]["tags"] == ["Shared - Auth Telegram"]
    assert "/api/v1/app/auth/telegram/request" not in paths
    assert "/api/v1/app/auth/telegram/confirm" not in paths
