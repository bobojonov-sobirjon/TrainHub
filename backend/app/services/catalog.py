import json
from uuid import uuid4

from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow
from app.db.transactions import transaction
from app.schemas.stage import (
    ExerciseCreateIn,
    ProgramCreateIn,
    ProgramDayExerciseIn,
    ProgramDayIn,
    ProgramWeekIn,
)

EXERCISE_COLS = """
    id, owner_id, name, photo_url, photo_urls, video_url, equipment, primary_muscle,
    secondary_muscles, exercise_type, is_public, created_at
"""


def _exercise_out(row) -> dict:
    data = dict(row)
    urls = [item for item in (data.get("photo_urls") or []) if item]
    if not urls and data.get("photo_url"):
        urls = [data["photo_url"]]
    data["photo_urls"] = urls
    data["photo_url"] = urls[0] if urls else None
    return data


async def list_exercises(q: str | None, equipment: str | None, muscle: str | None, owner_id: int | None) -> list[dict]:
    args: list = []
    where = ["TRUE"]
    if owner_id is not None:
        args.append(owner_id)
        where = ["(e.is_public = TRUE OR e.owner_id = $1)"]
    if q:
        args.append(f"%{q}%")
        where.append(f"e.name ILIKE ${len(args)}")
    if equipment:
        args.append(equipment)
        where.append(f"e.equipment = ${len(args)}")
    if muscle:
        args.append(muscle)
        where.append(f"(e.primary_muscle = ${len(args)} OR ${len(args)} = ANY(e.secondary_muscles))")
    rows = await fetch(
        f"""
        SELECT {EXERCISE_COLS}
        FROM exercises e
        WHERE {" AND ".join(where)}
        ORDER BY e.is_public DESC, e.created_at DESC
        LIMIT 100
        """,
        *args,
    )
    items = []
    for r in rows:
        item = _exercise_out(r)
        item["has_video"] = bool(item.get("video_url"))
        items.append(item)
    return items


async def get_exercise(exercise_id: int) -> dict:
    row = await fetchrow(
        f"SELECT {EXERCISE_COLS} FROM exercises WHERE id = $1",
        exercise_id,
    )
    if row is None:
        raise AppError("EXERCISE_NOT_FOUND", "Упражнение не найдено", http_status=404)
    data = _exercise_out(row)
    data["has_video"] = bool(data.get("video_url"))
    return data


async def create_exercise(owner_id: int | None, payload: ExerciseCreateIn, *, is_public: bool = False) -> dict:
    photos = [payload.photo_url] if payload.photo_url else []
    row = await fetchrow(
        """
        INSERT INTO exercises (
            owner_id, name, photo_url, photo_urls, video_url, equipment,
            primary_muscle, secondary_muscles, exercise_type, is_public
        )
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        RETURNING id
        """,
        owner_id,
        payload.name,
        payload.photo_url,
        photos,
        payload.video_url,
        payload.equipment,
        payload.primary_muscle,
        payload.secondary_muscles,
        payload.exercise_type,
        is_public,
    )
    return await get_exercise(row["id"])


async def set_exercise_media(exercise_id: int, photo_urls: list[str], video_url: str | None) -> dict:
    await get_exercise(exercise_id)
    await execute(
        """
        UPDATE exercises
        SET photo_urls = $2,
            photo_url = $3,
            video_url = $4
        WHERE id = $1
        """,
        exercise_id,
        photo_urls,
        photo_urls[0] if photo_urls else None,
        video_url,
    )
    return await get_exercise(exercise_id)


async def set_program_cover(program_id: int, cover_url: str | None) -> dict:
    await get_program(program_id, None)
    await execute("UPDATE programs SET cover_url = $2 WHERE id = $1", program_id, cover_url)
    return await get_program(program_id, None)


async def update_exercise(owner_id: int, exercise_id: int, payload: ExerciseCreateIn) -> dict:
    row = await fetchrow("SELECT id, owner_id FROM exercises WHERE id = $1", exercise_id)
    if row is None or row["owner_id"] != owner_id:
        raise AppError("FORBIDDEN", "Можно редактировать только своё упражнение", http_status=403)
    photos = [payload.photo_url] if payload.photo_url else []
    updated = await fetchrow(
        """
        UPDATE exercises
        SET name = $2, photo_url = $3, photo_urls = $4, video_url = $5, equipment = $6,
            primary_muscle = $7, secondary_muscles = $8, exercise_type = $9
        WHERE id = $1
        RETURNING id
        """,
        exercise_id,
        payload.name,
        payload.photo_url,
        photos,
        payload.video_url,
        payload.equipment,
        payload.primary_muscle,
        payload.secondary_muscles,
        payload.exercise_type,
    )
    return await get_exercise(updated["id"])


