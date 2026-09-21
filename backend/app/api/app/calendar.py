from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.roles import require_trainer
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.stage import CalendarIn, SessionCreateIn
from app.services import calendar as cal
from app.services import sessions as sess

router = APIRouter(prefix="/trainer/calendar")


@router.get("", tags=["App - Calendar"], summary="События календаря")
async def list_events(
    user: Annotated[UserPublic, Depends(require_trainer)],
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> SuccessResponse[list]:
    return SuccessResponse(data=await cal.list_events(user.id, date_from, date_to))


@router.post(
    "",
    tags=["App - Calendar"],
    summary="Назначить тренировку",
    description="Создаёт событие. `client_id` можно не указывать — тогда это личная тренировка тренера.",
)
async def create(payload: CalendarIn, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cal.create_event(user.id, payload))


@router.get("/{event_id}", tags=["App - Calendar"], summary="Карточка события")
async def detail(event_id: int, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cal.get_event(user.id, event_id))


@router.patch(
    "/{event_id}",
    tags=["App - Calendar"],
    summary="Изменить событие",
    description="Полная модель события: даты, формат, типы, мышцы, напоминание.",
)
async def update(
    event_id: int, payload: CalendarIn, user: Annotated[UserPublic, Depends(require_trainer)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cal.update_event(user.id, event_id, payload))


@router.post(
    "/{event_id}/cancel",
    tags=["App - Calendar"],
    summary="Отменить событие",
    description="Тело запроса не требуется. Статус события — cancelled.",
)
async def cancel(event_id: int, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cal.cancel_event(user.id, event_id))


@router.delete(
    "/{event_id}",
    tags=["App - Calendar"],
    summary="Удалить событие",
    description="Тело запроса не требуется.",
)
async def delete(event_id: int, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    await cal.delete_event(user.id, event_id)
    return SuccessResponse(data={"ok": True})


@router.post(
    "/{event_id}/start-session",
    tags=["App - Calendar"],
    summary="Начать живую сессию",
    description="Тело запроса не требуется. Создаёт сессию из события календаря.",
)
async def start(event_id: int, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    event = await cal.get_event(user.id, event_id)
    payload = SessionCreateIn(
        source="planned",
        client_ids=[event["client_id"]] if event.get("client_id") else [],
        kinds=list(event.get("kinds") or []),
        calendar_event_id=event_id,
    )
    return SuccessResponse(data=await sess.create_session(user.id, True, payload))
