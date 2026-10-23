from pydantic import BaseModel, ConfigDict, Field


class CategoryIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"name": "Набор массы", "description": "Силовые уроки", "sort_order": 1, "is_active": True}]
        }
    )

    name: str | None = Field(default=None, min_length=1, max_length=120, description="Название категории")
    description: str | None = Field(default=None, max_length=2000)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class CategoryCreateIn(CategoryIn):
    name: str = Field(min_length=1, max_length=120, description="Название категории")


class TopicIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"category_id": 1, "name": "Грудные мышцы", "sort_order": 1}]}
    )

    category_id: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class TopicCreateIn(TopicIn):
    category_id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)


class VideoRejectIn(BaseModel):
    reason: str = Field(min_length=3, max_length=1000, description="Причина отклонения")


class AssignVideosIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"video_ids": [1, 2]}]})

    video_ids: list[int] = Field(min_length=1, description="Один или несколько id видеоуроков")
