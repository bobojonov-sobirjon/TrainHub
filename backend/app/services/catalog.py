from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow
from app.db.transactions import transaction
from app.schemas.stage import ExerciseCreateIn, ProgramCreateIn, ProgramDayExerciseIn, ProgramDayIn


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
        SELECT id, owner_id, name, photo_url, video_url, equipment, primary_muscle,
               secondary_muscles, exercise_type, is_public, created_at
        FROM exercises e
        WHERE {" AND ".join(where)}
        ORDER BY e.is_public DESC, e.created_at DESC
        LIMIT 100
        """,
        *args,
    )
    return [dict(r) for r in rows]


async def get_exercise(exercise_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT id, owner_id, name, photo_url, video_url, equipment, primary_muscle,
               secondary_muscles, exercise_type, is_public, created_at
        FROM exercises WHERE id = $1
        """,
        exercise_id,
    )
    if row is None:
        raise AppError("EXERCISE_NOT_FOUND", "Упражнение не найдено", http_status=404)
    return dict(row)


async def create_exercise(owner_id: int | None, payload: ExerciseCreateIn, *, is_public: bool = False) -> dict:
    row = await fetchrow(
        """
        INSERT INTO exercises (owner_id, name, photo_url, video_url, equipment, primary_muscle, secondary_muscles, exercise_type, is_public)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
        RETURNING id, owner_id, name, photo_url, video_url, equipment, primary_muscle, secondary_muscles, exercise_type, is_public
        """,
        owner_id,
        payload.name,
        payload.photo_url,
        payload.video_url,
        payload.equipment,
        payload.primary_muscle,
        payload.secondary_muscles,
        payload.exercise_type,
        is_public,
    )
    return dict(row)


async def update_exercise(owner_id: int, exercise_id: int, payload: ExerciseCreateIn) -> dict:
    row = await fetchrow("SELECT id, owner_id FROM exercises WHERE id = $1", exercise_id)
    if row is None or row["owner_id"] != owner_id:
        raise AppError("FORBIDDEN", "Можно редактировать только своё упражнение", http_status=403)
    updated = await fetchrow(
        """
        UPDATE exercises
        SET name = $2, photo_url = $3, video_url = $4, equipment = $5,
            primary_muscle = $6, secondary_muscles = $7, exercise_type = $8
        WHERE id = $1
        RETURNING id, owner_id, name, photo_url, video_url, equipment, primary_muscle, secondary_muscles, exercise_type, is_public
        """,
        exercise_id,
        payload.name,
        payload.photo_url,
        payload.video_url,
        payload.equipment,
        payload.primary_muscle,
        payload.secondary_muscles,
        payload.exercise_type,
    )
    return dict(updated)


async def delete_exercise(owner_id: int, exercise_id: int) -> None:
    row = await fetchrow("SELECT owner_id FROM exercises WHERE id = $1", exercise_id)
    if row is None or row["owner_id"] != owner_id:
        raise AppError("FORBIDDEN", "Можно удалить только своё упражнение", http_status=403)
    await execute("DELETE FROM exercises WHERE id = $1", exercise_id)


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
) -> tuple[list[dict], int]:
    args: list = []
    where = ["p.status = 'published'"] if published_only else ["TRUE"]
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
    where_sql = " AND ".join(where)
    total = await fetchrow(f"SELECT COUNT(*) AS total FROM programs p WHERE {where_sql}", *args)
    args.extend([page_size, offset])
    rows = await fetch(
        f"""
        SELECT p.id, p.title, p.cover_url, p.level, p.goals, p.equipment, p.workouts_per_week,
               p.duration_weeks, p.is_pro, p.source, p.saves_count, p.author_id
        FROM programs p
        WHERE {where_sql}
        ORDER BY p.created_at DESC
        LIMIT ${len(args) - 1} OFFSET ${len(args)}
        """,
        *args,
    )
    return [dict(r) for r in rows], int(total["total"])


async def get_program(program_id: int, user_id: int | None) -> dict:
    row = await fetchrow("SELECT * FROM programs WHERE id = $1", program_id)
    if row is None:
        raise AppError("PROGRAM_NOT_FOUND", "Программа не найдена", http_status=404)
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
    data = dict(row)
    data["is_saved"] = saved
    day_items = []
    for day in days:
        exercises = await fetch(
            """
            SELECT pde.id, pde.exercise_id, pde.sort_order, pde.sets, pde.reps_min, pde.reps_max, pde.note, e.name
            FROM program_day_exercises pde
            JOIN exercises e ON e.id = pde.exercise_id
            WHERE pde.program_day_id = $1
            ORDER BY pde.sort_order, pde.id
            """,
            day["id"],
        )
        item = dict(day)
        item["exercises"] = [dict(e) for e in exercises]
        day_items.append(item)
    data["days"] = day_items
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
    await execute(
        """
        INSERT INTO program_days (program_id, title, description, sort_order, duration_min, focus_muscles)
        VALUES ($1,$2,$3,$4,$5,$6)
        """,
        program_id,
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
    await execute(
        """
        INSERT INTO program_day_exercises (program_day_id, exercise_id, sort_order, sets, reps_min, reps_max, note)
        VALUES ($1,$2,$3,$4,$5,$6,$7)
        """,
        day_id,
        payload.exercise_id,
        sort_order,
        payload.sets,
        payload.reps_min,
        payload.reps_max,
        payload.note,
    )
    return await get_program(program_id, None)


async def update_day_exercise(program_id: int, day_id: int, item_id: int, payload: ProgramDayExerciseIn) -> dict:
    await _require_day(program_id, day_id)
    exercise = await fetchrow("SELECT id FROM exercises WHERE id = $1", payload.exercise_id)
    if exercise is None:
        raise AppError("EXERCISE_NOT_FOUND", "Упражнение не найдено", http_status=404)
    row = await fetchrow(
        """
        UPDATE program_day_exercises
        SET exercise_id = $3, sets = $4, reps_min = $5, reps_max = $6, note = $7
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
    )
    if row is None:
        raise AppError("PROGRAM_DAY_EXERCISE_NOT_FOUND", "Упражнение дня не найдено", http_status=404)
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
    row = await fetchrow(
        """
        UPDATE exercises
        SET name = $2, photo_url = $3, video_url = $4, equipment = $5,
            primary_muscle = $6, secondary_muscles = $7, exercise_type = $8
        WHERE id = $1
        RETURNING id, owner_id, name, photo_url, video_url, equipment, primary_muscle, secondary_muscles, exercise_type, is_public
        """,
        exercise_id,
        payload.name,
        payload.photo_url,
        payload.video_url,
        payload.equipment,
        payload.primary_muscle,
        payload.secondary_muscles,
        payload.exercise_type,
    )
    if row is None:
        raise AppError("EXERCISE_NOT_FOUND", "Упражнение не найдено", http_status=404)
    return dict(row)


async def admin_delete_exercise(exercise_id: int) -> None:
    row = await fetchrow("SELECT id FROM exercises WHERE id = $1", exercise_id)
    if row is None:
        raise AppError("EXERCISE_NOT_FOUND", "Упражнение не найдено", http_status=404)
    await execute("DELETE FROM exercises WHERE id = $1", exercise_id)
