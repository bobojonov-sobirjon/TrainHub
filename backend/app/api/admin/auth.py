from fastapi import APIRouter, Depends, status

from app.core.constants import AUD_ADMIN
from app.deps.rate_limit import rate_limit_auth
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest
from app.schemas.common import SuccessResponse, TokenPair
from app.services import auth as auth_service

router = APIRouter(prefix="/auth")


@router.post(
    "/login",
    response_model=SuccessResponse[TokenPair],
    tags=["Admin - Auth"],
    summary="Вход администратора",
    description="Только пользователь с ролью `admin`. `login` — email или телефон. Токены с `aud=admin`.",
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
