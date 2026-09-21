from functools import lru_cache
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"


@lru_cache
def sql(relative_path: str) -> str:
    path = SQL_DIR / relative_path
    if not path.is_file():
        raise FileNotFoundError(f"SQL file not found: {relative_path}")
    return path.read_text(encoding="utf-8").strip()