async def delete_exercise(owner_id: int, exercise_id: int) -> None:
    row = await fetchrow("SELECT owner_id FROM exercises WHERE id = $1", exercise_id)
    if row is None or row["owner_id"] != owner_id:
        raise AppError("FORBIDDEN", "Можно удалить только своё упражнение", http_status=403)
    await execute("DELETE FROM exercises WHERE id = $1", exercise_id)


async def list_saved_programs(user_id: int, page_size: int, offset: int) -> tuple[list[dict], int]:
    """Programs saved by user (Figma «Сохраненные тренировки»)."""
    total = await fetchrow(
        "SELECT COUNT(*) AS total FROM user_programs WHERE user_id = $1",
        user_id,
    )
    rows = await fetch(
        """
        SELECT p.id, p.title, p.cover_url, p.level, p.goals, p.equipment, p.workouts_per_week,
               p.duration_weeks, p.is_pro, p.source, p.status, p.saves_count, p.author_id,
               TRUE AS is_saved, up.saved_at
        FROM user_programs up
        JOIN programs p ON p.id = up.program_id
        WHERE up.user_id = $1
        ORDER BY up.saved_at DESC
        LIMIT $2 OFFSET $3
        """,
        user_id,
        page_size,
        offset,
    )
    return [dict(r) for r in rows], int(total["total"] if total else 0)


async def list_programs(
    *,
    level: str | None,
    goal: str | None,
    equipment: str | None,
    source: str | None,
    author_id: int | None,
    page_size: int,
    offset: int,
    published_only: bool = True,
    q: str | None = None,
    is_pro: bool | None = None,
    status: str | None = None,
    duration_weeks: int | None = None,
) -> tuple[list[dict], int]:
    args: list = []
    if published_only:
        where = ["p.status = 'published'"]
    elif status:
        args.append(status)
        where = [f"p.status = ${len(args)}"]
    else:
        where = ["TRUE"]
    if level:
        args.append(level)
        where.append(f"p.level = ${len(args)}")
    if goal:
        args.append(goal)
        where.append(f"${len(args)} = ANY(p.goals)")
    if equipment:
        args.append(equipment)
        where.append(f"${len(args)} = ANY(p.equipment)")
    if source:
        args.append(source)
        where.append(f"p.source = ${len(args)}")
    if author_id:
        args.append(author_id)
        where.append(f"p.author_id = ${len(args)}")
    if q:
        args.append(f"%{q.strip()}%")
        where.append(f"(p.title ILIKE ${len(args)} OR COALESCE(p.description, '') ILIKE ${len(args)})")
    if is_pro is not None:
        args.append(is_pro)
        where.append(f"p.is_pro = ${len(args)}")
    if duration_weeks is not None:
        args.append(duration_weeks)
        where.append(f"p.duration_weeks = ${len(args)}")
    where_sql = " AND ".join(where)
    total = await fetchrow(f"SELECT COUNT(*) AS total FROM programs p WHERE {where_sql}", *args)
    args.extend([page_size, offset])
    rows = await fetch(
        f"""
        SELECT p.id, p.title, p.cover_url, p.level, p.goals, p.equipment, p.workouts_per_week,
               p.duration_weeks, p.is_pro, p.source, p.status, p.saves_count, p.author_id,
               p.reject_reason, p.submitted_at, p.reviewed_at
        FROM programs p
        WHERE {where_sql}
        ORDER BY p.created_at DESC
        LIMIT ${len(args) - 1} OFFSET ${len(args)}
        """,
        *args,
    )
    return [dict(r) for r in rows], int(total["total"])


async def _user_has_pro(user_id: int | None) -> bool:
    if not user_id:
        return False
    sub = await fetchrow(
        """
        SELECT id FROM subscriptions
        WHERE user_id = $1 AND status = 'active' AND ends_at > NOW()
        LIMIT 1
        """,
        user_id,
    )
    return sub is not None


