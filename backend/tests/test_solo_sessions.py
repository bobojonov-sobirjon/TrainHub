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


@pytest.mark.asyncio
async def test_add_set_client_op_id_is_idempotent(client: AsyncClient) -> None:
    person = await _register(client, "client", "Idem")
    headers = _auth(person)
    exercises = await client.get("/api/v1/app/exercises", headers=headers)
    exercise_id = exercises.json()["data"][0]["id"]

    started = await client.post(
        "/api/v1/app/sessions",
        headers=headers,
        json={"source": "new", "kinds": ["strength"]},
    )
    session_id = started.json()["data"]["id"]
    added = await client.post(
        f"/api/v1/app/sessions/{session_id}/exercises",
        headers=headers,
        json={"exercise_id": exercise_id},
    )
    se_id = added.json()["data"]["added_exercise_id"]

    payload = {"weight_kg": "55.0", "reps": 7, "client_op_id": "op_test_same"}
    first = await client.post(
        f"/api/v1/app/sessions/{session_id}/exercises/{se_id}/sets",
        headers=headers,
        json=payload,
    )
    second = await client.post(
        f"/api/v1/app/sessions/{session_id}/exercises/{se_id}/sets",
        headers=headers,
        json=payload,
    )
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    sets = first.json()["data"]["exercises"][0]["sets"]
    sets2 = second.json()["data"]["exercises"][0]["sets"]
    assert len(sets) == 1
    assert len(sets2) == 1
    assert sets[0]["id"] == sets2[0]["id"]
    assert sets[0].get("completed_at") is not None

    # complete twice stays completed
    done1 = await client.post(f"/api/v1/app/sessions/{session_id}/complete", headers=headers)
    done2 = await client.post(f"/api/v1/app/sessions/{session_id}/complete", headers=headers)
    assert done1.status_code == 200
    assert done2.status_code == 200
    assert done2.json()["data"]["status"] == "completed"


@pytest.mark.asyncio
async def test_start_session_from_published_program_day(client: AsyncClient) -> None:
    from app.core.constants import ROLE_ADMIN
    from app.core.security import hash_password
    from app.db.sql_loader import sql
    from app.db.transactions import transaction
    import uuid as _uuid

    trainer = await _register(client, "trainer", "Coach")
    person = await _register(client, "client", "Athlete")
    t = _auth(trainer)
    c = _auth(person)

    exercises = await client.get("/api/v1/app/exercises", headers=c)
    exercise_id = exercises.json()["data"][0]["id"]

    created = await client.post(
        "/api/v1/app/programs",
        headers=t,
        json={"title": "Каталог день", "level": "beginner", "status": "draft"},
    )
    program_id = created.json()["data"]["id"]
    day = await client.post(
        f"/api/v1/app/programs/{program_id}/days",
        headers=t,
        json={"title": "День 1", "duration_min": 40},
    )
    day_id = day.json()["data"]["days"][0]["id"]
    await client.post(
        f"/api/v1/app/programs/{program_id}/days/{day_id}/exercises",
        headers=t,
        json={"exercise_id": exercise_id, "sets": 2, "reps_min": 8, "reps_max": 10},
    )
    await client.post(f"/api/v1/app/programs/{program_id}/submit", headers=t)

    email = f"admin_{_uuid.uuid4().hex[:8]}@example.com"
    async with transaction() as conn:
        user = await conn.fetchrow(
            sql("auth/insert_user.sql"),
            email,
            None,
            hash_password("Password12"),
            "Admin",
            "QA",
            None,
            None,
        )
        await conn.execute(sql("auth/insert_role.sql"), user["id"], ROLE_ADMIN)
    login = await client.post("/api/v1/admin/auth/login", json={"login": email, "password": "Password12"})
    admin = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    approve = await client.post(f"/api/v1/admin/programs/{program_id}/approve", headers=admin)
    assert approve.status_code == 200, approve.text

    started = await client.post(
        "/api/v1/app/sessions",
        headers=c,
        json={"source": "program", "kinds": ["strength"], "program_day_id": day_id},
    )
    assert started.status_code == 200, started.text
    data = started.json()["data"]
    assert data["program_day_id"] == day_id
    assert len(data["exercises"]) >= 1
    assert data["exercises"][0]["exercise_id"] == exercise_id
    # planned sets seeded, not yet completed
    assert len(data["exercises"][0]["sets"]) == 2
