from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.exceptions import AppError
from app.deps.auth import get_admin_user
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.stage import FaqIn, FaqPublishIn, LegalIn, TicketStatusIn
from app.services import content as cnt
from app.services.storage import LEGAL_EXTENSIONS, assert_legal_file, save_bytes

router = APIRouter()


@router.get("/faq", tags=["Admin - FAQ"], summary="Все статьи FAQ")
async def list_faq(
    _user: Annotated[UserPublic, Depends(get_admin_user)],
    q: str | None = None,
    audience: str | None = None,
) -> SuccessResponse[list]:
    return SuccessResponse(data=await cnt.list_faq(q, audience, published_only=False))


@router.get("/faq/{faq_id}", tags=["Admin - FAQ"], summary="Карточка FAQ")
async def faq_detail(
    faq_id: int, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cnt.get_faq_admin(faq_id))


@router.post(
    "/faq",
    tags=["Admin - FAQ"],
    summary="Создать статью FAQ",
    description="`slug` уникален. Аудитория: all, trainer, client.",
)
async def create_faq(payload: FaqIn, _user: Annotated[UserPublic, Depends(get_admin_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cnt.upsert_faq(payload))


@router.patch(
    "/faq/{faq_id}",
    tags=["Admin - FAQ"],
    summary="Изменить статью FAQ",
    description="Полная модель статьи. Slug должен остаться уникальным.",
)
async def update_faq(
    faq_id: int, payload: FaqIn, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cnt.upsert_faq(payload, faq_id))


@router.post(
    "/faq/{faq_id}/publish",
    tags=["Admin - FAQ"],
    summary="Опубликовать или скрыть FAQ",
    description="`is_published: true` — показать в приложении, `false` — скрыть.",
)
async def publish_faq(
    faq_id: int,
    payload: FaqPublishIn,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cnt.publish_faq(faq_id, payload.is_published))


@router.get("/legal/{doc_type}", tags=["Admin - Legal"], summary="Юридический документ")
async def get_legal(doc_type: str, _user: Annotated[UserPublic, Depends(get_admin_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cnt.get_legal(doc_type))


@router.patch(
    "/legal/{doc_type}",
    tags=["Admin - Legal"],
    summary="Обновить юридический документ текстом",
    description="`doc_type`: terms или privacy. Сохраняет Markdown и снимает ранее загруженный файл.",
)
async def update_legal(
    doc_type: str, payload: LegalIn, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cnt.update_legal(doc_type, payload))


@router.post(
    "/legal/{doc_type}/file",
    tags=["Admin - Legal"],
    summary="Загрузить юридический документ файлом",
    description="multipart/form-data. Разрешены только PDF, DOC и DOCX. `file` можно не передавать, если файл уже есть и меняется только версия.",
)
async def upload_legal_file(
    doc_type: str,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
    version: str = Form("1.0", description="Версия документа", examples=["1.1"]),
    file: UploadFile | None = File(None, description="PDF, DOC или DOCX"),
) -> SuccessResponse[dict]:
    if doc_type not in {"terms", "privacy"}:
        raise AppError("LEGAL_NOT_FOUND", "Документ не найден", http_status=404)
    current = await cnt.get_legal(doc_type)
    if file is not None and file.filename:
        assert_legal_file(file.filename, file.content_type)
        data = await file.read()
        file_url = await save_bytes(
            data,
            folder=f"legal/{doc_type}",
            filename=file.filename,
            allowed=LEGAL_EXTENSIONS,
        )
        return SuccessResponse(
            data=await cnt.update_legal_file(
                doc_type,
                version=version,
                file_url=file_url,
                file_name=file.filename,
            )
        )
    if current.get("file_url"):
        return SuccessResponse(
            data=await cnt.update_legal_file(
                doc_type,
                version=version,
                file_url=str(current["file_url"]),
                file_name=str(current.get("file_name") or ""),
            )
        )
    raise AppError("FILE_REQUIRED", "Загрузите файл PDF, DOC или DOCX", http_status=400)


@router.get("/tickets", tags=["Admin - Tickets"], summary="Обращения поддержки")
async def tickets(_user: Annotated[UserPublic, Depends(get_admin_user)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await cnt.admin_tickets())


@router.get("/tickets/{ticket_id}", tags=["Admin - Tickets"], summary="Карточка обращения")
async def ticket_detail(
    ticket_id: int, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cnt.get_ticket_admin(ticket_id))


@router.patch(
    "/tickets/{ticket_id}",
    tags=["Admin - Tickets"],
    summary="Сменить статус обращения",
    description="Статус: open, in_progress, answered, closed.",
)
async def set_status(
    ticket_id: int, payload: TicketStatusIn, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cnt.set_ticket_status(ticket_id, payload.status))
