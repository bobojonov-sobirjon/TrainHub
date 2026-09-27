from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.deps.roles import require_trainer
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.pagination import Page, page_args
from app.schemas.stage import ClientAddIn, ClientManualIn, ClientNoteIn, ClientPatchIn, ClientSearchIn, MeasurementIn
from app.services import clients as svc

router = APIRouter(prefix="/trainer/clients")


@router.get("", tags=["Coach - Clients"], summary="Клиенты тренера")
async def list_clients(
    user: Annotated[UserPublic, Depends(require_trainer)],
    q: str | None = None,
    gender: str | None = None,
    format: str | None = None,
    status: str | None = None,
    sort: str = "newest",
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await svc.list_clients(
        user.id, q=q, gender=gender, format_=format, status=status, sort=sort, page=page, page_size=page_size, offset=offset
    )
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.post(
    "/search",
    tags=["Coach - Clients"],
    summary="Найти пользователя для добавления",
    description="Поиск по имени, email или телефону среди зарегистрированных клиентов.",
)
async def search(payload: ClientSearchIn, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.search_users(user.id, payload.query))


@router.post(
    "",
    tags=["Coach - Clients"],
    summary="Добавить существующего клиента",
    description="Привязывает уже зарегистрированного пользователя к тренеру по `user_id`.",
)
async def add(payload: ClientAddIn, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.add_existing(user.id, payload.user_id))


@router.post(
    "/manual",
    tags=["Coach - Clients"],
    summary="Создать теневого клиента",
    description="Создаёт клиента без входа в приложение. Можно сразу передать замеры, цели и противопоказания.",
)
async def manual(payload: ClientManualIn, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.add_manual(user.id, payload))


@router.get("/{link_id}", tags=["Coach - Clients"], summary="Карточка клиента")
async def detail(link_id: int, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.get_client(user.id, link_id))


@router.get(
    "/{link_id}/measurements",
    tags=["Coach - Clients"],
    summary="История замеров клиента",
)
async def list_measurements(
    link_id: int, user: Annotated[UserPublic, Depends(require_trainer)]
) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.list_measurements(user.id, link_id))


@router.get(
    "/{link_id}/measurements/chart",
    tags=["Coach - Clients"],
    summary="График замеров клиента",
    description=(
        "Метрика: `weight_kg`, `body_fat_pct`, `muscle_mass_kg`, `water_pct`, "
        "`chest_cm`, `back_cm`, `waist_cm`, `hips_cm`, `thigh_cm`, `calf_cm`, "
        "`neck_cm`, `shoulders_cm`, `arm_cm`, `forearm_cm`."
    ),
)
async def measurements_chart(
    link_id: int,
    user: Annotated[UserPublic, Depends(require_trainer)],
    metric: str = "weight_kg",
    date_from: date | None = Query(default=None, alias="from", description="Начало периода YYYY-MM-DD"),
    date_to: date | None = Query(default=None, alias="to", description="Конец периода YYYY-MM-DD"),
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.measurements_chart(user.id, link_id, metric, date_from, date_to))


@router.get(
    "/{link_id}/notes",
    tags=["Coach - Clients"],
    summary="Заметки тренера по клиенту",
)
async def list_notes(link_id: int, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.list_notes(user.id, link_id))


@router.get(
    "/{link_id}/stats",
    tags=["Coach - Clients"],
    summary="Статистика клиента",
    description="Сессии, календарь, замеры, дни в работе и последние показатели.",
)
async def client_stats(link_id: int, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.client_stats(user.id, link_id))


@router.get(
    "/{link_id}/sessions",
    tags=["Coach - Clients"],
    summary="Тренировки клиента",
)
async def client_sessions(
    link_id: int,
    user: Annotated[UserPublic, Depends(require_trainer)],
    kind: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await svc.client_sessions(user.id, link_id, kind=kind, page_size=page_size, offset=offset)
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.patch(
    "/{link_id}",
    tags=["Coach - Clients"],
    summary="Обновить связь с клиентом",
    description="Меняет статус (`new|permanent|paused|archived`), цели и формат тренировок.",
)
async def patch(link_id: int, payload: ClientPatchIn, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(
        data=await svc.patch_client(
            user.id, link_id, payload.status, payload.goals, payload.training_format, payload.target_weight_kg
        )
    )


@router.delete(
    "/{link_id}",
    tags=["Coach - Clients"],
    summary="Архивировать клиента",
    description="Тело запроса не требуется. Связь переводится в `archived`.",
)
async def archive(link_id: int, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    await svc.archive_client(user.id, link_id)
    return SuccessResponse(data={"ok": True})


@router.post(
    "/{link_id}/measurements",
    tags=["Coach - Clients"],
    summary="Добавить замеры клиента",
    description="Все поля необязательны — передайте только измеренные значения.",
)
async def measurement(link_id: int, payload: MeasurementIn, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.add_measurement(user.id, link_id, payload))


@router.post(
    "/{link_id}/notes",
    tags=["Coach - Clients"],
    summary="Добавить заметку тренера",
    description="Текстовая заметка в карточке клиента.",
)
async def note(link_id: int, payload: ClientNoteIn, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.add_note(user.id, link_id, payload.text))


@router.delete(
    "/{link_id}/notes/{note_id}",
    tags=["Coach - Clients"],
    summary="Удалить заметку тренера",
    description="Тело запроса не требуется.",
)
async def delete_note(link_id: int, note_id: int, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    await svc.delete_note(user.id, link_id, note_id)
    return SuccessResponse(data={"ok": True})
