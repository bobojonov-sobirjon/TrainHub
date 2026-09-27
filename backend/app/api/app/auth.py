from typing import Annotated

from fastapi import APIRouter, Depends, Header, status

from app.core.config import settings
from app.core.constants import AUD_APP
from app.core.exceptions import AppError
from app.deps.auth import get_app_user
from app.deps.rate_limit import rate_limit_auth
from app.schemas.auth import (
    AppleAuthIn,
    ChangePasswordRequest,
    GoogleAuthIn,
    LoginRequest,
    LogoutRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TelegramSendCodeIn,
    TelegramVerifyIn,
)
from app.schemas.common import SuccessResponse, TokenPair, UserPublic
from app.services import auth as auth_service
from app.services import social as social_service
from app.services import telegram_auth as telegram_auth_service

router = APIRouter(prefix="/auth")


@router.post(
    "/register",
    response_model=SuccessResponse[TokenPair],
    status_code=status.HTTP_201_CREATED,
    tags=["Shared - Auth"],
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
    tags=["Shared - Auth"],
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
    tags=["Shared - Auth"],
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
    tags=["Shared - Auth"],
    summary="Выход из приложения",
    description="Отзывает refresh-токен. После этого refresh перестаёт работать.",
)
async def logout(payload: LogoutRequest) -> None:
    await auth_service.logout(payload.refresh_token, AUD_APP)


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Shared - Auth"],
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
    tags=["Shared - Auth"],
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
    tags=["Shared - Auth"],
    summary="Подтвердить сброс пароля",
    description="Применяет новый пароль по токену из запроса сброса.",
    dependencies=[Depends(rate_limit_auth)],
)
async def password_reset_confirm(payload: PasswordResetConfirmRequest) -> None:
    await auth_service.confirm_password_reset(payload)


@router.post(
    "/google",
    response_model=SuccessResponse[TokenPair],
    tags=["Shared - Auth Google"],
    summary="Вход через Google",
    description="Принимает Firebase ID token (вход Google в Firebase Auth) или обычный Google ID token. Если аккаунта нет — создаёт. Возвращает пару JWT.",
    dependencies=[Depends(rate_limit_auth)],
)
async def google(payload: GoogleAuthIn) -> SuccessResponse[TokenPair]:
    return SuccessResponse(data=await social_service.login_google(payload))


@router.post(
    "/apple",
    response_model=SuccessResponse[TokenPair],
    tags=["Shared - Auth Apple"],
    summary="Вход через Apple",
    description="Firebase ID token (Apple в Firebase Auth) или native Apple identity token. Имя Apple отдаёт только при первом входе.",
    dependencies=[Depends(rate_limit_auth)],
)
async def apple(payload: AppleAuthIn) -> SuccessResponse[TokenPair]:
    return SuccessResponse(data=await social_service.login_apple(payload))


@router.post(
    "/telegram/send-code",
    response_model=SuccessResponse[dict],
    tags=["Shared - Auth Telegram"],
    summary="Запросить код в Telegram-бота",
    description="`identifier` — телефон или @username. Если бот уже открыт — код приходит в личку. Первый вход: `requires_bot_start=true` и `bot_url` с `?start=login_...`.",
    dependencies=[Depends(rate_limit_auth)],
)
async def telegram_send_code(payload: TelegramSendCodeIn) -> SuccessResponse[dict]:
    return SuccessResponse(data=await telegram_auth_service.send_login_code(payload))


@router.post(
    "/telegram/verify",
    response_model=SuccessResponse[TokenPair],
    tags=["Shared - Auth Telegram"],
    summary="Подтвердить код Telegram",
    description="Проверяет код из лички бота. Если верный — логин или регистрация и пара JWT.",
    dependencies=[Depends(rate_limit_auth)],
)
async def telegram_verify(payload: TelegramVerifyIn) -> SuccessResponse[TokenPair]:
    return SuccessResponse(data=await telegram_auth_service.verify_login_code(payload))


@router.post(
    "/telegram/webhook",
    include_in_schema=False,
)
async def telegram_webhook(
    update: dict,
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
) -> dict:
    secret = settings.telegram_webhook_secret.strip()
    if secret and x_telegram_bot_api_secret_token != secret:
        raise AppError("FORBIDDEN", "Недействительный webhook secret", http_status=403)
    return await telegram_auth_service.handle_webhook(update)
