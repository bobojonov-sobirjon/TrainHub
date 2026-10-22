import uuid

import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.services import robokassa


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


async def _register(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/v1/app/auth/register",
        json={
            "first_name": "Vadim",
            "last_name": "Pay",
            "email": _email("pay"),
            "password": "Password12",
            "role": "trainer",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _enable_test_merchant(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "robokassa_merchant_login", "TrainHub")
    monkeypatch.setattr(settings, "robokassa_test_password1", "testPassOne")
    monkeypatch.setattr(settings, "robokassa_test_password2", "testPassTwo")
    monkeypatch.setattr(settings, "robokassa_password1", "")
    monkeypatch.setattr(settings, "robokassa_password2", "")
    monkeypatch.setattr(settings, "robokassa_is_test", True)
    monkeypatch.setattr(settings, "robokassa_hash_alg", "md5")


def test_signature_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_test_merchant(monkeypatch)
    out_sum = "999.00"
    inv_id = 42
    result_sign = robokassa.sign_result(out_sum, inv_id)
    success_sign = robokassa.sign_success(out_sum, inv_id)
    payment_sign = robokassa.sign_payment(out_sum, inv_id)
    assert robokassa.verify_result(out_sum, inv_id, result_sign)
    assert robokassa.verify_success(out_sum, inv_id, success_sign)
    assert payment_sign != success_sign
    assert not robokassa.verify_result(out_sum, inv_id, "00" * 16)
    url = robokassa.payment_url(out_sum=out_sum, inv_id=inv_id, description="TrainHub PRO")
    assert "IsTest=1" in url
    assert "MerchantLogin=TrainHub" in url
    assert "SignatureValue=" in url


@pytest.mark.asyncio
async def test_checkout_webhook_activates_pro(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    _enable_test_merchant(monkeypatch)
    person = await _register(client)
    headers = {"Authorization": f"Bearer {person['access_token']}"}

    plans = await client.get("/api/v1/app/plans", params={"audience": "pro_trainer"})
    assert plans.status_code == 200, plans.text
    month = next(item for item in plans.json()["data"] if item["period"] == "month")
    assert float(month["price_amount"]) == 999

    checkout = await client.post(
        "/api/v1/app/me/subscription/checkout",
        headers=headers,
        json={"plan_id": month["id"]},
    )
    assert checkout.status_code == 200, checkout.text
    data = checkout.json()["data"]
    assert data["provider"] == "robokassa"
    assert data["status"] == "pending"
    assert data["payment_url"]
    assert "auth.robokassa.ru" in data["payment_url"]
    inv_id = data["inv_id"]
    out_sum = data["amount"]

    before = await client.get("/api/v1/app/me/subscription", headers=headers)
    assert before.json()["data"] is None

    bad = await client.post(
        "/api/v1/app/webhooks/payments/robokassa",
        data={"OutSum": out_sum, "InvId": str(inv_id), "SignatureValue": "deadbeef" * 4},
    )
    assert bad.status_code == 200
    assert bad.text == "bad sign"
    still = await client.get("/api/v1/app/me/subscription", headers=headers)
    assert still.json()["data"] is None

    signature = robokassa.sign_result(out_sum, inv_id)
    paid = await client.post(
        "/api/v1/app/webhooks/payments/robokassa",
        data={"OutSum": out_sum, "InvId": str(inv_id), "SignatureValue": signature},
    )
    assert paid.status_code == 200
    assert paid.text == f"OK{inv_id}"
    assert paid.headers["content-type"].startswith("text/plain")

    sub = await client.get("/api/v1/app/me/subscription", headers=headers)
    body = sub.json()["data"]
    assert body is not None
    assert body["status"] == "active"

    again = await client.get(
        "/api/v1/app/webhooks/payments/robokassa",
        params={"OutSum": out_sum, "InvId": str(inv_id), "SignatureValue": signature},
    )
    assert again.text == f"OK{inv_id}"

    success = await client.get("/pay/success", params={"InvId": str(inv_id)})
    assert success.status_code == 200
    assert "Платёж отправлен" in success.text

    fail = await client.get("/pay/fail", params={"InvId": "999999"})
    assert fail.status_code == 200
    assert "Оплата не завершена" in fail.text


@pytest.mark.asyncio
async def test_mock_checkout_without_merchant(client: AsyncClient) -> None:
    person = await _register(client)
    headers = {"Authorization": f"Bearer {person['access_token']}"}
    plans = await client.get("/api/v1/app/plans", params={"audience": "pro_client"})
    month = next(item for item in plans.json()["data"] if item["period"] == "month")
    checkout = await client.post(
        "/api/v1/app/me/subscription/checkout",
        headers=headers,
        json={"plan_id": month["id"]},
    )
    assert checkout.status_code == 200, checkout.text
    data = checkout.json()["data"]
    assert data["provider"] == "mock"
    assert data["status"] == "active"
    assert data["payment_url"] is None
