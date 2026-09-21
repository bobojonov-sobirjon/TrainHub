from fastapi import APIRouter

from app.schemas.common import DictionariesData, SuccessResponse
from app.services.dictionaries import list_dictionaries

router = APIRouter()


@router.get(
    "/dictionaries",
    response_model=SuccessResponse[DictionariesData],
    tags=["App - Dictionaries"],
    summary="Справочники",
    description="Коды и русские названия: уровень, цели, мышцы, оборудование, форматы.",
)
async def dictionaries() -> SuccessResponse[DictionariesData]:
    data = await list_dictionaries()
    return SuccessResponse(data=data)
