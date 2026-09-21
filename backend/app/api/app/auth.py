from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.constants import AUD_APP
from app.deps.auth import get_app_user
from app.deps.rate_limit import rate_limit_auth
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
)
from app.schemas.common import SuccessResponse, TokenPair, UserPublic
from app.services import auth as auth_service

router = APIRouter(prefix="/auth")


@router.post(
    "/register",
    response_model=SuccessResponse[TokenPair],
    status_code=status.HTTP_201_CREATED,
    tags=["App - Auth"],
    summary="Регистрация клиента или тренера",
    description="Создаёт аккаунт. Нужен email или телефон. Роль только `client` или `trainer`. Возвращает пару JWT.",
    dependencies=[Depends(rate_limit_auth)],
)
async def register(payload: RegisterRequest) -> SuccessResponse[TokenPair]:
    data = await auth_service.register(payload)
    return SuccessResponse(data=data)


@router.post(
    "/login",
    response_model=SuccessResponse[TokenPair],
    tags=["App - Auth"],
    summary="Вход в приложение",
    description="`login` — email или телефон. Возвращает access и refresh токены приложения (`aud=app`).",
    dependencies=[Depends(rate_limit_auth)],
)
async def login(payload: LoginRequest) -> SuccessResponse[TokenPair]:
    data = await auth_service.login(payload, AUD_APP)
    return SuccessResponse(data=data)


@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenPair],
    tags=["App - Auth"],
    summary="Обновить токены приложения",
    description="Принимает действующий refresh JWT и выдаёт новую пару токенов.",
    dependencies=[Depends(rate_limit_auth)],
)
async def refresh(payload: RefreshRequest) -> SuccessResponse[TokenPair]:
    data = await auth_service.refresh_tokens(payload.refresh_token, AUD_APP)
    return SuccessResponse(data=data)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["App - Auth"],
    summary="Выход из приложения",
    description="Отзывает refresh-токен. После этого refresh перестаёт работать.",
)
async def logout(payload: LogoutRequest) -> None:
    await auth_service.logout(payload.refresh_token, AUD_APP)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["App - Auth"],
    summary="Сменить пароль",
    description="Нужен текущий пароль. Новый пароль — минимум 8 символов.",
)
async def change_password(
    payload: ChangePasswordRequest,
    user: Annotated[UserPublic, Depends(get_app_user)],
) -> None:
    await auth_service.change_password(user.id, payload)


@router.post(
    "/password-reset/request",
    response_model=SuccessResponse[dict],
    tags=["App - Auth"],
    summary="Запросить сброс пароля",
    description="Ищет аккаунт по email/телефону и создаёт токен сброса. В ответе для локальной разработки может быть token.",
    dependencies=[Depends(rate_limit_auth)],
)
async def password_reset_request(
    payload: PasswordResetRequest,
) -> SuccessResponse[dict]:
    data = await auth_service.request_password_reset(payload)
    return SuccessResponse(data=data)


@router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["App - Auth"],
    summary="Подтвердить сброс пароля",
    description="Применяет новый пароль по токену из запроса сброса.",
    dependencies=[Depends(rate_limit_auth)],
)
async def password_reset_confirm(payload: PasswordResetConfirmRequest) -> None:
    await auth_service.confirm_password_reset(payload)
