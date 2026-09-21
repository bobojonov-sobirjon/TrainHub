import os
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_DEBUG", "true")
os.environ.setdefault("JWT_SECRET", "test-secret-not-for-production")

from app.db.migrate import apply_migrations
from app.db.pool import close_pool, create_pool
from app.deps.redis import close_redis
from app.main import create_app


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    await apply_migrations()
    await create_pool()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    await close_redis()
    await close_pool()
