from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.auth import get_admin_user
from app.schemas.common import SuccessResponse, UserPublic
from app.services import admin_users as svc

router = APIRouter()


@router.get("/dashboard", tags=["Admin - Dashboard"], summary="Дашборд администратора")
async def dashboard(_user: Annotated[UserPublic, Depends(get_admin_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.dashboard())