async def get_program(program_id: int, user_id: int | None) -> dict:
    row = await fetchrow("SELECT * FROM programs WHERE id = $1", program_id)
    if row is None:
        raise AppError("PROGRAM_NOT_FOUND", "Программа не найдена", http_status=404)
    data = dict(row)
    # user_id is None → internal/admin callers (any status).
    # Otherwise: published, own, or actively assigned.
    if user_id is not None and data.get("status") != "published" and data.get("author_id") != user_id:
        assigned = await fetchrow(
            """
            SELECT 1 FROM client_program_assignments
            WHERE program_id = $1 AND client_id = $2 AND status = 'active'
            """,
            program_id,
            user_id,
        )
        if assigned is None:
            raise AppError("PROGRAM_NOT_FOUND", "Программа не найдена", http_status=404)

    weeks = await fetch(
        """
        SELECT id, week_index, title, is_preview
        FROM program_weeks WHERE program_id = $1 ORDER BY week_index, id
        """,
        program_id,
    )
    days = await fetch(
        """
        SELECT id, title, description, sort_order, duration_min, focus_muscles, week_id
        FROM program_days WHERE program_id = $1 ORDER BY sort_order, id
        """,
        program_id,
    )
    saved = False
    if user_id:
        saved_row = await fetchrow(
            "SELECT 1 FROM user_programs WHERE user_id = $1 AND program_id = $2",
            user_id,
            program_id,
        )
        saved = saved_row is not None
    data["is_saved"] = saved
    # Admin/internal (user_id is None) must see full content — never strip exercises.
    if user_id is None:
        has_pro = True
    elif data.get("is_pro"):
        has_pro = await _user_has_pro(user_id)
    else:
        has_pro = True
    week_by_id = {int(w["id"]): dict(w) for w in weeks}

    day_items = []
    for day in days:
        exercises = await fetch(
            """
            SELECT
                pde.id, pde.exercise_id, pde.sort_order, pde.sets, pde.reps_min, pde.reps_max, pde.note,
                pde.video_lesson_id, pde.rest_sec, pde.weight_kg,
                e.name, e.photo_url, e.photo_urls, e.video_url, e.equipment,
                e.primary_muscle, e.secondary_muscles, e.exercise_type,
                vl.video_url AS lesson_video_url, vl.title AS lesson_title, vl.thumbnail_url AS lesson_thumb
            FROM program_day_exercises pde
            JOIN exercises e ON e.id = pde.exercise_id
            LEFT JOIN video_lessons vl ON vl.id = pde.video_lesson_id
            WHERE pde.program_day_id = $1
            ORDER BY pde.sort_order, pde.id
            """,
            day["id"],
        )
        item = dict(day)
        item["exercises"] = []
        for ex in exercises:
            out = _exercise_out(ex)
            lesson_url = ex.get("lesson_video_url")
            if lesson_url:
                out["video_url"] = lesson_url
                out["video_lesson_id"] = ex.get("video_lesson_id")
                out["lesson_title"] = ex.get("lesson_title")
                out["thumbnail_url"] = ex.get("lesson_thumb")
            out["rest_sec"] = ex.get("rest_sec")
            out["weight_kg"] = float(ex["weight_kg"]) if ex.get("weight_kg") is not None else None
            out["has_video"] = bool(out.get("video_url"))
            item["exercises"].append(out)
        day_items.append(item)

    # PRO lock by week.is_preview / week_index (fallback: sort_order // 7)
    for item in day_items:
        if user_id is None:
            item["locked"] = False
            continue
        week = week_by_id.get(int(item["week_id"])) if item.get("week_id") else None
        if week is not None:
            week_index = int(week.get("week_index") or 1)
            is_preview = bool(week.get("is_preview"))
            locked = bool(
                data.get("is_pro")
                and not has_pro
                and data.get("author_id") != user_id
                and not is_preview
                and week_index > 1
            )
        else:
            week_index = int(item.get("sort_order") or 0) // 7
            locked = bool(data.get("is_pro") and week_index > 0 and not has_pro and data.get("author_id") != user_id)
        item["locked"] = locked
        if locked:
            item["exercises"] = []

    data["days"] = day_items
    data["weeks"] = []
    for w in weeks:
        wdict = dict(w)
        wdict["days"] = [d for d in day_items if d.get("week_id") == w["id"]]
        data["weeks"].append(wdict)
    data["has_pro_access"] = bool(
        user_id is None or has_pro or data.get("author_id") == user_id or not data.get("is_pro")
    )
    return data


async def save_program(user_id: int, program_id: int) -> None:
    await get_program(program_id, user_id)
    await execute(
        """
        INSERT INTO user_programs (user_id, program_id) VALUES ($1,$2)
        ON CONFLICT DO NOTHING
        """,
        user_id,
        program_id,
    )
    await execute("UPDATE programs SET saves_count = saves_count + 1 WHERE id = $1", program_id)


async def unsave_program(user_id: int, program_id: int) -> None:
    await execute("DELETE FROM user_programs WHERE user_id = $1 AND program_id = $2", user_id, program_id)


