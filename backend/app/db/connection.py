from typing import Any

import asyncpg

from app.db.pool import get_pool


async def fetch(query: str, *args: Any) -> list[asyncpg.Record]:
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(query, *args)


async def fetchrow(query: str, *args: Any) -> asyncpg.Record | None:
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def execute(query: str, *args: Any) -> str:
    pool = get_pool()
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)
