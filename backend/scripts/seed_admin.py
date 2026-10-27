import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.core.constants import ROLE_ADMIN
from app.core.security import hash_password
from app.db.connection import execute, fetchrow
from app.db.pool import close_pool, create_pool
from app.db.sql_loader import sql
from app.db.transactions import transaction


async def seed_admin() -> None:
    await create_pool()
    email = settings.seed_admin_email
    password = hash_password(settings.seed_admin_password)
    existing = await fetchrow(sql("auth/get_user_by_email.sql"), email)

    if existing:
        await execute(sql("auth/update_password.sql"), existing["id"], password)
        roles = set(existing["roles"] or [])
        if ROLE_ADMIN not in roles:
            await execute(sql("auth/insert_role.sql"), existing["id"], ROLE_ADMIN)
        print(f"Reset admin password for {email}")
        print(f"Login: {email}")
        print(f"Password: {settings.seed_admin_password}")
        await close_pool()
        return

    async with transaction() as conn:
        user = await conn.fetchrow(
            sql("auth/insert_user.sql"),
            email,
            None,
            password,
            "Admin",
            "TrainHub",
            None,
            None,
        )
        await conn.execute(sql("auth/insert_role.sql"), user["id"], ROLE_ADMIN)
    print(f"Seeded admin {email}")
    print(f"Login: {email}")
    print(f"Password: {settings.seed_admin_password}")
    await close_pool()


if __name__ == "__main__":
    asyncio.run(seed_admin())