async def duplicate_program(user_id: int, program_id: int) -> dict:
    src = await get_program(program_id, user_id)
    async with transaction() as conn:
        copy = await conn.fetchrow(
            """
            INSERT INTO programs (author_id, source, title, cover_url, description, level, goals, equipment,
                                  workouts_per_week, duration_weeks, is_pro, status)
            SELECT $2, 'user_copy', title || ' (copy)', cover_url, description, level, goals, equipment,
                   workouts_per_week, duration_weeks, FALSE, 'draft'
            FROM programs WHERE id = $1
            RETURNING id
            """,
            program_id,
            user_id,
        )
        days = await conn.fetch("SELECT * FROM program_days WHERE program_id = $1", program_id)
        for day in days:
            new_day = await conn.fetchrow(
                """
                INSERT INTO program_days (program_id, title, description, sort_order, duration_min, focus_muscles)
                VALUES ($1,$2,$3,$4,$5,$6) RETURNING id
                """,
                copy["id"],
                day["title"],
                day["description"],
                day["sort_order"],
                day["duration_min"],
                day["focus_muscles"],
            )
            await conn.execute(
                """
                INSERT INTO program_day_exercises (program_day_id, exercise_id, sort_order, sets, reps_min, reps_max, note)
                SELECT $1, exercise_id, sort_order, sets, reps_min, reps_max, note
                FROM program_day_exercises WHERE program_day_id = $2
                """,
                new_day["id"],
                day["id"],
            )
    return await get_program(copy["id"], user_id)


async def create_program(author_id: int | None, payload: ProgramCreateIn) -> dict:
    row = await fetchrow(
        """
        INSERT INTO programs (author_id, source, title, description, level, goals, equipment,
                              workouts_per_week, duration_weeks, is_pro, status)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
        RETURNING id
        """,
        author_id,
        payload.source,
        payload.title,
        payload.description,
        payload.level,
        payload.goals,
        payload.equipment,
        payload.workouts_per_week,
        payload.duration_weeks,
        payload.is_pro,
        payload.status,
    )
    return await get_program(row["id"], author_id)


async def admin_update_program(program_id: int, payload: ProgramCreateIn) -> dict:
    await get_program(program_id, None)
    await execute(
        """
        UPDATE programs
        SET title = $2, description = $3, level = $4, goals = $5, equipment = $6,
            workouts_per_week = $7, duration_weeks = $8, is_pro = $9, status = $10
        WHERE id = $1
        """,
        program_id,
        payload.title,
        payload.description,
        payload.level,
        payload.goals,
        payload.equipment,
        payload.workouts_per_week,
        payload.duration_weeks,
        payload.is_pro,
        payload.status,
    )
    return await get_program(program_id, None)


async def admin_delete_program(program_id: int) -> None:
    await execute("UPDATE programs SET status = 'archived' WHERE id = $1", program_id)


async def _require_day(program_id: int, day_id: int) -> dict:
    row = await fetchrow(
        "SELECT id, program_id, title FROM program_days WHERE id = $1 AND program_id = $2",
        day_id,
        program_id,
    )
    if row is None:
        raise AppError("PROGRAM_DAY_NOT_FOUND", "День программы не найден", http_status=404)
    return dict(row)


async def create_program_day(program_id: int, payload: ProgramDayIn) -> dict:
    await get_program(program_id, None)
    sort_order = payload.sort_order
    if sort_order is None:
        nxt = await fetchrow(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM program_days WHERE program_id = $1",
            program_id,
        )
        sort_order = int(nxt["n"]) if nxt else 0
    week_id = payload.week_id
    if week_id is not None:
        week = await fetchrow(
            "SELECT id FROM program_weeks WHERE id = $1 AND program_id = $2",
            week_id,
            program_id,
        )
        if week is None:
            raise AppError("PROGRAM_WEEK_NOT_FOUND", "Неделя не найдена", http_status=404)
    await execute(
        """
        INSERT INTO program_days (program_id, week_id, title, description, sort_order, duration_min, focus_muscles)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        """,
        program_id,
        week_id,
        payload.title.strip(),
        payload.description,
        sort_order,
        payload.duration_min,
        payload.focus_muscles,
    )
    return await get_program(program_id, None)


async def update_program_day(program_id: int, day_id: int, payload: ProgramDayIn) -> dict:
    await _require_day(program_id, day_id)
    sort_order = payload.sort_order
    if sort_order is None:
        current = await fetchrow("SELECT sort_order FROM program_days WHERE id = $1", day_id)
        sort_order = int(current["sort_order"]) if current else 0
    await execute(
        """
        UPDATE program_days
        SET title = $3, description = $4, duration_min = $5, focus_muscles = $6, sort_order = $7
        WHERE id = $1 AND program_id = $2
        """,
        day_id,
        program_id,
        payload.title.strip(),
        payload.description,
        payload.duration_min,
        payload.focus_muscles,
        sort_order,
    )
    return await get_program(program_id, None)


