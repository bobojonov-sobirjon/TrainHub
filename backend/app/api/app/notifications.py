from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.auth import get_app_user
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.stage import NotificationPrefsIn
from app.services import cabinet as cab

router = APIRouter()


@router.get("/notifications", tags=["App - Notifications"], summary="Уведомления")
async def list_notifications(
    user: Annotated[UserPublic, Depends(get_app_user)],
    tab: str = "today",
) -> SuccessResponse[list]:
    return SuccessResponse(data=await cab.notifications(user.id, tab))


@router.post(
    "/notifications/{note_id}/read",
    tags=["App - Notifications"],
    summary="Отметить уведомление прочитанным",
    description="Тело запроса не требуется.",
)
async def read_one(note_id: int, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    await cab.read_notification(user.id, note_id)
    return SuccessResponse(data={"ok": True})


@router.post(
    "/notifications/read-all",
    tags=["App - Notifications"],
    summary="Прочитать все уведомления",
    description="Тело запроса не требуется.",
)
async def read_all(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    await cab.read_all(user.id)
    return SuccessResponse(data={"ok": True})


@router.get("/me/notification-preferences", tags=["App - Notifications"], summary="Настройки уведомлений")
async def get_prefs(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cab.get_prefs(user.id))


@router.patch(
    "/me/notification-preferences",
    tags=["App - Notifications"],
    summary="Обновить настройки уведомлений",
    description="Передайте только изменяемые флаги. Остальные сохраняются.",
)
async def update_prefs(
    payload: NotificationPrefsIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cab.update_prefs(user.id, payload))
