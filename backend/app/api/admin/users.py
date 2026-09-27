from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.auth import get_admin_user
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.pagination import Page, page_args
from app.schemas.stage import TrainerVerifyIn, UserBlockIn
from app.services import admin_users as svc

router = APIRouter()


@router.get("/coaches", tags=["Admin - Coach"], summary="Все Coach (тренеры)")
async def list_coaches(
    _user: Annotated[UserPublic, Depends(get_admin_user)],
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await svc.list_users(q, "trainer", page_size, offset)
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/app-clients", tags=["Admin - Client"], summary="Все Client (клиенты)")
async def list_app_clients(
    _user: Annotated[UserPublic, Depends(get_admin_user)],
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await svc.list_users(q, "client", page_size, offset)
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/users", tags=["Admin - Coach"], summary="Все пользователи")
async def list_users(
    _user: Annotated[UserPublic, Depends(get_admin_user)],
    q: str | None = None,
    role: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await svc.list_users(q, role, page_size, offset)
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/users/{user_id}", tags=["Admin - Coach"], summary="Карточка пользователя")
async def user_detail(
    user_id: int, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.get_user(user_id))


@router.post(
    "/users/{user_id}/verify",
    tags=["Admin - Coach"],
    summary="Верифицировать тренера",
    description="`is_verified: true` — подтвердить тренера, `false` — снять верификацию.",
)
async def verify_trainer(
    user_id: int,
    payload: TrainerVerifyIn,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.set_trainer_verified(user_id, payload.is_verified))


@router.post(
    "/users/{user_id}/block",
    tags=["Admin - Coach"],
    summary="Заблокировать или разблокировать",
    description="`is_blocked: true` и `reason` — блокировка. `false` — снять блок.",
)
async def block_user(
    user_id: int,
    payload: UserBlockIn,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.block_user(user_id, payload.is_blocked, payload.reason))