async def delete_program_day(program_id: int, day_id: int) -> dict:
    await _require_day(program_id, day_id)
    await execute("DELETE FROM program_days WHERE id = $1 AND program_id = $2", day_id, program_id)
    return await get_program(program_id, None)


async def add_day_exercise(program_id: int, day_id: int, payload: ProgramDayExerciseIn) -> dict:
    await _require_day(program_id, day_id)
    exercise = await fetchrow("SELECT id FROM exercises WHERE id = $1", payload.exercise_id)
    if exercise is None:
        raise AppError("EXERCISE_NOT_FOUND", "Упражнение не найдено", http_status=404)
    sort_order = payload.sort_order
    if sort_order is None:
        nxt = await fetchrow(
            "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM program_day_exercises WHERE program_day_id = $1",
            day_id,
        )
        sort_order = int(nxt["n"]) if nxt else 0
    if payload.video_lesson_id is not None:
        lesson = await fetchrow("SELECT id FROM video_lessons WHERE id = $1", payload.video_lesson_id)
        if lesson is None:
            raise AppError("VIDEO_NOT_FOUND", "Видеоурок не найден", http_status=404)
    await execute(
        """
        INSERT INTO program_day_exercises
            (program_day_id, exercise_id, sort_order, sets, reps_min, reps_max, note, video_lesson_id, rest_sec, weight_kg)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
        """,
        day_id,
        payload.exercise_id,
        sort_order,
        payload.sets,
        payload.reps_min,
        payload.reps_max,
        payload.note,
        payload.video_lesson_id,
        payload.rest_sec,
        payload.weight_kg,
    )
    return await get_program(program_id, None)


async def update_day_exercise(program_id: int, day_id: int, item_id: int, payload: ProgramDayExerciseIn) -> dict:
    await _require_day(program_id, day_id)
    exercise = await fetchrow("SELECT id FROM exercises WHERE id = $1", payload.exercise_id)
    if exercise is None:
        raise AppError("EXERCISE_NOT_FOUND", "Упражнение не найдено", http_status=404)
    sort_order = payload.sort_order
    if sort_order is None:
        current = await fetchrow(
            "SELECT sort_order FROM program_day_exercises WHERE id = $1 AND program_day_id = $2",
            item_id,
            day_id,
        )
        sort_order = int(current["sort_order"]) if current and current["sort_order"] is not None else 0
    row = await fetchrow(
        """
        UPDATE program_day_exercises
        SET exercise_id = $3, sets = $4, reps_min = $5, reps_max = $6, note = $7,
            video_lesson_id = $8, rest_sec = $9, weight_kg = $10, sort_order = $11
        WHERE id = $1 AND program_day_id = $2
        RETURNING id
        """,
        item_id,
        day_id,
        payload.exercise_id,
        payload.sets,
        payload.reps_min,
        payload.reps_max,
        payload.note,
        payload.video_lesson_id,
        payload.rest_sec,
        payload.weight_kg,
        sort_order,
    )
    if row is None:
        raise AppError("PROGRAM_DAY_EXERCISE_NOT_FOUND", "Упражнение дня не найдено", http_status=404)
    return await get_program(program_id, None)


async def reorder_day_exercises(program_id: int, day_id: int, item_ids: list[int]) -> dict:
    await _require_day(program_id, day_id)
    if not item_ids:
        raise AppError("VALIDATION_ERROR", "Список упражнений пуст", http_status=400)
    existing = await fetch(
        "SELECT id FROM program_day_exercises WHERE program_day_id = $1",
        day_id,
    )
    existing_ids = {int(r["id"]) for r in existing}
    if set(item_ids) != existing_ids:
        raise AppError(
            "VALIDATION_ERROR",
            "Список упражнений не совпадает с комплексом",
            http_status=400,
        )
    async with transaction() as conn:
        for index, item_id in enumerate(item_ids):
            await conn.execute(
                """
                UPDATE program_day_exercises
                SET sort_order = $1
                WHERE id = $2 AND program_day_id = $3
                """,
                index,
                item_id,
                day_id,
            )
    return await get_program(program_id, None)


async def delete_day_exercise(program_id: int, day_id: int, item_id: int) -> dict:
    await _require_day(program_id, day_id)
    row = await fetchrow(
        "DELETE FROM program_day_exercises WHERE id = $1 AND program_day_id = $2 RETURNING id",
        item_id,
        day_id,
    )
    if row is None:
        raise AppError("PROGRAM_DAY_EXERCISE_NOT_FOUND", "Упражнение дня не найдено", http_status=404)
    return await get_program(program_id, None)


