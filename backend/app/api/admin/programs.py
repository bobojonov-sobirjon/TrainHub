from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.auth import get_admin_user
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.pagination import Page, page_args
from app.schemas.stage import ExerciseCreateIn, ProgramCreateIn, ProgramDayExerciseIn, ProgramDayIn
from app.services import catalog as cat

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


@router.post(
    "/exercises",
    tags=["Admin - Exercises"],
    summary="Создать публичное упражнение",
    description="Упражнение сразу публичное. Коды мышц и оборудования — из справочников.",
)
async def create_exercise(
    payload: ExerciseCreateIn,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
) -> SuccessResponse[dict]:
    created = await cat.create_exercise(None, payload, is_public=True)
    return SuccessResponse(data=created)


@router.patch(
    "/exercises/{exercise_id}",
    tags=["Admin - Exercises"],
    summary="Изменить упражнение",
    description="Полная модель: название, мышцы, оборудование, тип, URL медиа.",
)
async def update_exercise(
    exercise_id: int,
    payload: ExerciseCreateIn,
    _user: Annotated[UserPublic, Depends(get_admin_user)],
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.admin_update_exercise(exercise_id, payload))


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
