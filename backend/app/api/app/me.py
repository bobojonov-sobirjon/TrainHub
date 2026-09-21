from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.auth import get_app_user
from app.schemas.common import SuccessResponse, UserPublic

router = APIRouter()


@router.get(
    "/me",
    response_model=SuccessResponse[UserPublic],
    tags=["App - Profile"],
    summary="Текущий пользователь приложения",
)
async def me(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[UserPublic]:
    return SuccessResponse(data=user)
