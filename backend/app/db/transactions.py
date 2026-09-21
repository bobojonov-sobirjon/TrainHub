from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg

from app.db.pool import get_pool


@asynccontextmanager
async def transaction() -> AsyncIterator[asyncpg.Connection]:
    pool = get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            yield conn
