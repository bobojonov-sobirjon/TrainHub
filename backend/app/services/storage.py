import uuid
from pathlib import Path

import anyio

from app.core.config import settings
from app.core.exceptions import AppError

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".mp4",
    ".mov",
    ".webm",
    ".pdf",
}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}

LEGAL_EXTENSIONS = {".pdf", ".doc", ".docx"}

LEGAL_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-word",
    "application/vnd.ms-word.document.macroenabled.12",
    "application/octet-stream",
    "application/zip",
    "application/x-zip-compressed",
}

MAX_BYTES = 20 * 1024 * 1024


def media_root() -> Path:
    root = Path(settings.media_dir)
    if not root.is_absolute():
        root = Path(__file__).resolve().parents[2] / root
    return root


def public_url(relative_key: str) -> str:
    base = settings.public_base_url.rstrip("/")
    return f"{base}/media/{relative_key.lstrip('/')}"


def _safe_suffix(filename: str, allowed: set[str] | None = None) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in (allowed or ALLOWED_EXTENSIONS):
        raise AppError("INVALID_FILE", "Этот тип файла не разрешён", http_status=400)
    return suffix


def assert_legal_file(filename: str, content_type: str | None) -> None:
    _safe_suffix(filename, LEGAL_EXTENSIONS)
    mime = (content_type or "").split(";")[0].strip().lower()
    if mime and mime not in LEGAL_MIME_TYPES:
        raise AppError("INVALID_FILE", "Разрешены только файлы PDF, DOC и DOCX", http_status=400)


async def save_bytes(
    data: bytes,
    *,
    folder: str,
    filename: str,
    allowed: set[str] | None = None,
) -> str:
    if len(data) > MAX_BYTES:
        raise AppError("FILE_TOO_LARGE", "Файл слишком большой", http_status=400)
    if settings.storage_backend != "local":
        raise AppError("STORAGE_NOT_READY", "Удалённое хранилище не настроено", http_status=501)

    suffix = _safe_suffix(filename, allowed)
    relative = f"{folder.strip('/')}/{uuid.uuid4().hex}{suffix}"
    dest = media_root() / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    await anyio.Path(dest).write_bytes(data)
    return public_url(relative)


def ensure_media_dir() -> None:
    media_root().mkdir(parents=True, exist_ok=True)
