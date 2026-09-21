from datetime import date
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: T


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_id: str
    email: str | None
    phone: str | None
    first_name: str
    last_name: str
    avatar_url: str | None = None
    gender: str | None = None
    birth_date: date | None = None
    roles: list[str] = Field(default_factory=list)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


class DictionaryItem(BaseModel):
    category: str
    code: str
    title_ru: str
    sort_order: int


class DictionariesData(BaseModel):
    items: list[DictionaryItem]
