from fastapi import APIRouter

from app.db.connection import fetchrow

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Проверка работоспособности", description="Возвращает status=ok при доступной БД.")
async def health() -> dict:
    db_ok = False
    try:
        row = await fetchrow("SELECT 1 AS ok")
        db_ok = bool(row and row["ok"] == 1)
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "db": db_ok,
    }
