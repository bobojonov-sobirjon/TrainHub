import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.exceptions import AppError
from app.deps.auth import get_admin_user
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.pagination import Page, page_args
from app.schemas.stage import ExerciseCreateIn, ProgramCreateIn, ProgramDayExerciseIn, ProgramDayIn
from app.services import catalog as cat
from app.services.storage import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, save_bytes

router = APIRouter()


@router.get("/programs", tags=["Admin - Programs"], summary="Все программы")
async def list_programs(
    _user: Annotated[UserPublic, Depends(get_admin_user)],
    level: str | None = None,
    source: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await cat.list_programs(
        level=level,
        goal=None,
        equipment=None,
        source=source,
        author_id=None,
        page_size=page_size,
        offset=offset,
        published_only=False,
    )
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.post(
    "/programs",
    tags=["Admin - Programs"],
    summary="Создать программу каталога",
    description="`source` на сервере ставится в `catalog`. Уровень, цели и оборудование — коды справочников.",
)
async def create_program(
    payload: ProgramCreateIn,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
) -> SuccessResponse[dict]:
    payload.source = "catalog"
    return SuccessResponse(data=await cat.create_program(None, payload))


@router.get("/programs/{program_id}", tags=["Admin - Programs"], summary="Карточка программы")
async def program_detail(
    program_id: int, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.get_program(program_id, None))


@router.patch(
    "/programs/{program_id}",
    tags=["Admin - Programs"],
    summary="Изменить программу",
    description="Полная модель программы: название, описание, уровень, цели, оборудование, статус.",
)
async def update_program(
    program_id: int,
    payload: ProgramCreateIn,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.admin_update_program(program_id, payload))


@router.delete(
    "/programs/{program_id}",
    tags=["Admin - Programs"],
    summary="Архивировать программу",
    description="Тело запроса не требуется. Статус программы становится `archived`.",
)
async def delete_program(
    program_id: int, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    await cat.admin_delete_program(program_id)
    return SuccessResponse(data={"ok": True})


@router.post(
    "/programs/{program_id}/days",
    tags=["Admin - Programs"],
    summary="Добавить день программы",
    description="Название обязательно. `focus_muscles` — коды из справочника мышц. Если `sort_order` пуст, день ставится в конец.",
)
async def create_program_day(
    program_id: int,
    payload: ProgramDayIn,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.create_program_day(program_id, payload))


@router.patch(
    "/programs/{program_id}/days/{day_id}",
    tags=["Admin - Programs"],
    summary="Изменить день программы",
    description="Название, описание, длительность и мышцы дня.",
)
async def update_program_day(
    program_id: int,
    day_id: int,
    payload: ProgramDayIn,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.update_program_day(program_id, day_id, payload))


@router.delete(
    "/programs/{program_id}/days/{day_id}",
    tags=["Admin - Programs"],
    summary="Удалить день программы",
    description="День и его упражнения удаляются. Тело запроса не требуется.",
)
async def delete_program_day(
    program_id: int,
    day_id: int,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.delete_program_day(program_id, day_id))


@router.post(
    "/programs/{program_id}/days/{day_id}/exercises",
    tags=["Admin - Programs"],
    summary="Добавить упражнение в день",
    description="`exercise_id` из каталога. Подходы и диапазон повторений необязательны.",
)
async def add_day_exercise(
    program_id: int,
    day_id: int,
    payload: ProgramDayExerciseIn,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.add_day_exercise(program_id, day_id, payload))


@router.patch(
    "/programs/{program_id}/days/{day_id}/exercises/{item_id}",
    tags=["Admin - Programs"],
    summary="Изменить упражнение дня",
    description="Можно сменить упражнение, подходы, повторения и заметку.",
)
async def update_day_exercise(
    program_id: int,
    day_id: int,
    item_id: int,
    payload: ProgramDayExerciseIn,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.update_day_exercise(program_id, day_id, item_id, payload))


@router.delete(
    "/programs/{program_id}/days/{day_id}/exercises/{item_id}",
    tags=["Admin - Programs"],
    summary="Убрать упражнение из дня",
    description="Тело запроса не требуется.",
)
async def delete_day_exercise(
    program_id: int,
    day_id: int,
    item_id: int,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.delete_day_exercise(program_id, day_id, item_id))


@router.get("/exercises", tags=["Admin - Exercises"], summary="Каталог упражнений")
async def exercises(
    _user: Annotated[UserPublic, Depends(get_admin_user)],
    q: str | None = None,
    equipment: str | None = None,
    muscle: str | None = None,
) -> SuccessResponse[list]:
    return SuccessResponse(data=await cat.list_exercises(q, equipment, muscle, None))


@router.get("/exercises/{exercise_id}", tags=["Admin - Exercises"], summary="Карточка упражнения")
async def exercise_detail(
    exercise_id: int, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.get_exercise(exercise_id))


async def _save_media(files: list[UploadFile] | None, folder: str, allowed: set[str]) -> list[str]:
    urls: list[str] = []
    for upload in files or []:
        if not upload or not upload.filename:
            continue
        data = await upload.read()
        urls.append(await save_bytes(data, folder=folder, filename=upload.filename, allowed=allowed))
    return urls


def _csv_list(raw: str | None) -> list[str]:
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            return [str(item) for item in parsed if str(item).strip()]
        except json.JSONDecodeError:
            pass
    return [item.strip() for item in raw.split(",") if item.strip()]


@router.post(
    "/exercises",
    tags=["Admin - Exercises"],
    summary="Создать публичное упражнение",
    description="multipart/form-data. Фото — несколько изображений, видео — один файл.",
)
async def create_exercise(
    _user: Annotated[UserPublic, Depends(get_admin_user)],
    name: str = Form(..., description="Название"),
    primary_muscle: str | None = Form(None),
    equipment: str | None = Form(None),
    exercise_type: str = Form("strength"),
    secondary_muscles: str = Form("", description="Коды мышц через запятую или JSON"),
    photos: list[UploadFile] | None = File(None, description="Фото, можно несколько"),
    video: UploadFile | None = File(None, description="Видео MP4/MOV/WEBM"),
) -> SuccessResponse[dict]:
    payload = ExerciseCreateIn(
        name=name,
        primary_muscle=primary_muscle or None,
        equipment=equipment or None,
        exercise_type=exercise_type,
        secondary_muscles=_csv_list(secondary_muscles),
    )
    created = await cat.create_exercise(None, payload, is_public=True)
    photo_urls = await _save_media(photos, f"exercises/{created['id']}", IMAGE_EXTENSIONS)
    video_urls = await _save_media([video] if video else [], f"exercises/{created['id']}/video", VIDEO_EXTENSIONS)
    data = await cat.set_exercise_media(created["id"], photo_urls, video_urls[0] if video_urls else None)
    return SuccessResponse(data=data)


@router.patch(
    "/exercises/{exercise_id}",
    tags=["Admin - Exercises"],
    summary="Изменить упражнение",
    description="multipart/form-data. `keep_photos` — JSON-массив уже сохранённых URL. Новые фото добавляются. Видео заменяется файлом.",
)
async def update_exercise(
    exercise_id: int,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
    name: str = Form(...),
    primary_muscle: str | None = Form(None),
    equipment: str | None = Form(None),
    exercise_type: str = Form("strength"),
    secondary_muscles: str = Form(""),
    keep_photos: str = Form("[]", description="JSON-массив оставшихся фото URL"),
    photos: list[UploadFile] | None = File(None),
    video: UploadFile | None = File(None),
    clear_video: bool = Form(False),
) -> SuccessResponse[dict]:
    payload = ExerciseCreateIn(
        name=name,
        primary_muscle=primary_muscle or None,
        equipment=equipment or None,
        exercise_type=exercise_type,
        secondary_muscles=_csv_list(secondary_muscles),
    )
    current = await cat.admin_update_exercise(exercise_id, payload)
    kept = _csv_list(keep_photos)
    added = await _save_media(photos, f"exercises/{exercise_id}", IMAGE_EXTENSIONS)
    video_url = current.get("video_url")
    if clear_video:
        video_url = None
    new_video = await _save_media([video] if video else [], f"exercises/{exercise_id}/video", VIDEO_EXTENSIONS)
    if new_video:
        video_url = new_video[0]
    data = await cat.set_exercise_media(exercise_id, kept + added, video_url)
    return SuccessResponse(data=data)


@router.post(
    "/programs/{program_id}/cover",
    tags=["Admin - Programs"],
    summary="Обложка программы",
    description="multipart/form-data. Одно изображение. `clear=true` снимает обложку.",
)
async def upload_program_cover(
    program_id: int,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
    file: UploadFile | None = File(None),
    clear: bool = Form(False),
) -> SuccessResponse[dict]:
    if clear:
        return SuccessResponse(data=await cat.set_program_cover(program_id, None))
    if file is None or not file.filename:
        raise AppError("FILE_REQUIRED", "Загрузите изображение обложки", http_status=400)
    urls = await _save_media([file], f"programs/{program_id}", IMAGE_EXTENSIONS)
    return SuccessResponse(data=await cat.set_program_cover(program_id, urls[0]))


@router.delete(
    "/exercises/{exercise_id}",
    tags=["Admin - Exercises"],
    summary="Удалить упражнение",
    description="Тело запроса не требуется.",
)
async def delete_exercise(
    exercise_id: int, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    await cat.admin_delete_exercise(exercise_id)
    return SuccessResponse(data={"ok": True})
