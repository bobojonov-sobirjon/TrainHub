from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.roles import require_trainer
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.pagination import Page, page_args
from app.schemas.stage import TrainerProfileIn
from app.services import trainers as svc

router = APIRouter()


@router.get("/trainer/profile", tags=["App - Trainer"], summary="Профиль тренера")
async def profile(user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.get_profile(user.id))


@router.patch(
    "/trainer/profile",
    tags=["App - Trainer"],
    summary="Обновить профиль тренера",
    description="Можно передать только нужные поля: био, опыт, специализации, форматы, цена, длительность.",
)
async def update_profile(
    payload: TrainerProfileIn,
    user: Annotated[UserPublic, Depends(require_trainer)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.update_profile(user.id, payload.model_dump(exclude_unset=True)))


@router.get("/trainer/dashboard", tags=["App - Trainer"], summary="Дашборд тренера")
async def dashboard(user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.dashboard(user.id))


@router.get("/trainer/reports", tags=["App - Trainer"], summary="Месячный отчёт")
async def reports(user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.reports(user.id))


@router.get("/trainer/attention", tags=["App - Trainer"], summary="Клиенты, требующие внимания")
async def attention(user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await svc.attention_list(user.id))


@router.post(
    "/trainer/attention/{item_id}/resolve",
    tags=["App - Trainer"],
    summary="Снять пункт внимания",
    description="Тело запроса не требуется. Помечает карточку внимания решённой.",
)
async def resolve(item_id: int, user: Annotated[UserPublic, Depends(require_trainer)]) -> SuccessResponse[dict]:
    await svc.resolve_attention(user.id, item_id)
    return SuccessResponse(data={"ok": True})


@router.get("/trainers", tags=["App - Trainers"], summary="Каталог тренеров")
async def trainers(
    category: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await svc.list_marketplace(category, page, page_size, offset)
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/trainers/{trainer_id}", tags=["App - Trainers"], summary="Публичный профиль тренера")
async def trainer_detail(trainer_id: int) -> SuccessResponse[dict]:
    return SuccessResponse(data=await svc.public_trainer(trainer_id))
