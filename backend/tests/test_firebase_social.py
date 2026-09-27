import jwt
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch


def _firebase_jwt(*, provider: str, uid: str, email: str, name: str) -> str:
    return jwt.encode(
        {
            "iss": "https://securetoken.google.com/trainhub-75989",
            "aud": "trainhub-75989",
            "uid": uid,
            "sub": uid,
            "email": email,
            "name": name,
            "firebase": {
                "sign_in_provider": provider,
                "identities": {provider: [uid], "email": [email]},
            },
        },
        "test-secret",
        algorithm="HS256",
    )


@pytest.mark.asyncio
async def test_google_firebase_login_creates_user(client: AsyncClient) -> None:
    token = _firebase_jwt(
        provider="google.com",
        uid="google-uid-1",
        email="fb.google@example.com",
        name="Ivan Petrov",
    )
    claims = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
    with patch("app.services.social.verify_firebase_token", new=AsyncMock(return_value=claims)):
        response = await client.post(
            "/api/v1/app/auth/google",
            json={"id_token": token, "role": "client"},
        )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["access_token"]
    assert data["user"]["email"] == "fb.google@example.com"
    assert data["user"]["first_name"] == "Ivan"
    assert data["user"]["roles"] == ["client"]
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    created = await client.post(
        "/api/v1/app/me/devices",
        headers=headers,
        json={"platform": "android", "token": "fcm-test-token-12345678", "device_name": "Pixel"},
    )
    assert created.status_code == 200, created.text
    listed = await client.get("/api/v1/app/me/devices", headers=headers)
    assert "fcm-test-token-12345678" in [item["token"] for item in listed.json()["data"]]


@pytest.mark.asyncio
async def test_apple_firebase_login_creates_trainer(client: AsyncClient) -> None:
    token = _firebase_jwt(
        provider="apple.com",
        uid="apple-uid-1",
        email="fb.apple@example.com",
        name="Anna Smirnova",
    )
    claims = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
    with patch("app.services.social.verify_firebase_token", new=AsyncMock(return_value=claims)):
        response = await client.post(
            "/api/v1/app/auth/apple",
            json={"identity_token": token, "first_name": "Anna", "last_name": "Smirnova", "role": "trainer"},
        )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["user"]["roles"] == ["trainer"]
    assert data["user"]["email"] == "fb.apple@example.com"


@pytest.mark.asyncio
async def test_google_rejects_apple_firebase_token(client: AsyncClient) -> None:
    token = _firebase_jwt(
        provider="apple.com",
        uid="apple-uid-2",
        email="wrong@example.com",
        name="Wrong User",
    )
    claims = jwt.decode(token, options={"verify_signature": False, "verify_aud": False})
    with patch("app.services.social.verify_firebase_token", new=AsyncMock(return_value=claims)):
        response = await client.post(
            "/api/v1/app/auth/google",
            json={"id_token": token, "role": "client"},
        )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_TOKEN"
