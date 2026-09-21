from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def page_args(page: int = 1, page_size: int = 20) -> tuple[int, int, int]:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    offset = (page - 1) * page_size
    return page, page_size, offset


class IdResponse(BaseModel):
    id: int


class MessageResponse(BaseModel):
    message: str = Field(default="ok")
