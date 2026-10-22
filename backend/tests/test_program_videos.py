import uuid

import pytest
from httpx import AsyncClient


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


async def _register(client: AsyncClient, role: str) -> dict:
    response = await client.post(
        "/api/v1/app/auth/register",
        json={
            "first_name": "Anna",
            "last_name": "Video",
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
async def test_program_detail_includes_video_fields(client: AsyncClient) -> None:
    trainer = await _register(client, "trainer")
    person = await _register(client, "client")
    t_headers = _auth(trainer)
    c_headers = _auth(person)

    exercises = await client.get("/api/v1/app/exercises", headers=c_headers)
    assert exercises.status_code == 200, exercises.text
    catalog = exercises.json()["data"]
    assert catalog
    exercise_id = catalog[0]["id"]
    assert "video_url" in catalog[0]
    assert "has_video" in catalog[0]

    card = await client.get(f"/api/v1/app/exercises/{exercise_id}", headers=c_headers)
    assert card.status_code == 200, card.text
    assert "video_url" in card.json()["data"]
    assert card.json()["data"]["has_video"] is bool(card.json()["data"]["video_url"])

    created = await client.post(
        "/api/v1/app/programs",
        headers=t_headers,
        json={"title": "Видео тест", "level": "beginner", "status": "published", "is_pro": False},
    )
    assert created.status_code == 200, created.text
    program_id = created.json()["data"]["id"]

    day = await client.post(
        f"/api/v1/app/programs/{program_id}/days",
        headers=t_headers,
        json={"title": "День 1", "duration_min": 40},
    )
    assert day.status_code == 200, day.text
    day_id = next(item["id"] for item in day.json()["data"]["days"])

    added = await client.post(
        f"/api/v1/app/programs/{program_id}/days/{day_id}/exercises",
        headers=t_headers,
        json={"exercise_id": exercise_id, "sets": 3, "reps_min": 8, "reps_max": 10},
    )
    assert added.status_code == 200, added.text

    detail = await client.get(f"/api/v1/app/programs/{program_id}", headers=c_headers)
    assert detail.status_code == 200, detail.text
    days = detail.json()["data"]["days"]
    items = [ex for d in days for ex in d.get("exercises") or []]
    assert items
    first = items[0]
    assert first["exercise_id"] == exercise_id
    assert "video_url" in first
    assert first["has_video"] is bool(first["video_url"])
    assert "photo_url" in first
    assert "name" in first
