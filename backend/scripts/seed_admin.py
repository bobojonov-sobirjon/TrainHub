import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.core.constants import ROLE_ADMIN
from app.core.security import hash_password
from app.db.connection import fetchrow
from app.db.pool import close_pool, create_pool
from app.db.sql_loader import sql
from app.db.transactions import transaction


async def seed_admin() -> None:
    await create_pool()
    existing = await fetchrow(sql("auth/get_user_by_email.sql"), settings.seed_admin_email)
    if existing:
        print(f"Admin already exists: {settings.seed_admin_email}")
        await close_pool()
        return

    password = hash_password(settings.seed_admin_password)
    async with transaction() as conn:
        user = await conn.fetchrow(
            sql("auth/insert_user.sql"),
            settings.seed_admin_email,
            None,
            password,
            "Admin",
            "TrainHub",
            None,
            None,
        )
        await conn.execute(sql("auth/insert_role.sql"), user["id"], ROLE_ADMIN)
    print(f"Seeded admin {settings.seed_admin_email}")
    await close_pool()


if __name__ == "__main__":
    asyncio.run(seed_admin())
