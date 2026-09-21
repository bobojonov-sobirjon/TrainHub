from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.auth import get_app_user
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.stage import TicketIn
from app.services import content as cnt

router = APIRouter()


@router.get("/faq", tags=["App - FAQ"], summary="Список FAQ")
async def faq(q: str | None = None, audience: str | None = None) -> SuccessResponse[list]:
    return SuccessResponse(data=await cnt.list_faq(q, audience, published_only=True))


@router.get("/faq/{slug}", tags=["App - FAQ"], summary="Статья FAQ")
async def faq_detail(slug: str) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cnt.get_faq(slug))


@router.get("/legal/{doc_type}", tags=["App - Legal"], summary="Юридический документ")
async def legal(doc_type: str) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cnt.get_legal(doc_type))


@router.get("/support/tickets", tags=["App - Support"], summary="Мои обращения")
async def tickets(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await cnt.my_tickets(user.id))


@router.post(
    "/support/tickets",
    tags=["App - Support"],
    summary="Создать обращение",
    description="Тема и текст обязательны. Статус нового обращения — `open`.",
)
async def create_ticket(payload: TicketIn, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cnt.create_ticket(user.id, payload))
