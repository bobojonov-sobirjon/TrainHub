from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.constants import AUD_ADMIN
from app.deps.auth import get_admin_user
from app.deps.rate_limit import rate_limit_auth
from app.schemas.auth import ChangePasswordRequest, LoginRequest, LogoutRequest, RefreshRequest
from app.schemas.common import SuccessResponse, TokenPair, UserPublic
from app.services import auth as auth_service

router = APIRouter(prefix="/auth")


@router.post(
    "/login",
    response_model=SuccessResponse[TokenPair],
    tags=["Admin - Auth"],
    summary="Вход администратора",
    description=(
        "Только пользователь с ролью `admin`. "
        "`login` — username (`admin`), email или телефон. Токены с `aud=admin`."
    ),
    dependencies=[Depends(rate_limit_auth)],
)
async def login(payload: LoginRequest) -> SuccessResponse[TokenPair]:
    data = await auth_service.login(payload, AUD_ADMIN)
    return SuccessResponse(data=data)


@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenPair],
    tags=["Admin - Auth"],
    summary="Обновить токены администратора",
    description="Принимает admin refresh JWT и выдаёт новую пару токенов.",
    dependencies=[Depends(rate_limit_auth)],
)
async def refresh(payload: RefreshRequest) -> SuccessResponse[TokenPair]:
    data = await auth_service.refresh_tokens(payload.refresh_token, AUD_ADMIN)
    return SuccessResponse(data=data)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Admin - Auth"],
    summary="Выход администратора",
    description="Отзывает admin refresh-токен.",
)
async def logout(payload: LogoutRequest) -> None:
    await auth_service.logout(payload.refresh_token, AUD_ADMIN)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Admin - Auth"],
    summary="Сменить пароль администратора",
    description="Нужен текущий пароль. Новый пароль — минимум 8 символов.",
)
async def change_password(
    payload: ChangePasswordRequest,
    user: Annotated[UserPublic, Depends(get_admin_user)],
) -> None:
    await auth_service.change_password(user.id, payload)
