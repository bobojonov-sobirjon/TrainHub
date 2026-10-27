"""Course weeks, moderation, catalog visibility, assignment."""

import uuid

import pytest
from httpx import AsyncClient

from app.core.constants import ROLE_ADMIN
from app.core.security import hash_password
from app.db.sql_loader import sql
from app.db.transactions import transaction


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


async def _register(client: AsyncClient, role: str) -> dict:
    response = await client.post(
        "/api/v1/app/auth/register",
        json={
            "first_name": "Course",
            "last_name": role.title(),
            "email": _email(role),
            "password": "Password12",
            "role": role,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _auth(tokens: dict) -> dict:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _admin_headers(client: AsyncClient) -> dict:
    email = _email("admin")
    password = "Password12"
    async with transaction() as conn:
        user = await conn.fetchrow(
            sql("auth/insert_user.sql"),
            email,
            None,
            hash_password(password),
            "Admin",
            "Course",
            None,
            None,
        )
        await conn.execute(sql("auth/insert_role.sql"), user["id"], ROLE_ADMIN)
    login = await client.post("/api/v1/admin/auth/login", json={"login": email, "password": password})
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


@pytest.mark.asyncio
async def test_course_week_duplicate_submit_and_catalog_visibility(client: AsyncClient) -> None:
    trainer = await _register(client, "trainer")
    person = await _register(client, "client")
    t = _auth(trainer)
    c = _auth(person)

    exercises = await client.get("/api/v1/app/exercises", headers=c)
    assert exercises.status_code == 200, exercises.text
    catalog = exercises.json()["data"]
    assert catalog
    exercise_id = catalog[0]["id"]

    created = await client.post(
        "/api/v1/app/programs",
        headers=t,
        json={"title": "Ноги 4 недели", "level": "intermediate", "status": "draft"},
    )
    assert created.status_code == 200, created.text
    program = created.json()["data"]
    program_id = program["id"]
    assert program["status"] == "draft"
    assert program["source"] == "trainer"

    # Draft must not appear in public catalog
    catalog_list = await client.get("/api/v1/app/programs", headers=c)
    assert catalog_list.status_code == 200
    ids = {item["id"] for item in catalog_list.json()["data"]["items"]}
    assert program_id not in ids

    week = await client.post(
        f"/api/v1/app/programs/{program_id}/weeks",
        headers=t,
        json={"title": "Неделя 1", "week_index": 1, "is_preview": True},
    )
    assert week.status_code == 200, week.text
    weeks = week.json()["data"]["weeks"]
    assert len(weeks) >= 1
    week_id = weeks[0]["id"]

    day = await client.post(
        f"/api/v1/app/programs/{program_id}/days",
        headers=t,
        json={"title": "День A", "duration_min": 45, "week_id": week_id},
    )
    assert day.status_code == 200, day.text
    day_id = next(d["id"] for d in day.json()["data"]["days"] if d.get("week_id") == week_id)

    added = await client.post(
        f"/api/v1/app/programs/{program_id}/days/{day_id}/exercises",
        headers=t,
        json={"exercise_id": exercise_id, "sets": 3, "reps_min": 8, "reps_max": 10, "rest_sec": 90},
    )
    assert added.status_code == 200, added.text

    dup = await client.post(
        f"/api/v1/app/programs/{program_id}/weeks/{week_id}/duplicate",
        headers=t,
    )
    assert dup.status_code == 200, dup.text
    weeks_after = dup.json()["data"]["weeks"]
    assert len(weeks_after) >= 2
    # Same exercise ids reused — count day exercises across weeks
    all_ex = [ex for w in weeks_after for d in w.get("days") or [] for ex in d.get("exercises") or []]
    assert len(all_ex) >= 2
    assert all(ex["exercise_id"] == exercise_id for ex in all_ex)

    submit = await client.post(f"/api/v1/app/programs/{program_id}/submit", headers=t)
    assert submit.status_code == 200, submit.text
    assert submit.json()["data"]["status"] == "pending_review"

    # Still hidden from catalog while pending
    catalog_list2 = await client.get("/api/v1/app/programs", headers=c)
    ids2 = {item["id"] for item in catalog_list2.json()["data"]["items"]}
    assert program_id not in ids2

    # Client cannot open draft/pending of another author
    blocked = await client.get(f"/api/v1/app/programs/{program_id}", headers=c)
    assert blocked.status_code == 404


@pytest.mark.asyncio
async def test_admin_approve_reject_and_assign(client: AsyncClient) -> None:
    trainer = await _register(client, "trainer")
    person = await _register(client, "client")
    t = _auth(trainer)
    c = _auth(person)
    admin = await _admin_headers(client)

    created = await client.post(
        "/api/v1/app/programs",
        headers=t,
        json={"title": "Персональный план", "status": "draft", "level": "beginner"},
    )
    assert created.status_code == 200
    program_id = created.json()["data"]["id"]

    day = await client.post(
        f"/api/v1/app/programs/{program_id}/days",
        headers=t,
        json={"title": "День 1"},
    )
    assert day.status_code == 200

    submit = await client.post(f"/api/v1/app/programs/{program_id}/submit", headers=t)
    assert submit.status_code == 200
    assert submit.json()["data"]["status"] == "pending_review"

    reject = await client.post(
        f"/api/v1/admin/programs/{program_id}/reject",
        headers=admin,
        json={"reason": "Добавьте описание и обложку"},
    )
    assert reject.status_code == 200, reject.text
    assert reject.json()["data"]["status"] == "rejected"
    assert "описание" in (reject.json()["data"].get("reject_reason") or "").lower()

    resubmit = await client.post(f"/api/v1/app/programs/{program_id}/submit", headers=t)
    assert resubmit.status_code == 200
    assert resubmit.json()["data"]["status"] == "pending_review"

    approve = await client.post(f"/api/v1/admin/programs/{program_id}/approve", headers=admin)
    assert approve.status_code == 200, approve.text
    assert approve.json()["data"]["status"] == "published"

    catalog_list = await client.get("/api/v1/app/programs", headers=c)
    ids = {item["id"] for item in catalog_list.json()["data"]["items"]}
    assert program_id in ids

    linked = await client.post(
        "/api/v1/app/trainer/clients",
        headers=t,
        json={"user_id": person["user"]["id"]},
    )
    assert linked.status_code == 200, linked.text
    link_id = linked.json()["data"]["id"]

    assigned = await client.post(
        f"/api/v1/app/programs/{program_id}/assign",
        headers=t,
        json={"link_id": link_id, "note": "старт"},
    )
    assert assigned.status_code == 200, assigned.text

    mine = await client.get("/api/v1/app/me/assigned-programs", headers=c)
    assert mine.status_code == 200, mine.text
    titles = {item.get("title") for item in mine.json()["data"]}
    assert "Персональный план" in titles
