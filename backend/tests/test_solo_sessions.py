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
async def test_client_trains_without_trainer(client: AsyncClient) -> None:
    person = await _register(client, "client", "Anna")
    headers = _auth(person)
    other = await _register(client, "client", "Petr")

    home = await client.get("/api/v1/app/client/home", headers=headers)
    assert home.status_code == 200, home.text
    body = home.json()["data"]
    assert body["can_train_solo"] is True
    assert body["has_trainer"] is False

    exercises = await client.get("/api/v1/app/exercises", headers=headers)
    assert exercises.status_code == 200
    exercise_id = exercises.json()["data"][0]["id"]

    started = await client.post(
        "/api/v1/app/sessions",
        headers=headers,
        json={"source": "new", "kinds": ["strength"], "client_ids": [other["user"]["id"]]},
    )
    assert started.status_code == 200, started.text
    session = started.json()["data"]
    assert session["trainer_id"] is None
    assert session["lead_client_id"] == person["user"]["id"]
    session_id = session["id"]

    added = await client.post(
        f"/api/v1/app/sessions/{session_id}/exercises",
        headers=headers,
        json={"exercise_id": exercise_id, "rest_sec": 90},
    )
    assert added.status_code == 200, added.text
    se_id = added.json()["data"]["added_exercise_id"]

    first_set = await client.post(
        f"/api/v1/app/sessions/{session_id}/exercises/{se_id}/sets",
        headers=headers,
        json={"weight_kg": "40.0", "reps": 10, "is_warmup": False},
    )
    assert first_set.status_code == 200, first_set.text

    done = await client.post(f"/api/v1/app/sessions/{session_id}/complete", headers=headers)
    assert done.status_code == 200, done.text
    assert done.json()["data"]["status"] == "completed"

    second = await client.post(
        "/api/v1/app/sessions",
        headers=headers,
        json={"source": "new", "kinds": ["strength"]},
    )
    assert second.status_code == 200
    sid2 = second.json()["data"]["id"]
    added2 = await client.post(
        f"/api/v1/app/sessions/{sid2}/exercises",
        headers=headers,
        json={"exercise_id": exercise_id},
    )
    se2 = added2.json()["data"]["added_exercise_id"]
    prev = await client.get(
        f"/api/v1/app/sessions/{sid2}/previous/{exercise_id}",
        headers=headers,
        params={"client_id": other["user"]["id"]},
    )
    assert prev.status_code == 200, prev.text
    last = prev.json()["data"]
    assert len(last) >= 1
    assert float(last[0]["weight_kg"]) == 40.0
    assert last[0]["reps"] == 10

    await client.post(
        f"/api/v1/app/sessions/{sid2}/exercises/{se2}/sets",
        headers=headers,
        json={"weight_kg": "45.0", "reps": 8, "is_warmup": False},
    )
    await client.post(f"/api/v1/app/sessions/{sid2}/complete", headers=headers)

    progress = await client.get("/api/v1/app/client/strength-progress", headers=headers)
    assert progress.status_code == 200, progress.text
    items = progress.json()["data"]
    row = next(item for item in items if item["exercise_id"] == exercise_id)
    assert float(row["last_weight_kg"]) == 45.0
    assert float(row["best_weight_kg"]) == 45.0
    assert row["sessions_count"] >= 2

    home2 = await client.get("/api/v1/app/client/home", headers=headers)
    assert home2.json()["data"]["last_session"] is not None
    assert home2.json()["data"]["strength_progress"]


@pytest.mark.asyncio
async def test_trainer_sees_client_solo_progress(client: AsyncClient) -> None:
    trainer = await _register(client, "trainer", "Ivan")
    person = await _register(client, "client", "Anna")
    exercises = await client.get("/api/v1/app/exercises", headers=_auth(person))
    exercise_id = exercises.json()["data"][0]["id"]

    started = await client.post(
        "/api/v1/app/sessions",
        headers=_auth(person),
        json={"source": "new", "kinds": ["strength"]},
    )
    session_id = started.json()["data"]["id"]
    added = await client.post(
        f"/api/v1/app/sessions/{session_id}/exercises",
        headers=_auth(person),
        json={"exercise_id": exercise_id},
    )
    se_id = added.json()["data"]["added_exercise_id"]
    await client.post(
        f"/api/v1/app/sessions/{session_id}/exercises/{se_id}/sets",
        headers=_auth(person),
        json={"weight_kg": "50.0", "reps": 6},
    )
    await client.post(f"/api/v1/app/sessions/{session_id}/complete", headers=_auth(person))

    linked = await client.post(
        "/api/v1/app/trainer/clients",
        headers=_auth(trainer),
        json={"user_id": person["user"]["id"]},
    )
    assert linked.status_code == 200, linked.text
    link_id = linked.json()["data"]["id"]

    progress = await client.get(
        f"/api/v1/app/trainer/clients/{link_id}/strength-progress",
        headers=_auth(trainer),
    )
    assert progress.status_code == 200, progress.text
    row = next(item for item in progress.json()["data"] if item["exercise_id"] == exercise_id)
    assert float(row["last_weight_kg"]) == 50.0

    opened = await client.get(f"/api/v1/app/sessions/{session_id}", headers=_auth(trainer))
    assert opened.status_code == 200, opened.text
    assert opened.json()["data"]["trainer_id"] is None
