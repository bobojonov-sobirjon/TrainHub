import uuid

import pytest
from httpx import AsyncClient

API = "/api/v1/app"


async def _register(client: AsyncClient, role: str, first_name: str) -> dict:
    response = await client.post(
        f"{API}/auth/register",
        json={
            "first_name": first_name,
            "last_name": "Testov",
            "email": f"{role}_{uuid.uuid4().hex[:10]}@example.com",
            "password": "Password12",
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _link(client: AsyncClient, trainer: dict, person: dict) -> int:
    linked = await client.post(f"{API}/trainer/clients", headers=_auth(trainer), json={"user_id": person["user"]["id"]})
    assert linked.status_code == 200, linked.text
    return linked.json()["data"]["id"]


async def _exercise_ids(client: AsyncClient, tokens: dict) -> list[int]:
    response = await client.get(f"{API}/exercises", headers=_auth(tokens))
    return [item["id"] for item in response.json()["data"]]


async def _add(client: AsyncClient, trainer: dict, session_id: int, exercise_id: int, client_id: int | None) -> int:
    body = {"exercise_id": exercise_id}
    if client_id is not None:
        body["client_id"] = client_id
    added = await client.post(f"{API}/sessions/{session_id}/exercises", headers=_auth(trainer), json=body)
    assert added.status_code == 200, added.text
    return added.json()["data"]["added_exercise_id"]


async def _set(client: AsyncClient, tokens: dict, session_id: int, se_id: int, weight: str, reps: int) -> None:
    response = await client.post(
        f"{API}/sessions/{session_id}/exercises/{se_id}/sets",
        headers=_auth(tokens),
        json={"weight_kg": weight, "reps": reps},
    )
    assert response.status_code == 200, response.text


@pytest.mark.asyncio
async def test_each_client_has_own_exercises_and_weights(client: AsyncClient) -> None:
    trainer = await _register(client, "trainer", "Coach")
    anna = await _register(client, "client", "Anna")
    petr = await _register(client, "client", "Petr")
    anna_id, petr_id = anna["user"]["id"], petr["user"]["id"]
    await _link(client, trainer, anna)
    await _link(client, trainer, petr)
    squat, bench = (await _exercise_ids(client, trainer))[:2]

    started = await client.post(
        f"{API}/sessions",
        headers=_auth(trainer),
        json={"source": "new", "kinds": ["strength"], "client_ids": [anna_id, petr_id]},
    )
    assert started.status_code == 200, started.text
    session_id = started.json()["data"]["id"]

    anna_squat = await _add(client, trainer, session_id, squat, anna_id)
    petr_bench = await _add(client, trainer, session_id, bench, petr_id)
    await _set(client, trainer, session_id, anna_squat, "60.0", 8)
    await _set(client, trainer, session_id, petr_bench, "100.0", 5)

    full = (await client.get(f"{API}/sessions/{session_id}", headers=_auth(trainer))).json()["data"]
    owners = {ex["id"]: ex["client_id"] for ex in full["exercises"]}
    assert owners == {anna_squat: anna_id, petr_bench: petr_id}

    only_petr = await client.get(f"{API}/sessions/{session_id}", headers=_auth(trainer), params={"client_id": petr_id})
    assert [ex["id"] for ex in only_petr.json()["data"]["exercises"]] == [petr_bench]
    assert only_petr.json()["data"]["sets_count"] == 1

    # A client sees only own exercises, even without the filter.
    as_anna = await client.get(f"{API}/sessions/{session_id}", headers=_auth(anna))
    assert [ex["id"] for ex in as_anna.json()["data"]["exercises"]] == [anna_squat]

    stranger = await _register(client, "client", "Olga")
    wrong = await client.post(
        f"{API}/sessions/{session_id}/exercises",
        headers=_auth(trainer),
        json={"exercise_id": squat, "client_id": stranger["user"]["id"]},
    )
    assert wrong.status_code == 400, wrong.text

    done = await client.post(f"{API}/sessions/{session_id}/complete", headers=_auth(trainer))
    assert done.status_code == 200, done.text

    # Next workout: previous results and progress are per client.
    nxt = await client.post(
        f"{API}/sessions",
        headers=_auth(trainer),
        json={"source": "new", "kinds": ["strength"], "client_ids": [anna_id, petr_id]},
    )
    sid2 = nxt.json()["data"]["id"]
    prev_anna = await client.get(f"{API}/sessions/{sid2}/previous/{squat}", headers=_auth(trainer), params={"client_id": anna_id})
    prev_petr = await client.get(f"{API}/sessions/{sid2}/previous/{squat}", headers=_auth(trainer), params={"client_id": petr_id})
    assert [float(s["weight_kg"]) for s in prev_anna.json()["data"]] == [60.0]
    assert prev_petr.json()["data"] == []

    progress = await client.get(f"{API}/client/strength-progress", headers=_auth(petr))
    assert {row["exercise_id"] for row in progress.json()["data"]} == {bench}

    history = await client.get(f"{API}/client/sessions", headers=_auth(anna))
    item = next(i for i in history.json()["data"]["items"] if i["id"] == session_id)
    assert item["exercises_count"] == 1
    assert item["sets_count"] == 1

    home = await client.get(f"{API}/client/home", headers=_auth(petr))
    assert home.status_code == 200, home.text


@pytest.mark.asyncio
async def test_program_day_is_copied_for_every_client(client: AsyncClient) -> None:
    trainer = await _register(client, "trainer", "Coach")
    anna = await _register(client, "client", "Anna")
    petr = await _register(client, "client", "Petr")
    anna_id, petr_id = anna["user"]["id"], petr["user"]["id"]
    await _link(client, trainer, anna)
    await _link(client, trainer, petr)
    exercise_id = (await _exercise_ids(client, trainer))[0]

    program = await client.post(f"{API}/programs", headers=_auth(trainer), json={"title": "План", "status": "draft"})
    program_id = program.json()["data"]["id"]
    day = await client.post(f"{API}/programs/{program_id}/days", headers=_auth(trainer), json={"title": "День 1"})
    day_id = day.json()["data"]["days"][0]["id"]
    await client.post(
        f"{API}/programs/{program_id}/days/{day_id}/exercises",
        headers=_auth(trainer),
        json={"exercise_id": exercise_id, "sets": 2, "reps_min": 8, "reps_max": 10},
    )

    started = await client.post(
        f"{API}/sessions",
        headers=_auth(trainer),
        json={"source": "program", "kinds": ["strength"], "program_day_id": day_id, "client_ids": [anna_id]},
    )
    assert started.status_code == 200, started.text
    session_id = started.json()["data"]["id"]
    assert [ex["client_id"] for ex in started.json()["data"]["exercises"]] == [anna_id]

    added = await client.post(
        f"{API}/sessions/{session_id}/clients", headers=_auth(trainer), json={"client_id": petr_id}
    )
    assert added.status_code == 200, added.text
    exercises = added.json()["data"]["exercises"]
    assert sorted(ex["client_id"] for ex in exercises) == sorted([anna_id, petr_id])
    assert all(len(ex["sets"]) == 2 for ex in exercises)


@pytest.mark.asyncio
async def test_solo_trainer_workout_goes_to_first_added_client(client: AsyncClient) -> None:
    trainer = await _register(client, "trainer", "Coach")
    anna = await _register(client, "client", "Anna")
    anna_id = anna["user"]["id"]
    await _link(client, trainer, anna)
    exercise_id = (await _exercise_ids(client, trainer))[0]

    started = await client.post(f"{API}/sessions", headers=_auth(trainer), json={"source": "new", "kinds": ["strength"]})
    session_id = started.json()["data"]["id"]
    se_id = await _add(client, trainer, session_id, exercise_id, None)

    added = await client.post(
        f"{API}/sessions/{session_id}/clients", headers=_auth(trainer), json={"client_id": anna_id}
    )
    assert added.status_code == 200, added.text
    assert [(ex["id"], ex["client_id"]) for ex in added.json()["data"]["exercises"]] == [(se_id, anna_id)]
