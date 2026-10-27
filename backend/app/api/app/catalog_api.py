from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.constants import ROLE_TRAINER
from app.core.exceptions import AppError
from app.deps.auth import get_app_user
from app.deps.roles import require_trainer
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.pagination import Page, page_args
from app.schemas.stage import (
    AssignProgramIn,
    ExerciseCreateIn,
    ProgramCreateIn,
    ProgramDayExerciseIn,
    ProgramDayIn,
    ProgramWeekIn,
    ReorderDayExercisesIn,
    SessionCreateIn,
    SessionExerciseIn,
    SetIn,
)
from app.services import catalog as cat
from app.services import sessions as sess
from app.services.storage import IMAGE_EXTENSIONS, save_bytes

router = APIRouter()


@router.get("/exercises", tags=["Shared - Exercises"], summary="Каталог упражнений")
async def exercises(
    user: Annotated[UserPublic, Depends(get_app_user)],
    q: str | None = None,
    equipment: str | None = None,
    muscle: str | None = None,
) -> SuccessResponse[list]:
    return SuccessResponse(data=await cat.list_exercises(q, equipment, muscle, user.id))


@router.get(
    "/exercises/{exercise_id}",
    tags=["Shared - Exercises"],
    summary="Карточка упражнения",
    description="Имя, мышцы, оборудование, фото и `video_url`. Нет видео — `video_url` null, `has_video` false.",
)
async def exercise_detail(
    exercise_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    data = await cat.get_exercise(exercise_id)
    data["has_video"] = bool(data.get("video_url"))
    return SuccessResponse(data=data)


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
    duration_weeks: int | None = None,
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
        duration_weeks=duration_weeks,
    )
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/programs/shared/{token}", tags=["Shared - Programs"], summary="Открыть программу по токену")
async def shared_program(
    token: str, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.get_program_by_token(token, user.id))


@router.get(
    "/programs/{program_id}",
    tags=["Shared - Programs"],
    summary="Карточка программы",
    description=(
        "Дни и упражнения. У каждого упражнения: `video_url`, `has_video`, фото, мышцы, sets/reps. "
        "Видео — ссылка, не отдельная платформа. PRO-дни без подписки: `locked=true`, exercises пустой."
    ),
)
async def program_detail(
    program_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.get_program(program_id, user.id))


