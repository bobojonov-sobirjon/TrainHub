from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.constants import ROLE_TRAINER
from app.deps.auth import get_app_user
from app.deps.roles import require_trainer
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.pagination import Page, page_args
from app.schemas.stage import (
    ExerciseCreateIn,
    ProgramCreateIn,
    ProgramDayExerciseIn,
    ProgramDayIn,
    SessionCreateIn,
    SessionExerciseIn,
    SetIn,
)
from app.services import catalog as cat
from app.services import sessions as sess

router = APIRouter()


@router.get("/exercises", tags=["Shared - Exercises"], summary="Каталог упражнений")
async def exercises(
    user: Annotated[UserPublic, Depends(get_app_user)],
    q: str | None = None,
    equipment: str | None = None,
    muscle: str | None = None,
) -> SuccessResponse[list]:
    return SuccessResponse(data=await cat.list_exercises(q, equipment, muscle, user.id))


@router.post(
    "/exercises",
    tags=["Shared - Exercises"],
    summary="Создать своё упражнение",
    description="Пользовательское упражнение (не публичное). Коды мышц и оборудования — из справочников.",
)
async def create_ex(
    payload: ExerciseCreateIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.create_exercise(user.id, payload))


@router.patch(
    "/exercises/{exercise_id}",
    tags=["Shared - Exercises"],
    summary="Изменить своё упражнение",
    description="Можно править только упражнение, созданное текущим пользователем. Тело — полная модель упражнения.",
)
async def update_ex(
    exercise_id: int, payload: ExerciseCreateIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.update_exercise(user.id, exercise_id, payload))


