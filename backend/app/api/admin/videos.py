from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.deps.auth import get_admin_user
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.pagination import Page, page_args
from app.schemas.videos import CategoryCreateIn, CategoryIn, TopicCreateIn, TopicIn, VideoRejectIn
from app.services import video_lessons as svc

router = APIRouter()


@router.get("/categories", tags=["Admin - Video lessons"], summary="Все категории видео")
async def categories(_user: Annotated[UserPublic, Depends(get_admin_user)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.list_categories(public=False))


@router.post("/categories", tags=["Admin - Video lessons"], summary="Создать категорию")
async def create_category(
    payload: CategoryCreateIn, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.create_category(payload))


@router.patch("/categories/{category_id}", tags=["Admin - Video lessons"], summary="Изменить категорию")
async def patch_category(
    category_id: int, payload: CategoryIn, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.update_category(category_id, payload))


@router.post("/categories/{category_id}/archive", tags=["Admin - Video lessons"], summary="Архивировать категорию")
async def archive_category(
    category_id: int, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.archive_category(category_id))


@router.get("/categories/{category_id}/topics", tags=["Admin - Video lessons"], summary="Темы категории")
async def topics(
    category_id: int, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.list_topics(category_id, public=False))


@router.post("/topics", tags=["Admin - Video lessons"], summary="Создать тему")
async def create_topic(
    payload: TopicCreateIn, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.create_topic(payload))


@router.patch("/topics/{topic_id}", tags=["Admin - Video lessons"], summary="Изменить тему")
async def patch_topic(
    topic_id: int, payload: TopicIn, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.update_topic(topic_id, payload))


@router.get("/videos", tags=["Admin - Video lessons"], summary="Все видеоуроки")
async def videos(
    _user: Annotated[UserPublic, Depends(get_admin_user)],
    status: str | None = None,
    source_type: str | None = None,
    category_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await svc.list_admin_videos(
        status=status,
        source_type=source_type,
        category_id=category_id,
        search=search,
        page_size=page_size,
        offset=offset,
    )
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.post("/videos", tags=["Admin - Video lessons"], summary="Создать общее видео")
async def create_video(
    user: Annotated[UserPublic, Depends(get_admin_user)],
    title: str = Form(...),
    category_id: int = Form(...),
    topic_id: int = Form(...),
    description: str | None = Form(None),
    level: str | None = Form(None),
    duration_seconds: int | None = Form(None),
    exercise_id: int | None = Form(None),
    exercise_name: str | None = Form(None),
    technique: str | None = Form(None),
    equipment: str | None = Form(None),
    muscles: str | None = Form(None),
    sets: int | None = Form(None),
    reps: int | None = Form(None),
    video_url: str | None = Form(None),
    publish: bool = Form(True),
    video: UploadFile | None = File(None),
    thumbnail: UploadFile | None = File(None),
) -> SuccessResponse[dict]:
    file_url, thumb_url = await svc.save_lesson_media("video-lessons/admin", video, thumbnail)
    data = await svc.create_video(
        actor_id=user.id,
        source_type="admin",
        trainer_id=None,
        title=title,
        description=description,
        category_id=category_id,
        topic_id=topic_id,
        level=level,
        duration_seconds=duration_seconds,
        exercise_id=exercise_id,
        exercise_details=svc.build_details(exercise_name, technique, equipment, muscles, sets, reps),
        video_url=file_url or video_url,
        thumbnail_url=thumb_url,
        submit=False,
        publish=publish,
    )
    return SuccessResponse(data=data)


@router.get("/videos/{video_id}", tags=["Admin - Video lessons"], summary="Карточка видео")
async def video_detail(video_id: int, _user: Annotated[UserPublic, Depends(get_admin_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.get_video_row(video_id))


@router.patch("/videos/{video_id}", tags=["Admin - Video lessons"], summary="Изменить видео")
async def patch_video(
    video_id: int,
    user: Annotated[UserPublic, Depends(get_admin_user)],
    title: str | None = Form(None),
    description: str | None = Form(None),
    category_id: int | None = Form(None),
    topic_id: int | None = Form(None),
    level: str | None = Form(None),
    duration_seconds: int | None = Form(None),
    exercise_id: int | None = Form(None),
    exercise_name: str | None = Form(None),
    technique: str | None = Form(None),
    equipment: str | None = Form(None),
    muscles: str | None = Form(None),
    sets: int | None = Form(None),
    reps: int | None = Form(None),
    video_url: str | None = Form(None),
    video: UploadFile | None = File(None),
    thumbnail: UploadFile | None = File(None),
) -> SuccessResponse[dict]:
    file_url, thumb_url = await svc.save_lesson_media("video-lessons/admin", video, thumbnail)
    details = svc.build_details(exercise_name, technique, equipment, muscles, sets, reps)
    data = await svc.update_video(
        video_id,
        actor_id=user.id,
        as_admin=True,
        title=title,
        description=description,
        category_id=category_id,
        topic_id=topic_id,
        level=level,
        duration_seconds=duration_seconds,
        exercise_id=exercise_id,
        exercise_details=details or None,
        video_url=file_url or video_url,
        thumbnail_url=thumb_url,
    )
    return SuccessResponse(data=data)


@router.get("/videos/{video_id}/assignments", tags=["Admin - Video lessons"], summary="Все назначения видео")
async def video_assignments(
    video_id: int, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.list_video_assignments(video_id))


@router.post("/videos/{video_id}/approve", tags=["Admin - Video lessons"], summary="Одобрить видео")
async def approve(video_id: int, user: Annotated[UserPublic, Depends(get_admin_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.approve_video(user.id, video_id))


@router.post("/videos/{video_id}/reject", tags=["Admin - Video lessons"], summary="Отклонить видео")
async def reject(
    video_id: int, payload: VideoRejectIn, user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.reject_video(user.id, video_id, payload.reason))


@router.post("/videos/{video_id}/archive", tags=["Admin - Video lessons"], summary="Архивировать видео")
async def archive(video_id: int, user: Annotated[UserPublic, Depends(get_admin_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.archive_admin_video(user.id, video_id))