async def admin_update_exercise(exercise_id: int, payload: ExerciseCreateIn) -> dict:
    await get_exercise(exercise_id)
    await execute(
        """
        UPDATE exercises
        SET name = $2, equipment = $3, primary_muscle = $4, secondary_muscles = $5, exercise_type = $6
        WHERE id = $1
        """,
        exercise_id,
        payload.name,
        payload.equipment,
        payload.primary_muscle,
        payload.secondary_muscles,
        payload.exercise_type,
    )
    return await get_exercise(exercise_id)


async def admin_delete_exercise(exercise_id: int) -> None:
    row = await fetchrow("SELECT id FROM exercises WHERE id = $1", exercise_id)
    if row is None:
        raise AppError("EXERCISE_NOT_FOUND", "Упражнение не найдено", http_status=404)
    # Detach FKs without ON DELETE (program days + session logs), then remove catalog row.
    async with transaction() as conn:
        await conn.execute(
            "DELETE FROM program_day_exercises WHERE exercise_id = $1",
            exercise_id,
        )
        await conn.execute(
            "DELETE FROM session_exercises WHERE exercise_id = $1",
            exercise_id,
        )
        await conn.execute("DELETE FROM exercises WHERE id = $1", exercise_id)


async def _require_author(program_id: int, user_id: int) -> dict:
    row = await fetchrow("SELECT id, author_id FROM programs WHERE id = $1", program_id)
    if row is None:
        raise AppError("PROGRAM_NOT_FOUND", "Программа не найдена", http_status=404)
    if row["author_id"] != user_id:
        raise AppError("FORBIDDEN", "Можно менять только свою программу", http_status=403)
    return dict(row)


async def update_own_program(user_id: int, program_id: int, payload: ProgramCreateIn) -> dict:
    await _require_author(program_id, user_id)
    row = await fetchrow("SELECT status FROM programs WHERE id = $1", program_id)
    current = row["status"] if row else "draft"
    # Author can keep draft / publish / archive without admin moderation.
    if payload.status not in ("draft", "published", "archived", "rejected", "pending_review"):
        payload.status = current if current else "draft"
    if current == "published" and payload.status == "draft":
        payload.status = "published"
    return await admin_update_program(program_id, payload)


async def _demote_if_published(program_id: int, actor_id: int | None, action: str) -> None:
    """No-op: programs stay published after structural edits (moderation disabled)."""
    return


async def delete_own_program(user_id: int, program_id: int) -> None:
    await _require_author(program_id, user_id)
    await admin_delete_program(program_id)


async def share_program(user_id: int, program_id: int) -> dict:
    await get_program(program_id, user_id)
    row = await fetchrow("SELECT share_token FROM programs WHERE id = $1", program_id)
    token = row["share_token"] if row and row["share_token"] else uuid4().hex
    if not row or not row["share_token"]:
        await execute("UPDATE programs SET share_token = $2 WHERE id = $1", program_id, token)
    return {"program_id": program_id, "share_token": token}


async def get_program_by_token(token: str, user_id: int | None) -> dict:
    row = await fetchrow("SELECT id FROM programs WHERE share_token = $1", token)
    if row is None:
        raise AppError("PROGRAM_NOT_FOUND", "Программа не найдена", http_status=404)
    return await get_program(row["id"], user_id)


# ── Course weeks / moderation / client assignment ─────────────────────────────

async def _audit_program(program_id: int, actor_id: int | None, action: str, detail: dict | None = None) -> None:
    await execute(
        """
        INSERT INTO program_audit_log (program_id, actor_id, action, detail)
        VALUES ($1, $2, $3, $4::jsonb)
        """,
        program_id,
        actor_id,
        action,
        json.dumps(detail or {}),
    )


async def create_program_week(program_id: int, payload: ProgramWeekIn, actor_id: int | None = None) -> dict:
    await get_program(program_id, None)
    week_index = payload.week_index
    if week_index is None:
        nxt = await fetchrow(
            "SELECT COALESCE(MAX(week_index), 0) + 1 AS n FROM program_weeks WHERE program_id = $1",
            program_id,
        )
        week_index = int(nxt["n"]) if nxt else 1
    title = payload.title or f"Неделя {week_index}"
    await execute(
        """
        INSERT INTO program_weeks (program_id, week_index, title, is_preview)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (program_id, week_index) DO UPDATE
          SET title = EXCLUDED.title, is_preview = EXCLUDED.is_preview
        """,
        program_id,
        week_index,
        title,
        bool(payload.is_preview),
    )
    await _demote_if_published(program_id, actor_id, "add_week")
    return await get_program(program_id, None)