@router.post(
    "/programs",
    tags=["Shared - Programs"],
    summary="Создать программу",
    description="Тренер: source=`trainer`. Клиент (своя тренировка): source=`user_copy`. Всегда черновик.",
)
async def create_program(
    payload: ProgramCreateIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    is_trainer = ROLE_TRAINER in user.roles
    payload.source = "trainer" if is_trainer else "user_copy"
    payload.status = "draft"
    if not is_trainer:
        payload.is_pro = False
    return SuccessResponse(data=await cat.create_program(user.id, payload))


@router.patch(
    "/programs/{program_id}",
    tags=["Shared - Programs"],
    summary="Изменить свою программу",
)
async def update_program(
    program_id: int, payload: ProgramCreateIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.update_own_program(user.id, program_id, payload))


@router.delete(
    "/programs/{program_id}",
    tags=["Shared - Programs"],
    summary="Архивировать свою программу",
    description="Тело запроса не требуется.",
)
async def delete_program(
    program_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    await cat.delete_own_program(user.id, program_id)
    return SuccessResponse(data={"ok": True})


@router.post(
    "/programs/{program_id}/cover",
    tags=["Shared - Programs"],
    summary="Обложка своей программы",
    description="multipart/form-data, поле `file`. `clear=true` снимает обложку.",
)
async def upload_program_cover(
    program_id: int,
    user: Annotated[UserPublic, Depends(get_app_user)],
    file: UploadFile | None = File(None),
    clear: bool = Form(False),
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    if clear:
        return SuccessResponse(data=await cat.set_program_cover(program_id, None))
    if file is None or not file.filename:
        raise AppError("FILE_REQUIRED", "Загрузите изображение обложки", http_status=400)
    data = await file.read()
    url = await save_bytes(data, folder=f"programs/{program_id}", filename=file.filename, allowed=IMAGE_EXTENSIONS)
    return SuccessResponse(data=await cat.set_program_cover(program_id, url))


@router.get("/programs/{program_id}/share", tags=["Shared - Programs"], summary="Ссылка на программу")
async def share_program(
    program_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.share_program(user.id, program_id))


@router.post(
    "/programs/{program_id}/days",
    tags=["Shared - Programs"],
    summary="Добавить день в программу",
)
async def add_program_day(
    program_id: int, payload: ProgramDayIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.create_program_day(program_id, payload))


@router.patch(
    "/programs/{program_id}/days/{day_id}",
    tags=["Shared - Programs"],
    summary="Изменить день программы",
)
async def update_program_day(
    program_id: int,
    day_id: int,
    payload: ProgramDayIn,
    user: Annotated[UserPublic, Depends(get_app_user)],
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.update_program_day(program_id, day_id, payload))


@router.delete(
    "/programs/{program_id}/days/{day_id}",
    tags=["Shared - Programs"],
    summary="Удалить день программы",
)
async def delete_program_day(
    program_id: int, day_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.delete_program_day(program_id, day_id))


@router.post(
    "/programs/{program_id}/days/{day_id}/exercises",
    tags=["Shared - Programs"],
    summary="Добавить упражнение в день",
)
async def add_program_day_exercise(
    program_id: int,
    day_id: int,
    payload: ProgramDayExerciseIn,
    user: Annotated[UserPublic, Depends(get_app_user)],
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.add_day_exercise(program_id, day_id, payload))


@router.put(
    "/programs/{program_id}/days/{day_id}/exercises/reorder",
    tags=["Shared - Programs"],
    summary="Изменить порядок упражнений в дне",
)
async def reorder_program_day_exercises(
    program_id: int,
    day_id: int,
    payload: ReorderDayExercisesIn,
    user: Annotated[UserPublic, Depends(get_app_user)],
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.reorder_day_exercises(program_id, day_id, payload.item_ids))


@router.patch(
    "/programs/{program_id}/days/{day_id}/exercises/{item_id}",
    tags=["Shared - Programs"],
    summary="Изменить упражнение дня",
)
async def update_program_day_exercise(
    program_id: int,
    day_id: int,
    item_id: int,
    payload: ProgramDayExerciseIn,
    user: Annotated[UserPublic, Depends(get_app_user)],
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.update_day_exercise(program_id, day_id, item_id, payload))


@router.delete(
    "/programs/{program_id}/days/{day_id}/exercises/{item_id}",
    tags=["Shared - Programs"],
    summary="Убрать упражнение из дня",
)
async def delete_program_day_exercise(
    program_id: int,
    day_id: int,
    item_id: int,
    user: Annotated[UserPublic, Depends(get_app_user)],
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
    "/programs/{program_id}/weeks",
    tags=["Shared - Programs"],
    summary="Добавить неделю курса",
)
async def add_program_week(
    program_id: int, payload: ProgramWeekIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.create_program_week(program_id, payload, actor_id=user.id))


@router.delete(
    "/programs/{program_id}/weeks/{week_id}",
    tags=["Shared - Programs"],
    summary="Удалить неделю курса",
)
async def delete_program_week(
    program_id: int, week_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.delete_program_week(program_id, week_id, actor_id=user.id))


@router.post(
    "/programs/{program_id}/weeks/{week_id}/duplicate",
    tags=["Shared - Programs"],
    summary="Повторить неделю (дни и упражнения, видео без дублей)",
)
async def duplicate_program_week(
    program_id: int, week_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    await cat._require_author(program_id, user.id)
    return SuccessResponse(data=await cat.duplicate_program_week(program_id, week_id, actor_id=user.id))


@router.post(
    "/programs/{program_id}/submit",
    tags=["Shared - Programs"],
    summary="Опубликовать программу",
    description="Модерация отключена: сразу status=`published` (нужны обложка, день и ≥1 упражнение).",
)
async def submit_program(
    program_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.submit_program_for_review(user.id, program_id))


@router.post(
    "/programs/{program_id}/assign",
    tags=["Coach - Programs"],
    summary="Назначить курс одному или нескольким клиентам",
)
async def assign_program(
    program_id: int, payload: AssignProgramIn, user: Annotated[UserPublic, Depends(require_trainer)]
) -> SuccessResponse[list]:
    return SuccessResponse(
        data=await cat.assign_program_to_clients(
            user.id, program_id, payload.link_ids or [payload.link_id], payload.note
        )
    )


@router.delete(
    "/trainer/program-assignments/{assignment_id}",
    tags=["Coach - Programs"],
    summary="Снять назначение курса",
)
async def revoke_program_assignment(
    assignment_id: int, user: Annotated[UserPublic, Depends(require_trainer)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await cat.revoke_program_assignment(user.id, assignment_id))


@router.get(
    "/me/assigned-programs",
    tags=["Client - Programs"],
    summary="Курсы, назначенные мне",
)
async def my_assigned_programs(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await cat.list_client_assigned_programs(user.id))


@router.get(
    "/me/saved-programs",
    tags=["Shared - Programs"],
    summary="Сохранённые тренировки",
)
async def my_saved_programs(
    user: Annotated[UserPublic, Depends(get_app_user)],
    page: int = 1,
    page_size: int = 50,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await cat.list_saved_programs(user.id, page_size, offset)
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get(
    "/me/programs",
    tags=["Client - Programs"],
    summary="Мои свои тренировки (все статусы)",
    description="Черновики и готовые комплексы текущего пользователя (`author_id=me`).",
)
async def my_own_programs(
    user: Annotated[UserPublic, Depends(get_app_user)],
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await cat.list_programs(
        level=None,
        goal=None,
        equipment=None,
        source=None,
        author_id=user.id,
        page_size=page_size,
        offset=offset,
        published_only=False,
        status=status,
    )
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get(
    "/trainer/programs",
    tags=["Coach - Programs"],
    summary="Мои курсы (все статусы)",
)
async def my_programs(
    user: Annotated[UserPublic, Depends(require_trainer)],
    status: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await cat.list_programs(
        level=None,
        goal=None,
        equipment=None,
        source=None,
        author_id=user.id,
        page_size=page_size,
        offset=offset,
        published_only=False,
        status=status,
    )
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.post(
    "/sessions",
    tags=["Shared - Sessions"],
    summary="Начать тренировку",
    description=(
        "Создаёт живую сессию. Coach передаёт `client_ids`. "
        "Client начинает свою тренировку без тренера: `client_ids` игнорируется, `trainer_id` будет null. "
        "Если есть незавершённая тренировка (in_progress, активность < 1ч) — 409 ACTIVE_SESSION_EXISTS. "
        "Сессии без активности 1ч+ помечаются abandoned."
    ),
)
async def create_session(
    payload: SessionCreateIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await sess.create_session(user.id, ROLE_TRAINER in user.roles, payload))


@router.get(
    "/me/active-session",
    tags=["Shared - Sessions"],
    summary="Активная незавершённая тренировка",
    description="null если нет. Просроченные (>1ч без активности) автоматически abandoned.",
)
async def my_active_session(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict | None]:
    return SuccessResponse(data=await sess.find_active_session_for_user(user.id))


@router.get("/sessions/{session_id}", tags=["Shared - Sessions"], summary="Карточка тренировки")
async def session_detail(session_id: int, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await sess.get_session(session_id, user.id, ROLE_TRAINER in user.roles))


@router.post(
    "/sessions/{session_id}/exercises",
    tags=["Shared - Sessions"],
    summary="Добавить упражнение в сессию",
    description="`exercise_id` обязателен. `rest_sec` — отдых. `sets`/`reps` — как в дне программы: создают запланированные подходы.",
)
async def add_ex(
    session_id: int, payload: SessionExerciseIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(
        data=await sess.add_exercise(
            session_id,
            user.id,
            ROLE_TRAINER in user.roles,
            payload.exercise_id,
            payload.rest_sec,
            sets=payload.sets,
            reps=payload.reps,
        )
    )


@router.delete(
    "/sessions/{session_id}/exercises/{se_id}",
    tags=["Shared - Sessions"],
    summary="Убрать упражнение из сессии",
    description="Удаляет упражнение и его подходы из текущей тренировки.",
)
async def delete_ex(
    session_id: int, se_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(
        data=await sess.delete_exercise(session_id, se_id, user.id, ROLE_TRAINER in user.roles)
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
    "/sessions/{session_id}/pause",
    tags=["Shared - Sessions"],
    summary="Пауза тренировки",
    description="Останавливает таймер. Пока на паузе — сессия не abandoned по таймауту 1ч.",
)
async def pause_session(session_id: int, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await sess.pause_session(session_id, user.id, ROLE_TRAINER in user.roles))


@router.post(
    "/sessions/{session_id}/resume",
    tags=["Shared - Sessions"],
    summary="Продолжить тренировку",
    description="Снимает паузу и продолжает таймер.",
)
async def resume_session(session_id: int, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await sess.resume_session(session_id, user.id, ROLE_TRAINER in user.roles))


@router.post(
    "/sessions/{session_id}/complete",
    tags=["Shared - Sessions"],
    summary="Завершить тренировку",
    description="Тело запроса не требуется. Помечает сессию выполненной.",
)
async def complete(session_id: int, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await sess.complete_session(session_id, user.id, ROLE_TRAINER in user.roles))


@router.patch(
    "/sessions/{session_id}/sets/{set_id}",
    tags=["Shared - Sessions"],
    summary="Изменить подход",
    description="Обновляет вес, повторения или флаг разминки у подхода текущей сессии.",
)
async def patch_set(
    session_id: int, set_id: int, payload: SetIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(
        data=await sess.patch_set(session_id, set_id, user.id, ROLE_TRAINER in user.roles, payload)
    )


@router.get(
    "/sessions/{session_id}/previous/{exercise_id}",
    tags=["Shared - Sessions"],
    summary="Прошлый результат",
    description=(
        "Подходы прошлого завершённого занятия по этому упражнению: вес и повторения. "
        "Client всегда видит свои. Coach может передать `client_id` своего ученика."
    ),
)
async def previous(
    session_id: int,
    exercise_id: int,
    user: Annotated[UserPublic, Depends(get_app_user)],
    client_id: int | None = None,
) -> SuccessResponse[list]:
    return SuccessResponse(
        data=await sess.previous_sets(
            session_id,
            exercise_id,
            user.id,
            ROLE_TRAINER in user.roles,
            client_id,
        )
    )
