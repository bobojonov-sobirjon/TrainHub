import uuid

import pytest
from httpx import AsyncClient

from app.core.constants import ROLE_ADMIN
from app.core.security import hash_password
from app.db.sql_loader import sql
from app.db.transactions import transaction


def _email(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}@example.com"


async def _register(client: AsyncClient, role: str, first_name: str = "User") -> dict:
    response = await client.post(
        "/api/v1/app/auth/register",
        json={
            "first_name": first_name,
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
            "Video",
            None,
            None,
        )
        await conn.execute(sql("auth/insert_role.sql"), user["id"], ROLE_ADMIN)
    login = await client.post("/api/v1/admin/auth/login", json={"login": email, "password": password})
    assert login.status_code == 200, login.text
    return _auth(login.json()["data"])


async def _first_topic(client: AsyncClient, headers: dict) -> tuple[int, int]:
    cats = await client.get("/api/v1/app/categories", headers=headers)
    assert cats.status_code == 200, cats.text
    items = cats.json()["data"]
    assert items
    category_id = items[0]["id"]
    topics = await client.get(f"/api/v1/app/categories/{category_id}/topics", headers=headers)
    assert topics.status_code == 200, topics.text
    topic_id = topics.json()["data"][0]["id"]
    return category_id, topic_id


@pytest.mark.asyncio
async def test_video_lessons_catalog_assign_and_moderation(client: AsyncClient) -> None:
    trainer = await _register(client, "trainer", "Alex")
    other = await _register(client, "trainer", "Daniel")
    person = await _register(client, "client", "Anna")
    stranger = await _register(client, "client", "Oleg")
    t_headers = _auth(trainer)
    o_headers = _auth(other)
    c_headers = _auth(person)
    s_headers = _auth(stranger)
    admin = await _admin_headers(client)

    category_id, topic_id = await _first_topic(client, c_headers)

    created_admin = await client.post(
        "/api/v1/admin/videos",
        headers=admin,
        data={
            "title": "Bench press техника",
            "description": "Общий урок",
            "category_id": str(category_id),
            "topic_id": str(topic_id),
            "level": "beginner",
            "video_url": "http://test/media/admin-bench.mp4",
            "duration_seconds": "180",
            "publish": "true",
        },
    )
    assert created_admin.status_code == 200, created_admin.text
    admin_video = created_admin.json()["data"]
    assert admin_video["status"] == "published"
    assert admin_video["source_type"] == "admin"
    assert admin_video["has_video"] is True

    draft = await client.post(
        "/api/v1/app/trainer/videos",
        headers=t_headers,
        data={
            "title": "Грудь от Alex",
            "category_id": str(category_id),
            "topic_id": str(topic_id),
            "level": "intermediate",
            "video_url": "http://test/media/alex-chest.mp4",
            "submit": "true",
        },
    )
    assert draft.status_code == 200, draft.text
    trainer_video = draft.json()["data"]
    assert trainer_video["status"] == "pending_review"
    assert trainer_video["trainer"]["id"] == trainer["user"]["id"]

    hidden = await client.get("/api/v1/app/videos", headers=c_headers)
    assert hidden.status_code == 200, hidden.text
    public_ids = {item["id"] for item in hidden.json()["data"]["items"]}
    assert admin_video["id"] in public_ids
    assert trainer_video["id"] not in public_ids

    reject = await client.post(
        f"/api/v1/admin/videos/{trainer_video['id']}/reject",
        headers=admin,
        json={"reason": "Плохое качество звука"},
    )
    assert reject.status_code == 200, reject.text
    assert reject.json()["data"]["status"] == "rejected"

    submit = await client.post(
        f"/api/v1/app/trainer/videos/{trainer_video['id']}/submit",
        headers=t_headers,
    )
    assert submit.status_code == 200, submit.text
    assert submit.json()["data"]["status"] == "pending_review"

    approve = await client.post(
        f"/api/v1/admin/videos/{trainer_video['id']}/approve",
        headers=admin,
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["data"]["status"] == "published"

    topic_list = await client.get(f"/api/v1/app/topics/{topic_id}/videos", headers=c_headers)
    assert topic_list.status_code == 200, topic_list.text
    topic_ids = {item["id"] for item in topic_list.json()["data"]["items"]}
    assert admin_video["id"] in topic_ids
    assert trainer_video["id"] in topic_ids

    linked = await client.post(
        "/api/v1/app/trainer/clients",
        headers=t_headers,
        json={"user_id": person["user"]["id"]},
    )
    assert linked.status_code == 200, linked.text
    link_id = linked.json()["data"]["id"]

    assigned = await client.post(
        f"/api/v1/app/trainer/clients/{link_id}/videos",
        headers=t_headers,
        json={"video_ids": [trainer_video["id"], admin_video["id"], admin_video["id"]]},
    )
    assert assigned.status_code == 200, assigned.text
    assert len(assigned.json()["data"]) == 2
    first_assignment = assigned.json()["data"][0]["id"]

    mine = await client.get("/api/v1/app/me/assigned-videos", headers=c_headers)
    assert mine.status_code == 200, mine.text
    assert len(mine.json()["data"]) == 2

    other_see = await client.get("/api/v1/app/me/assigned-videos", headers=s_headers)
    assert other_see.status_code == 200
    assert other_see.json()["data"] == []

    stolen = await client.get(f"/api/v1/app/me/assigned-videos/{first_assignment}", headers=s_headers)
    assert stolen.status_code == 404

    foreign_client = await client.post(
        "/api/v1/app/trainer/clients",
        headers=o_headers,
        json={"user_id": stranger["user"]["id"]},
    )
    assert foreign_client.status_code == 200, foreign_client.text
    other_link = foreign_client.json()["data"]["id"]

    steal_assign = await client.post(
        f"/api/v1/app/trainer/clients/{link_id}/videos",
        headers=o_headers,
        json={"video_ids": [trainer_video["id"]]},
    )
    assert steal_assign.status_code == 404

    steal_video = await client.post(
        f"/api/v1/app/trainer/clients/{other_link}/videos",
        headers=o_headers,
        json={"video_ids": [trainer_video["id"]]},
    )
    assert steal_video.status_code == 403

    revoke = await client.delete(
        f"/api/v1/app/trainer/clients/{link_id}/videos/{first_assignment}",
        headers=t_headers,
    )
    assert revoke.status_code == 200, revoke.text
    after = await client.get("/api/v1/app/me/assigned-videos", headers=c_headers)
    assert after.status_code == 200
    assert len(after.json()["data"]) == 1

    still_public = await client.get(f"/api/v1/app/videos/{admin_video['id']}", headers=c_headers)
    assert still_public.status_code == 200
    assert still_public.json()["data"]["id"] == admin_video["id"]

    archived = await client.delete(f"/api/v1/app/trainer/videos/{trainer_video['id']}", headers=t_headers)
    assert archived.status_code == 200
    assert archived.json()["data"]["status"] == "archived"

    gone = await client.get(f"/api/v1/app/videos/{trainer_video['id']}", headers=c_headers)
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_admin_category_and_duplicate_topic(client: AsyncClient) -> None:
    admin = await _admin_headers(client)
    created = await client.post(
        "/api/v1/admin/categories",
        headers=admin,
        json={"name": "Тестовая категория", "description": "Проверка"},
    )
    assert created.status_code == 200, created.text
    category_id = created.json()["data"]["id"]

    topic = await client.post(
        "/api/v1/admin/topics",
        headers=admin,
        json={"category_id": category_id, "name": "Новая тема"},
    )
    assert topic.status_code == 200, topic.text

    dup = await client.post(
        "/api/v1/admin/topics",
        headers=admin,
        json={"category_id": category_id, "name": "новая тема"},
    )
    assert dup.status_code == 409

    archived = await client.post(f"/api/v1/admin/categories/{category_id}/archive", headers=admin)
    assert archived.status_code == 200
    assert archived.json()["data"]["is_active"] is False