async def delete_program_week(program_id: int, week_id: int, actor_id: int | None = None) -> dict:
    row = await fetchrow(
        "DELETE FROM program_weeks WHERE id = $1 AND program_id = $2 RETURNING id",
        week_id,
        program_id,
    )
    if row is None:
        raise AppError("PROGRAM_WEEK_NOT_FOUND", "Неделя не найдена", http_status=404)
    await _demote_if_published(program_id, actor_id, "delete_week")
    return await get_program(program_id, None)


async def duplicate_program_week(program_id: int, week_id: int, actor_id: int | None = None) -> dict:
    """Copy week days+exercises into a new week (videos/exercises reused, not duplicated)."""
    src = await fetchrow(
        "SELECT * FROM program_weeks WHERE id = $1 AND program_id = $2",
        week_id,
        program_id,
    )
    if src is None:
        raise AppError("PROGRAM_WEEK_NOT_FOUND", "Неделя не найдена", http_status=404)
    nxt = await fetchrow(
        "SELECT COALESCE(MAX(week_index), 0) + 1 AS n FROM program_weeks WHERE program_id = $1",
        program_id,
    )
    new_index = int(nxt["n"]) if nxt else 1
    async with transaction() as conn:
        new_week = await conn.fetchrow(
            """
            INSERT INTO program_weeks (program_id, week_index, title, is_preview)
            VALUES ($1, $2, $3, FALSE)
            RETURNING id
            """,
            program_id,
            new_index,
            f"{src['title'] or 'Неделя'} (копия)",
        )
        days = await conn.fetch("SELECT * FROM program_days WHERE week_id = $1 ORDER BY sort_order, id", week_id)
        for day in days:
            new_day = await conn.fetchrow(
                """
                INSERT INTO program_days
                    (program_id, week_id, title, description, sort_order, duration_min, focus_muscles)
                VALUES ($1,$2,$3,$4,$5,$6,$7) RETURNING id
                """,
                program_id,
                new_week["id"],
                day["title"],
                day["description"],
                day["sort_order"],
                day["duration_min"],
                day["focus_muscles"],
            )
            await conn.execute(
                """
                INSERT INTO program_day_exercises
                    (program_day_id, exercise_id, sort_order, sets, reps_min, reps_max, note,
                     video_lesson_id, rest_sec, weight_kg)
                SELECT $1, exercise_id, sort_order, sets, reps_min, reps_max, note,
                       video_lesson_id, rest_sec, weight_kg
                FROM program_day_exercises WHERE program_day_id = $2
                """,
                new_day["id"],
                day["id"],
            )
    await _demote_if_published(program_id, actor_id, "duplicate_week")
    return await get_program(program_id, None)


async def submit_program_for_review(user_id: int, program_id: int) -> dict:
    """Publish own program immediately (moderation disabled)."""
    await _require_author(program_id, user_id)
    row = await fetchrow("SELECT status FROM programs WHERE id = $1", program_id)
    status = row["status"] if row else None
    if status not in ("draft", "rejected", "pending_review", "published"):
        raise AppError("INVALID_STATUS", "Опубликовать можно только черновик или отклонённый курс", http_status=400)
    days = await fetchrow("SELECT COUNT(*) AS n FROM program_days WHERE program_id = $1", program_id)
    if not days or int(days["n"]) < 1:
        raise AppError("VALIDATION_ERROR", "Добавьте хотя бы один день тренировки", http_status=400)
    exercises = await fetchrow(
        """
        SELECT COUNT(*) AS n
        FROM program_day_exercises pde
        JOIN program_days pd ON pd.id = pde.program_day_id
        WHERE pd.program_id = $1
        """,
        program_id,
    )
    if not exercises or int(exercises["n"]) < 1:
        raise AppError("VALIDATION_ERROR", "Добавьте хотя бы одно упражнение", http_status=400)
    cover = await fetchrow("SELECT cover_url FROM programs WHERE id = $1", program_id)
    if cover is None or not (cover.get("cover_url") or "").strip():
        raise AppError("VALIDATION_ERROR", "Добавьте обложку программы", http_status=400)
    if status == "published":
        return await get_program(program_id, user_id)
    await execute(
        """
        UPDATE programs
        SET status = 'published', submitted_at = NOW(), reviewed_at = NOW(),
            reviewed_by = $2, reject_reason = NULL
        WHERE id = $1
        """,
        program_id,
        user_id,
    )
    await _audit_program(program_id, user_id, "publish", {"from": status})
    return await get_program(program_id, user_id)