@router.delete(
    "/exercises/{exercise_id}",
    tags=["Shared - Exercises"],
    summary="Удалить своё упражнение",
    description="Тело запроса не требуется. Удаляет только своё упражнение.",
)
async def delete_ex(exercise_id: int, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    await cat.delete_exercise(user.id, exercise_id)
    return SuccessResponse(data={"ok": True})


@router.get("/programs", tags=["Shared - Programs"], summary="Готовые программы")
async def programs(
    level: str | None = None,
    goal: str | None = None,
    equipment: str | None = None,
    source: str | None = None,
    author_id: int | None = None,
    q: str | None = None,
    is_pro: bool | None = None,
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await cat.list_programs(
        level=level,
        goal=goal,
        equipment=equipment,
        source=source,
        author_id=author_id,
        page_size=page_size,
        offset=offset,
        q=q,
        is_pro=is_pro,
    )
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/programs/shared/{token}", tags=["Shared - Programs"], summary="Открыть программу по токену")
async def shared_program(
    token: str, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.get_program_by_token(token, user.id))


@router.get("/programs/{program_id}", tags=["Shared - Programs"], summary="Карточка программы")
async def program_detail(
    program_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.get_program(program_id, user.id))


@router.post(
    "/programs",
    tags=["Coach - Programs"],
    summary="Создать программу тренера",
    description="Доступно тренеру. `source` на сервере ставится в `trainer`.",
)
async def create_program(
    payload: ProgramCreateIn, user: Annotated[UserPublic, Depends(require_trainer)]
) -> SuccessResponse[dict]:
    payload.source = "trainer"
    return SuccessResponse(data=await cat.create_program(user.id, payload))


@router.patch(
    "/programs/{program_id}",
    tags=["Coach - Programs"],
    summary="Изменить свою программу",
)
async def update_program(
    program_id: int, payload: ProgramCreateIn, user: Annotated[UserPublic, Depends(require_trainer)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.update_own_program(user.id, program_id, payload))


@router.delete(
    "/programs/{program_id}",
    tags=["Coach - Programs"],
    summary="Архивировать свою программу",
    description="Тело запроса не требуется.",
)
async def delete_program(
    program_id: int, user: Annotated[UserPublic, Depends(require_trainer)]
) -> SuccessResponse[dict]:
    await cat.delete_own_program(user.id, program_id)
    return SuccessResponse(data={"ok": True})


@router.get("/programs/{program_id}/share", tags=["Shared - Programs"], summary="Ссылка на программу")
async def share_program(
    program_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.share_program(user.id, program_id))


@router.post(
    "/programs/{program_id}/days",
    tags=["Coach - Programs"],
    summary="Добавить день в программу",
)
async def add_program_day(
    program_id: int, payload: ProgramDayIn, user: Annotated[UserPublic, Depends(require_trainer)]
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.create_program_day(program_id, payload))


@router.patch(
    "/programs/{program_id}/days/{day_id}",
    tags=["Coach - Programs"],
    summary="Изменить день программы",
)
async def update_program_day(
    program_id: int,
    day_id: int,
    payload: ProgramDayIn,
    user: Annotated[UserPublic, Depends(require_trainer)],
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.update_program_day(program_id, day_id, payload))


@router.delete(
    "/programs/{program_id}/days/{day_id}",
    tags=["Coach - Programs"],
    summary="Удалить день программы",
)
async def delete_program_day(
    program_id: int, day_id: int, user: Annotated[UserPublic, Depends(require_trainer)]
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.delete_program_day(program_id, day_id))


@router.post(
    "/programs/{program_id}/days/{day_id}/exercises",
    tags=["Coach - Programs"],
    summary="Добавить упражнение в день",
)
async def add_program_day_exercise(
    program_id: int,
    day_id: int,
    payload: ProgramDayExerciseIn,
    user: Annotated[UserPublic, Depends(require_trainer)],
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.add_day_exercise(program_id, day_id, payload))


@router.patch(
    "/programs/{program_id}/days/{day_id}/exercises/{item_id}",
    tags=["Coach - Programs"],
    summary="Изменить упражнение дня",
)
async def update_program_day_exercise(
    program_id: int,
    day_id: int,
    item_id: int,
    payload: ProgramDayExerciseIn,
    user: Annotated[UserPublic, Depends(require_trainer)],
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.update_day_exercise(program_id, day_id, item_id, payload))


@router.delete(
    "/programs/{program_id}/days/{day_id}/exercises/{item_id}",
    tags=["Coach - Programs"],
    summary="Убрать упражнение из дня",
)
async def delete_program_day_exercise(
    program_id: int,
    day_id: int,
    item_id: int,
    user: Annotated[UserPublic, Depends(require_trainer)],
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.delete_day_exercise(program_id, day_id, item_id))


@router.post(
    "/programs/{program_id}/save",
    tags=["Shared - Programs"],
    summary="Сохранить программу",
    description="Тело запроса не требуется. Добавляет программу в сохранённые.",
)
async def save(program_id: int, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    await cat.save_program(user.id, program_id)
    return SuccessResponse(data={"ok": True})


@router.delete(
    "/programs/{program_id}/save",
    tags=["Shared - Programs"],
    summary="Убрать программу из сохранённых",
    description="Тело запроса не требуется.",
)
async def unsave(program_id: int, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    await cat.unsave_program(user.id, program_id)
    return SuccessResponse(data={"ok": True})


@router.post(
    "/programs/{program_id}/duplicate",
    tags=["Shared - Programs"],
    summary="Скопировать программу",
    description="Тело запроса не требуется. Создаёт копию со статусом черновика пользователя.",
)
async def duplicate(program_id: int, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.duplicate_program(user.id, program_id))


@router.post(
    "/sessions",
    tags=["Shared - Sessions"],
    summary="Начать тренировку",
    description="Создаёт живую сессию. Можно привязать клиентов, день программы или событие календаря.",
)
async def create_session(
    payload: SessionCreateIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await sess.create_session(user.id, ROLE_TRAINER in user.roles, payload))


@router.get("/sessions/{session_id}", tags=["Shared - Sessions"], summary="Карточка тренировки")
async def session_detail(session_id: int, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await sess.get_session(session_id, user.id, ROLE_TRAINER in user.roles))


@router.post(
    "/sessions/{session_id}/exercises",
    tags=["Shared - Sessions"],
    summary="Добавить упражнение в сессию",
    description="`exercise_id` обязателен. `rest_sec` — отдых после упражнения.",
)
async def add_ex(
    session_id: int, payload: SessionExerciseIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(
        data=await sess.add_exercise(
            session_id, user.id, ROLE_TRAINER in user.roles, payload.exercise_id, payload.rest_sec
        )
    )


@router.post(
    "/sessions/{session_id}/exercises/{se_id}/sets",
    tags=["Shared - Sessions"],
    summary="Добавить подход",
    description="`se_id` — ID упражнения внутри сессии. Вес и повторения можно не указывать.",
)
async def add_set(
    session_id: int, se_id: int, payload: SetIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await sess.add_set(session_id, se_id, user.id, ROLE_TRAINER in user.roles, payload))


@router.post(
    "/sessions/{session_id}/complete",
    tags=["Shared - Sessions"],
    summary="Завершить тренировку",
    description="Тело запроса не требуется. Помечает сессию выполненной.",
)
async def complete(session_id: int, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await sess.complete_session(session_id, user.id, ROLE_TRAINER in user.roles))


@router.get("/sessions/{session_id}/previous/{exercise_id}", tags=["Shared - Sessions"], summary="Прошлый результат")
async def previous(
    session_id: int,
    exercise_id: int,
    user: Annotated[UserPublic, Depends(get_app_user)],
    client_id: int | None = None,
) -> SuccessResponse[list]:
    cid = client_id or user.id
    return SuccessResponse(data=await sess.previous_sets(session_id, exercise_id, cid))
