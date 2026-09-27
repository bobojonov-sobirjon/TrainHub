from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.auth import get_admin_user
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.pagination import Page, page_args
from app.services import clients as svc

router = APIRouter()


@router.get("/clients", tags=["Admin - Links"], summary="Связи тренер–клиент")
async def list_clients(
    _user: Annotated[UserPublic, Depends(get_admin_user)],
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await svc.admin_list(q, page_size, offset)
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/clients/{link_id}", tags=["Admin - Links"], summary="Карточка связи")
async def client_detail(
    link_id: int, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.admin_get(link_id))
