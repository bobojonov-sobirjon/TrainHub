import asyncio
import logging
from pathlib import Path

from app.db.pool import close_pool, create_pool, get_pool

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


def _split_statements(script: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []
    for line in script.splitlines():
        stripped = line.strip()
        if stripped.startswith("--"):
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
    tail = "\n".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


async def apply_migrations() -> None:
    await create_pool()
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        rows = await conn.fetch("SELECT filename FROM schema_migrations")
        applied = {row["filename"] for row in rows}

        files = sorted(path for path in MIGRATIONS_DIR.glob("*.sql") if path.is_file())
        for file in files:
            if file.name in applied:
                continue
            script = file.read_text(encoding="utf-8")
            async with conn.transaction():
                for statement in _split_statements(script):
                    await conn.execute(statement)
                await conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($1)",
                    file.name,
                )
            logger.info("Applied migration %s", file.name)

    await close_pool()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(apply_migrations())
