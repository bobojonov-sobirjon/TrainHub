from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.auth import get_app_user
from app.deps.roles import require_client, require_trainer
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.pagination import Page, page_args
from app.schemas.stage import ReviewIn, TrainerProfileIn
from app.services import clients as client_svc
from app.services import trainers as svc

router = APIRouter()


@router.get("/trainer/profile", tags=["Coach - Profile"], summary="Профиль тренера")
async def profile(user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.get_profile(user.id))


@router.patch(
    "/trainer/profile",
    tags=["Coach - Profile"],
    summary="Обновить профиль тренера",
    description="Можно передать только нужные поля: био, опыт, специализации, форматы, цена, длительность.",
)
async def update_profile(
    payload: TrainerProfileIn,
    user: Annotated[UserPublic, Depends(require_trainer)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.update_profile(user.id, payload.model_dump(exclude_unset=True)))


@router.get("/trainer/dashboard", tags=["Coach - Dashboard"], summary="Дашборд тренера")
async def dashboard(user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.dashboard(user.id))


@router.get("/trainer/reports", tags=["Coach - Dashboard"], summary="Отчёт тренера")
async def reports(
    user: Annotated[UserPublic, Depends(require_trainer)],
    period: str = "month",
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.reports(user.id, period))


@router.get("/trainer/attention", tags=["Coach - Dashboard"], summary="Клиенты, требующие внимания")
async def attention(user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.attention_list(user.id))


@router.post(
    "/trainer/attention/{item_id}/resolve",
    tags=["Coach - Dashboard"],
    summary="Снять пункт внимания",
    description="Тело запроса не требуется. Помечает карточку внимания решённой.",
)
async def resolve(item_id: int, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    await svc.resolve_attention(user.id, item_id)
    return SuccessResponse(data={"ok": True})


@router.get("/trainers", tags=["Client - Catalog"], summary="Каталог тренеров")
async def trainers(
    category: str | None = None,
    q: str | None = None,
    sort: str = "rating",
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await svc.list_marketplace(category, page, page_size, offset, q=q, sort=sort)
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/trainers/{trainer_id}", tags=["Client - Catalog"], summary="Публичный профиль тренера")
async def trainer_detail(trainer_id: int) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.public_trainer(trainer_id))


@router.get("/trainers/{trainer_id}/reviews", tags=["Client - Catalog"], summary="Отзывы о тренере")
async def trainer_reviews(trainer_id: int) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.list_reviews(trainer_id))


@router.post(
    "/trainers/{trainer_id}/reviews",
    tags=["Client - Catalog"],
    summary="Оставить отзыв тренеру",
    description="Оценка 1–5. Повторный вызов обновляет отзыв клиента.",
)
async def create_review(
    trainer_id: int,
    payload: ReviewIn,
    user: Annotated[UserPublic, Depends(require_client)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.upsert_review(trainer_id, user.id, payload))


@router.get("/me/trainer-bookmarks", tags=["Client - Catalog"], summary="Сохранённые тренеры")
async def list_bookmarks(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.list_bookmarks(user.id))


@router.post(
    "/trainers/{trainer_id}/bookmark",
    tags=["Client - Catalog"],
    summary="Сохранить тренера",
    description="Тело запроса не требуется.",
)
async def bookmark_trainer(
    trainer_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    await svc.bookmark_trainer(user.id, trainer_id)
    return SuccessResponse(data={"ok": True})


@router.delete(
    "/trainers/{trainer_id}/bookmark",
    tags=["Client - Catalog"],
    summary="Убрать тренера из сохранённых",
    description="Тело запроса не требуется.",
)
async def unbookmark_trainer(
    trainer_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    await svc.unbookmark_trainer(user.id, trainer_id)
    return SuccessResponse(data={"ok": True})


@router.post(
    "/trainers/{trainer_id}/request",
    tags=["Client - Catalog"],
    summary="Отправить заявку тренеру",
    description="Тело запроса не требуется. Клиент отправляет заявку выбранному тренеру.",
)
async def request_trainer(
    trainer_id: int, user: Annotated[UserPublic, Depends(require_client)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await client_svc.create_request(user.id, trainer_id))


@router.get(
    "/trainer/requests",
    tags=["Coach - Clients"],
    summary="Заявки клиентов",
    description="Новые заявки на добавление к тренеру. По умолчанию статус `pending`.",
)
async def list_requests(
    user: Annotated[UserPublic, Depends(require_trainer)],
    status: str | None = "pending",
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await client_svc.list_requests(user.id, status, page_size, offset)
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.post(
    "/trainer/requests/{request_id}/accept",
    tags=["Coach - Clients"],
    summary="Принять заявку клиента",
    description="Тело запроса не требуется. Создаёт связь тренер–клиент (`invited_via=request`).",
)
async def accept_request(
    request_id: int, user: Annotated[UserPublic, Depends(require_trainer)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await client_svc.accept_request(user.id, request_id))


@router.post(
    "/trainer/requests/{request_id}/reject",
    tags=["Coach - Clients"],
    summary="Отклонить заявку клиента",
    description="Тело запроса не требуется.",
)
async def reject_request(
    request_id: int, user: Annotated[UserPublic, Depends(require_trainer)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await client_svc.reject_request(user.id, request_id))
