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
async def test_stage3_clients_measurements_notes_stats_requests(client: AsyncClient) -> None:
    trainer = await _register(client, "trainer", "Trainer")
    person = await _register(client, "client", "Anna")
    trainer_id = trainer["user"]["id"]
    client_id = person["user"]["id"]

    manual = await client.post(
        "/api/v1/app/trainer/clients/manual",
        headers=_auth(trainer),
        json={
            "first_name": "Shadow",
            "last_name": "Client",
            "phone": f"+7900{uuid.uuid4().int % 10_000_000:07d}",
            "gender": "female",
            "goals": ["lose_weight"],
            "training_format": "gym",
            "measurements": {"weight_kg": "62.0", "waist_cm": "70.0"},
            "notes": ["Первая заметка"],
        },
    )
    assert manual.status_code == 200, manual.text
    link_id = manual.json()["data"]["id"]

    added = await client.post(
        "/api/v1/app/trainer/clients/{0}/measurements".format(link_id),
        headers=_auth(trainer),
        json={"weight_kg": "61.4", "waist_cm": "69.0"},
    )
    assert added.status_code == 200, added.text

    history = await client.get(
        f"/api/v1/app/trainer/clients/{link_id}/measurements",
        headers=_auth(trainer),
    )
    assert history.status_code == 200
    assert len(history.json()["data"]) >= 2

    chart = await client.get(
        f"/api/v1/app/trainer/clients/{link_id}/measurements/chart",
        headers=_auth(trainer),
        params={"metric": "weight_kg"},
    )
    assert chart.status_code == 200, chart.text
    body = chart.json()["data"]
    assert body["metric"] == "weight_kg"
    assert len(body["points"]) >= 2

    notes = await client.get(
        f"/api/v1/app/trainer/clients/{link_id}/notes",
        headers=_auth(trainer),
    )
    assert notes.status_code == 200
    assert notes.json()["data"]

    stats = await client.get(
        f"/api/v1/app/trainer/clients/{link_id}/stats",
        headers=_auth(trainer),
    )
    assert stats.status_code == 200
    assert stats.json()["data"]["measurements_count"] >= 2
    assert stats.json()["data"]["notes_count"] >= 1

    sessions = await client.get(
        f"/api/v1/app/trainer/clients/{link_id}/sessions",
        headers=_auth(trainer),
    )
    assert sessions.status_code == 200
    assert sessions.json()["data"]["items"] == []

    request = await client.post(
        f"/api/v1/app/trainers/{trainer_id}/request",
        headers=_auth(person),
    )
    assert request.status_code == 200, request.text
    request_id = request.json()["data"]["id"]

    pending = await client.get(
        "/api/v1/app/trainer/requests",
        headers=_auth(trainer),
    )
    assert pending.status_code == 200
    assert pending.json()["data"]["total"] >= 1
    assert pending.json()["data"]["items"][0]["client_id"] == client_id

    accepted = await client.post(
        f"/api/v1/app/trainer/requests/{request_id}/accept",
        headers=_auth(trainer),
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["data"]["status"] == "accepted"
    assert accepted.json()["data"]["trainer_client_id"]

    duplicate = await client.post(
        f"/api/v1/app/trainers/{trainer_id}/request",
        headers=_auth(person),
    )
    assert duplicate.status_code == 409
