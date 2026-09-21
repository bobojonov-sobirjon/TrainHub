from typing import Annotated

from fastapi import Depends

from app.core.constants import ROLE_CLIENT, ROLE_TRAINER
from app.core.exceptions import AppError
from app.deps.auth import get_app_user
from app.schemas.common import UserPublic


async def require_trainer(user: Annotated[UserPublic, Depends(get_app_user)]) -> UserPublic:
    if ROLE_TRAINER not in user.roles:
        raise AppError("FORBIDDEN", "Требуются права тренера", http_status=403)
    return user


async def require_client(user: Annotated[UserPublic, Depends(get_app_user)]) -> UserPublic:
    if ROLE_CLIENT not in user.roles:
        raise AppError("FORBIDDEN", "Требуются права клиента", http_status=403)
    return user