async def approve_program(admin_id: int, program_id: int) -> dict:
    row = await fetchrow("SELECT status FROM programs WHERE id = $1", program_id)
    if row is None:
        raise AppError("PROGRAM_NOT_FOUND", "Программа не найдена", http_status=404)
    if row["status"] != "pending_review":
        raise AppError("INVALID_STATUS", "Одобрить можно только курс на модерации", http_status=400)
    await execute(
        """
        UPDATE programs
        SET status = 'published', reviewed_at = NOW(), reviewed_by = $2, reject_reason = NULL
        WHERE id = $1
        """,
        program_id,
        admin_id,
    )
    await _audit_program(program_id, admin_id, "approve", {"from": row["status"]})
    return await get_program(program_id, None)


async def reject_program(admin_id: int, program_id: int, reason: str) -> dict:
    row = await fetchrow("SELECT status FROM programs WHERE id = $1", program_id)
    if row is None:
        raise AppError("PROGRAM_NOT_FOUND", "Программа не найдена", http_status=404)
    if row["status"] != "pending_review":
        raise AppError("INVALID_STATUS", "Отклонить можно только курс на модерации", http_status=400)
    if not reason or not reason.strip():
        raise AppError("VALIDATION_ERROR", "Укажите причину отклонения", http_status=400)
    await execute(
        """
        UPDATE programs
        SET status = 'rejected', reviewed_at = NOW(), reviewed_by = $2, reject_reason = $3
        WHERE id = $1
        """,
        program_id,
        admin_id,
        reason.strip(),
    )
    await _audit_program(program_id, admin_id, "reject", {"reason": reason.strip(), "from": row["status"]})
    return await get_program(program_id, None)


async def assign_program_to_client(trainer_id: int, program_id: int, link_id: int, note: str | None = None) -> dict:
    prog = await fetchrow("SELECT id, author_id, status, source FROM programs WHERE id = $1", program_id)
    if prog is None:
        raise AppError("PROGRAM_NOT_FOUND", "Программа не найдена", http_status=404)
    if prog["status"] != "published" and prog["author_id"] != trainer_id:
        raise AppError("FORBIDDEN", "Можно назначить только опубликованный или свой курс", http_status=403)
    link = await fetchrow(
        """
        SELECT id, client_id FROM trainer_clients
        WHERE id = $1 AND trainer_id = $2 AND status != 'archived'
        """,
        link_id,
        trainer_id,
    )
    if link is None:
        raise AppError("CLIENT_NOT_FOUND", "Клиент не найден", http_status=404)
    row = await fetchrow(
        """
        INSERT INTO client_program_assignments (program_id, trainer_id, client_id, link_id, note, status)
        VALUES ($1, $2, $3, $4, $5, 'active')
        ON CONFLICT (program_id, client_id) DO UPDATE
          SET status = 'active', revoked_at = NULL, note = EXCLUDED.note, assigned_at = NOW(),
              trainer_id = EXCLUDED.trainer_id, link_id = EXCLUDED.link_id
        RETURNING *
        """,
        program_id,
        trainer_id,
        link["client_id"],
        link_id,
        note,
    )
    return dict(row)


async def revoke_program_assignment(trainer_id: int, assignment_id: int) -> dict:
    row = await fetchrow(
        """
        UPDATE client_program_assignments
        SET status = 'revoked', revoked_at = NOW()
        WHERE id = $1 AND trainer_id = $2
        RETURNING *
        """,
        assignment_id,
        trainer_id,
    )
    if row is None:
        raise AppError("ASSIGNMENT_NOT_FOUND", "Назначение не найдено", http_status=404)
    return dict(row)


async def list_client_assigned_programs(client_id: int) -> list[dict]:
    rows = await fetch(
        """
        SELECT a.id AS assignment_id, a.status AS assignment_status, a.assigned_at, a.note,
               p.id, p.title, p.cover_url, p.level, p.duration_weeks, p.is_pro, p.author_id
        FROM client_program_assignments a
        JOIN programs p ON p.id = a.program_id
        WHERE a.client_id = $1 AND a.status = 'active'
        ORDER BY a.assigned_at DESC
        """,
        client_id,
    )
    return [dict(r) for r in rows]


async def list_trainer_program_assignments(trainer_id: int, link_id: int | None = None) -> list[dict]:
    args: list = [trainer_id]
    where = ["a.trainer_id = $1"]
    if link_id is not None:
        args.append(link_id)
        where.append(f"a.link_id = ${len(args)}")
    rows = await fetch(
        f"""
        SELECT a.*, p.title AS program_title
        FROM client_program_assignments a
        JOIN programs p ON p.id = a.program_id
        WHERE {' AND '.join(where)}
        ORDER BY a.assigned_at DESC
        """,
        *args,
    )
    return [dict(r) for r in rows]
