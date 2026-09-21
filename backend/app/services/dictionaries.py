from app.db.connection import fetch
from app.db.sql_loader import sql
from app.schemas.common import DictionariesData, DictionaryItem


async def list_dictionaries() -> DictionariesData:
    rows = await fetch(sql("dictionaries/list_all.sql"))
    items = [
        DictionaryItem(
            category=row["category"],
            code=row["code"],
            title_ru=row["title_ru"],
            sort_order=row["sort_order"],
        )
        for row in rows
    ]
    return DictionariesData(items=items)
