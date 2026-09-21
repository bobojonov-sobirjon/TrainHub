from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.auth import get_admin_user
from app.schemas.common import DictionariesData, SuccessResponse, UserPublic
from app.services.dictionaries import list_dictionaries

router = APIRouter()


@router.get(
    "/dictionaries",
    tags=["Admin - Dictionaries"],
    summary="Справочники",
    description="Коды и русские названия для селектов админ-панели.",
)
async def dictionaries(_user: Annotated[UserPublic, Depends(get_admin_user)]) -> SuccessResponse[DictionariesData]:
    return SuccessResponse(data=await list_dictionaries())
