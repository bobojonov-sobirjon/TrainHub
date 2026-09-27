import uuid

import pytest
from httpx import AsyncClient


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


async def _register(client: AsyncClient, role: str, first_name: str = "User") -> dict:
    response = await client.post(
        "/api/v1/app/auth/register",
        json={
            "first_name": first_name,
            "last_name": "Testov",
            "email": _email(role),
            "password": "Password12",
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest.mark.asyncio
async def test_patch_me_and_client_home_gaps(client: AsyncClient) -> None:
    person = await _register(client, "client", "Vadim")
    headers = _auth(person)

    patched = await client.patch(
        "/api/v1/app/me",
        headers=headers,
        json={"height_cm": "190.0", "weight_goal_kg": "75.0", "first_name": "Вадим"},
    )
    assert patched.status_code == 200, patched.text
    me = patched.json()["data"]
    assert me["first_name"] == "Вадим"
    assert float(me["height_cm"]) == 190.0
    assert float(me["weight_goal_kg"]) == 75.0

    measure = await client.post(
        "/api/v1/app/client/measurements",
        headers=headers,
        json={"weight_kg": "80.0", "arm_left_cm": "37.0", "arm_right_cm": "37.5"},
    )
    assert measure.status_code == 200, measure.text

    home = await client.get("/api/v1/app/client/home", headers=headers)
    assert home.status_code == 200, home.text
    body = home.json()["data"]
    assert body["weight_goal_kg"] is not None
    assert "streak" in body
    assert "unread_count" in body
    assert "trainer_notes" in body

    notes = await client.get("/api/v1/app/client/trainer-notes", headers=headers)
    assert notes.status_code == 200

    unread = await client.get("/api/v1/app/notifications/unread-count", headers=headers)
    assert unread.status_code == 200
    assert "unread_count" in unread.json()["data"]

    chart = await client.get("/api/v1/app/client/measurements/chart", headers=headers, params={"metric": "weight_kg"})
    assert chart.status_code == 200, chart.text
    assert chart.json()["data"]["metric"] == "weight_kg"


@pytest.mark.asyncio
async def test_coach_marketplace_and_billing_gaps(client: AsyncClient) -> None:
    trainer = await _register(client, "trainer", "Ivan")
    person = await _register(client, "client", "Anna")

    listed = await client.get("/api/v1/app/trainers", params={"q": "Ivan", "sort": "newest"})
    assert listed.status_code == 200, listed.text
    assert listed.json()["data"]["total"] >= 1

    trainer_id = trainer["user"]["id"]
    reviews = await client.get(f"/api/v1/app/trainers/{trainer_id}/reviews")
    assert reviews.status_code == 200

    created = await client.post(
        f"/api/v1/app/trainers/{trainer_id}/reviews",
        headers=_auth(person),
        json={"rating": "5.0", "text": "Отличный тренер"},
    )
    assert created.status_code == 200, created.text

    book = await client.post(f"/api/v1/app/trainers/{trainer_id}/bookmark", headers=_auth(person))
    assert book.status_code == 200, book.text

    card = await client.post(
        "/api/v1/app/me/payment-methods",
        headers=_auth(person),
        json={"brand": "visa", "last4": "4417", "is_default": True},
    )
    assert card.status_code == 200, card.text
    methods = await client.get("/api/v1/app/me/payment-methods", headers=_auth(person))
    assert methods.status_code == 200
    assert len(methods.json()["data"]) >= 1
