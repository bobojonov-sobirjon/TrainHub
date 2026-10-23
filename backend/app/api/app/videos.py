from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.deps.auth import get_app_user
from app.deps.roles import require_trainer
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.pagination import Page, page_args
from app.schemas.videos import AssignVideosIn
from app.services import video_lessons as svc

router = APIRouter()


def _pager(page: int, page_size: int, limit: int | None) -> tuple[int, int, int]:
    return page_args(page, limit or page_size)


@router.get("/categories", tags=["Shared - Video lessons"], summary="Категории видеоуроков")
async def categories(_user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.list_categories(public=True))


@router.get("/categories/{category_id}", tags=["Shared - Video lessons"], summary="Карточка категории")
async def category_detail(
    category_id: int, _user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.get_category(category_id, public=True))


@router.get(
    "/categories/{category_id}/topics",
    tags=["Shared - Video lessons"],
    summary="Темы категории",
)
async def category_topics(
    category_id: int, _user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.list_topics(category_id, public=True))


@router.get("/topics/{topic_id}/videos", tags=["Shared - Video lessons"], summary="Видео темы")
async def topic_videos(
    topic_id: int,
    _user: Annotated[UserPublic, Depends(get_app_user)],
    page: int = 1,
    page_size: int = 20,
    limit: int | None = None,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = _pager(page, page_size, limit)
    items, total = await svc.topic_videos(topic_id, page_size, offset)
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/videos", tags=["Shared - Video lessons"], summary="Каталог видеоуроков")
async def videos(
    _user: Annotated[UserPublic, Depends(get_app_user)],
    category_id: int | None = Query(default=None),
    topic_id: int | None = Query(default=None),
    trainer_id: int | None = Query(default=None),
    categoryId: int | None = None,
    topicId: int | None = None,
    trainerId: int | None = None,
    level: str | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
    limit: int | None = None,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = _pager(page, page_size, limit)
    items, total = await svc.list_public_videos(
        category_id=category_id or categoryId,
        topic_id=topic_id or topicId,
        trainer_id=trainer_id or trainerId,
        level=level,
        search=search,
        page_size=page_size,
        offset=offset,
    )
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/videos/{video_id}", tags=["Shared - Video lessons"], summary="Карточка видеоурока")
async def video_detail(
    video_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.public_video_detail(video_id, user.id, user.roles))


@router.get("/trainers/{trainer_id}/videos", tags=["Shared - Video lessons"], summary="Опубликованные видео тренера")
async def trainer_videos_public(
    trainer_id: int,
    _user: Annotated[UserPublic, Depends(get_app_user)],
    page: int = 1,
    page_size: int = 20,
    limit: int | None = None,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = _pager(page, page_size, limit)
    items, total = await svc.trainer_public_videos(trainer_id, page_size, offset)
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/trainer/videos", tags=["Coach - Videos"], summary="Мои видеоуроки")
async def my_videos(
    user: Annotated[UserPublic, Depends(require_trainer)],
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    limit: int | None = None,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = _pager(page, page_size, limit)
    items, total = await svc.list_trainer_videos(user.id, status, page_size, offset)
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.post("/trainer/videos", tags=["Coach - Videos"], summary="Создать видеоурок")
async def create_video(
    user: Annotated[UserPublic, Depends(require_trainer)],
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
    muscles: str | None = Form(None, description="Через запятую"),
    sets: int | None = Form(None),
    reps: int | None = Form(None),
    video_url: str | None = Form(None),
    submit: bool = Form(False),
    video: UploadFile | None = File(None),
    thumbnail: UploadFile | None = File(None),
) -> SuccessResponse[dict]:
    file_url, thumb_url = await svc.save_lesson_media(f"video-lessons/trainer/{user.id}", video, thumbnail)
    data = await svc.create_video(
        actor_id=user.id,
        source_type="trainer",
        trainer_id=user.id,
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
        submit=submit,
        publish=False,
    )
    return SuccessResponse(data=data)


@router.patch("/trainer/videos/{video_id}", tags=["Coach - Videos"], summary="Изменить своё видео")
async def patch_video(
    video_id: int,
    user: Annotated[UserPublic, Depends(require_trainer)],
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
    file_url, thumb_url = await svc.save_lesson_media(f"video-lessons/trainer/{user.id}", video, thumbnail)
    details = svc.build_details(exercise_name, technique, equipment, muscles, sets, reps)
    data = await svc.update_video(
        video_id,
        actor_id=user.id,
        as_admin=False,
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


@router.post("/trainer/videos/{video_id}/submit", tags=["Coach - Videos"], summary="Отправить на модерацию")
async def submit_video(
    video_id: int, user: Annotated[UserPublic, Depends(require_trainer)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.submit_video(user.id, video_id))


@router.delete("/trainer/videos/{video_id}", tags=["Coach - Videos"], summary="Архивировать своё видео")
async def delete_video(
    video_id: int, user: Annotated[UserPublic, Depends(require_trainer)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.archive_trainer_video(user.id, video_id))


@router.get(
    "/trainer/clients/{link_id}/videos",
    tags=["Coach - Videos"],
    summary="Видео, назначенные клиенту",
    description="`link_id` — id связи тренер–клиент, как в остальных `/trainer/clients/{link_id}`.",
)
async def client_videos(
    link_id: int, user: Annotated[UserPublic, Depends(require_trainer)]
) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.list_client_assignments(user.id, link_id))


@router.post(
    "/trainer/clients/{link_id}/videos",
    tags=["Coach - Videos"],
    summary="Назначить видео клиенту",
)
async def assign_videos(
    link_id: int,
    payload: AssignVideosIn,
    user: Annotated[UserPublic, Depends(require_trainer)],
) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.assign_videos(user.id, link_id, payload.video_ids))


@router.delete(
    "/trainer/clients/{link_id}/videos/{assignment_id}",
    tags=["Coach - Videos"],
    summary="Снять назначение видео",
)
async def revoke_assignment(
    link_id: int,
    assignment_id: int,
    user: Annotated[UserPublic, Depends(require_trainer)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.revoke_assignment(user.id, link_id, assignment_id))


@router.get("/me/assigned-videos", tags=["Client - Videos"], summary="Видео, назначенные мне")
async def my_assigned(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.my_assigned_videos(user.id))


@router.get("/me/assigned-videos/{assignment_id}", tags=["Client - Videos"], summary="Карточка назначения")
async def my_assignment(
    assignment_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.my_assignment(user.id, assignment_id))


@router.get("/me/videos/{video_id}", tags=["Client - Videos"], summary="Видео с проверкой доступа")
async def my_video(video_id: int, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.my_video(user.id, video_id, user.roles))
