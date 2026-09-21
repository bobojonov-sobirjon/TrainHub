from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.constants import ROLE_TRAINER
from app.deps.auth import get_app_user
from app.deps.roles import require_client
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.pagination import Page, page_args
from app.schemas.stage import MeasurementIn, NoteIn
from app.services import cabinet as cab
from app.services import sessions as sess

router = APIRouter()


@router.get("/client/home", tags=["App - Client"], summary="Главная клиента")
async def home(user: Annotated[UserPublic, Depends(require_client)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cab.home(user.id))


@router.get("/client/measurements", tags=["App - Client"], summary="Мои замеры")
async def measurements(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await cab.measurements(user.id))


@router.post(
    "/client/measurements",
    tags=["App - Client"],
    summary="Добавить свои замеры",
    description="Все поля необязательны. Передайте только измеренные значения в кг/см/%.",
)
async def add_measurement(
    payload: MeasurementIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cab.add_own_measurement(user.id, payload))


@router.get("/client/progress", tags=["App - Client"], summary="Прогресс относительно прошлого замера")
async def progress(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cab.progress(user.id))


@router.get("/client/photo-progress", tags=["App - Client"], summary="Фотопрогресс")
async def photos(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await cab.list_photo_sets(user.id))


@router.post(
    "/client/photo-progress",
    tags=["App - Client"],
    summary="Загрузить фотопрогресс",
    description="multipart/form-data. `taken_on` — дата съёмки, `angles` — front,side,back через запятую, `files` — до 3 фото.",
)
async def add_photo(
    user: Annotated[UserPublic, Depends(get_app_user)],
    taken_on: date = Form(..., description="Дата съёмки YYYY-MM-DD", examples=["2026-09-19"]),
    angles: str = Form("front", description="Ракурсы через запятую: front, side, back", examples=["front,side,back"]),
    files: list[UploadFile] = File(..., description="До 3 изображений JPEG/PNG"),
) -> SuccessResponse[dict]:
    allowed = {"front", "side", "back"}
    angle_list = [item.strip() for item in angles.split(",") if item.strip() in allowed]
    blobs: list[tuple[str, bytes, str]] = []
    fallback = ["front", "side", "back"]
    for index, upload in enumerate(files[:3]):
        data = await upload.read()
        angle = angle_list[index] if index < len(angle_list) else fallback[index]
        blobs.append((angle, data, upload.filename or "photo.jpg"))
    return SuccessResponse(data=await cab.add_photo_set(user.id, taken_on, blobs))


@router.get("/client/notes", tags=["App - Client"], summary="Личные заметки")
async def notes(user: Annotated[UserPublic, Depends(get_app_user)], q: str | None = None) -> SuccessResponse[list]:
    return SuccessResponse(data=await cab.list_notes(user.id, q))


@router.post(
    "/client/notes",
    tags=["App - Client"],
    summary="Создать заметку",
    description="Заголовок обязателен, тело можно оставить пустым.",
)
async def create_note(payload: NoteIn, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cab.create_note(user.id, payload))


@router.patch(
    "/client/notes/{note_id}",
    tags=["App - Client"],
    summary="Изменить заметку",
    description="Полная модель: title и body.",
)
async def update_note(
    note_id: int, payload: NoteIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cab.update_note(user.id, note_id, payload))


@router.delete(
    "/client/notes/{note_id}",
    tags=["App - Client"],
    summary="Удалить заметку",
    description="Тело запроса не требуется.",
)
async def delete_note(note_id: int, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    await cab.delete_note(user.id, note_id)
    return SuccessResponse(data={"ok": True})


@router.get("/client/sessions", tags=["App - Client"], summary="История тренировок клиента")
async def client_sessions(
    user: Annotated[UserPublic, Depends(get_app_user)],
    kind: str | None = None,
    format: str | None = None,
    with_trainer: bool | None = None,
    sort: str = "newest",
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await sess.client_sessions(
        user.id,
        kind=kind,
        format_=format,
        with_trainer=with_trainer,
        sort=sort,
        page_size=page_size,
        offset=offset,
    )
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/client/sessions/{session_id}", tags=["App - Client"], summary="Карточка тренировки клиента")
async def client_session_detail(
    session_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await sess.get_session(session_id, user.id, ROLE_TRAINER in user.roles))
