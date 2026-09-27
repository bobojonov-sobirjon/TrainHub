import uuid

import pytest
from httpx import AsyncClient


def _unique_email() -> str:
    return f"user_{uuid.uuid4().hex[:10]}@example.com"


@pytest.mark.asyncio
async def test_register_login_me_logout(client: AsyncClient) -> None:
    email = _unique_email()
    register = await client.post(
        "/api/v1/app/auth/register",
        json={
            "first_name": "Ivan",
            "last_name": "Petrov",
            "email": email,
            "password": "Password12",
            "role": "trainer",
        },
    )
    assert register.status_code == 201, register.text
    tokens = register.json()["data"]
    assert tokens["access_token"]
    assert tokens["user"]["roles"] == ["trainer"]

    me = await client.get(
        "/api/v1/app/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["data"]["email"] == email

    login = await client.post(
        "/api/v1/app/auth/login",
        json={"login": email, "password": "Password12"},
    )
    assert login.status_code == 200

    logout = await client.post(
        "/api/v1/app/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert logout.status_code == 204


@pytest.mark.asyncio
async def test_admin_login_rejected_for_trainer(client: AsyncClient) -> None:
    email = _unique_email()
    await client.post(
        "/api/v1/app/auth/register",
        json={
            "first_name": "Anna",
            "email": email,
            "password": "Password12",
            "role": "client",
        },
    )
    admin_login = await client.post(
        "/api/v1/admin/auth/login",
        json={"login": email, "password": "Password12"},
    )
    assert admin_login.status_code == 403
    assert admin_login.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_invalid_password(client: AsyncClient) -> None:
    email = _unique_email()
    await client.post(
        "/api/v1/app/auth/register",
        json={
            "first_name": "Oleg",
            "email": email,
            "password": "Password12",
            "role": "client",
        },
    )
    login = await client.post(
        "/api/v1/app/auth/login",
        json={"login": email, "password": "WrongPass1"},
    )
    assert login.status_code == 401
