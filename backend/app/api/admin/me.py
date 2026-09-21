from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.auth import get_admin_user
from app.schemas.common import SuccessResponse, UserPublic

router = APIRouter()


@router.get(
    "/me",
    response_model=SuccessResponse[UserPublic],
    tags=["Admin - Profile"],
    summary="Текущий администратор",
)
async def me(user: Annotated[UserPublic, Depends(get_admin_user)]) -> SuccessResponse[UserPublic]:
    return SuccessResponse(data=user)
