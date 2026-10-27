"""DEPRECATED for local demo: use seed_nbek_ready_program.py (1 trainer program).

Legacy multi-catalog seed for Figma «Готовая тренировка» (idempotent).
Prefer: .venv/bin/python scripts/seed_nbek_ready_program.py

Run:  .venv/bin/python scripts/seed_figma_ready_programs.py
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.connection import execute, fetch, fetchrow
from app.db.pool import close_pool, create_pool
from app.services.storage import media_root, public_url

ASSETS = Path(__file__).resolve().parent / "figma_exercises"

# name → (sets, reps_min, reps_max) defaults when linking
EXTRA_EXERCISES = [
    {"name": "Жим с плеч (Гантель)", "primary_muscle": "shoulders", "equipment": "dumbbell", "exercise_type": "strength", "file": "ex1.png"},
    {"name": "Сгибания «Молотки»", "primary_muscle": "arms", "equipment": "dumbbell", "exercise_type": "strength", "file": "circle1.png"},
    {"name": "Тяга к подбородку", "primary_muscle": "shoulders", "equipment": "dumbbell", "exercise_type": "strength", "file": "ex5.png"},
    {"name": "Бабочка (Грудная клетка)", "primary_muscle": "chest", "equipment": "machine", "exercise_type": "strength", "file": "ex1.png"},
    {"name": "Жим ногами (Тренажер)", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "ex2.png"},
    {"name": "Подъем на носки", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "ex5.png"},
    {"name": "Разгибание на трицепс (Блок)", "primary_muscle": "arms", "equipment": "cable", "exercise_type": "strength", "file": "ex3.png"},
    {"name": "Вертикальная тяга (Блок)", "primary_muscle": "back", "equipment": "cable", "exercise_type": "strength", "file": "ex4.png"},
]


async def _upsert_exercise(item: dict) -> int:
    existing = await fetchrow(
        "SELECT id FROM exercises WHERE name = $1 AND is_public = TRUE AND owner_id IS NULL LIMIT 1",
        item["name"],
    )
    if existing:
        exercise_id = int(existing["id"])
    else:
        row = await fetchrow(
            """
            INSERT INTO exercises (
                owner_id, name, equipment, primary_muscle, secondary_muscles,
                exercise_type, is_public
            ) VALUES (NULL, $1, $2, $3, $4, $5, TRUE)
            RETURNING id
            """,
            item["name"],
            item["equipment"],
            item["primary_muscle"],
            [],
            item["exercise_type"],
        )
        exercise_id = int(row["id"])

    src = ASSETS / item.get("file", "")
    if src.exists():
        dest_dir = media_root() / "exercises" / str(exercise_id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"figma_{src.name}"
        shutil.copyfile(src, dest)
        url = public_url(f"exercises/{exercise_id}/{dest.name}")
        await execute(
            "UPDATE exercises SET photo_url = $2, photo_urls = $3 WHERE id = $1",
            exercise_id,
            url,
            [url],
        )
    return exercise_id


async def _set_cover(program_id: int, cover_file: str) -> None:
    src = ASSETS / cover_file
    if not src.exists():
        alt = Path(__file__).resolve().parents[3] / "app" / "assets" / "images" / "ready" / cover_file.replace(".jpg", ".png")
        src = alt if alt.exists() else src
    if not src.exists():
        print(f"  cover missing {cover_file}")
        return
    dest_dir = media_root() / "programs" / str(program_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"cover{src.suffix}"
    shutil.copyfile(src, dest)
    url = public_url(f"programs/{program_id}/{dest.name}")
    await execute("UPDATE programs SET cover_url = $2 WHERE id = $1", program_id, url)
    print(f"  cover → {url}")


async def _replace_days(program_id: int, days: list[tuple[str, str, list[tuple[str, int, int, int]]]]) -> None:
    week = await fetchrow(
        "SELECT id FROM program_weeks WHERE program_id = $1 ORDER BY week_index LIMIT 1",
        program_id,
    )
    if not week:
        week = await fetchrow(
            """
            INSERT INTO program_weeks (program_id, week_index, title, is_preview)
            VALUES ($1, 1, 'Неделя 1', TRUE) RETURNING id
            """,
            program_id,
        )
    week_id = int(week["id"])

    old_days = await fetch("SELECT id FROM program_days WHERE program_id = $1", program_id)
    for d in old_days:
        await execute("DELETE FROM program_day_exercises WHERE program_day_id = $1", int(d["id"]))
    await execute("DELETE FROM program_days WHERE program_id = $1", program_id)

    name_to_id: dict[str, int] = {}
    for row in await fetch("SELECT id, name FROM exercises WHERE is_public = TRUE"):
        name_to_id[row["name"]] = int(row["id"])

    for di, (title, desc, exercises) in enumerate(days, start=1):
        day = await fetchrow(
            """
            INSERT INTO program_days (program_id, week_id, title, description, sort_order, duration_min, focus_muscles)
            VALUES ($1, $2, $3, $4, $5, 60, $6)
            RETURNING id
            """,
            program_id,
            week_id,
            title,
            desc,
            di,
            [title.lower()],
        )
        day_id = int(day["id"])
        for oi, (ex_name, sets, rmin, rmax) in enumerate(exercises, start=1):
            eid = name_to_id.get(ex_name)
            if not eid:
                # fuzzy: try without parentheses extras
                for k, v in name_to_id.items():
                    if ex_name.split("(")[0].strip() in k:
                        eid = v
                        break
            if not eid:
                print(f"  missing exercise: {ex_name}")
                continue
            await execute(
                """
                INSERT INTO program_day_exercises (
                    program_day_id, exercise_id, sort_order, sets, reps_min, reps_max
                ) VALUES ($1, $2, $3, $4, $5, $6)
                """,
                day_id,
                eid,
                oi,
                sets,
                rmin if rmin > 0 else None,
                rmax if rmax > 0 else None,
            )


async def _upsert_program(
    title: str,
    description: str,
    level: str,
    goals: list[str],
    equipment: list[str],
    cover: str,
    days: list,
) -> int:
    existing = await fetchrow(
        "SELECT id FROM programs WHERE title = $1 AND source = 'catalog' LIMIT 1",
        title,
    )
    if existing:
        program_id = int(existing["id"])
        await execute(
            """
            UPDATE programs SET
                description = $2, level = $3, goals = $4, equipment = $5,
                workouts_per_week = 3, duration_weeks = 4, is_pro = FALSE, status = 'published'
            WHERE id = $1
            """,
            program_id,
            description,
            level,
            goals,
            equipment,
        )
        print(f"Updated program #{program_id} {title}")
    else:
        row = await fetchrow(
            """
            INSERT INTO programs (
                author_id, source, title, description, level, goals, equipment,
                workouts_per_week, duration_weeks, is_pro, status
            ) VALUES (
                NULL, 'catalog', $1, $2, $3, $4, $5, 3, 4, FALSE, 'published'
            ) RETURNING id
            """,
            title,
            description,
            level,
            goals,
            equipment,
        )
        program_id = int(row["id"])
        print(f"Created program #{program_id} {title}")

    await _set_cover(program_id, cover)
    await _replace_days(program_id, days)
    return program_id


async def main() -> None:
    await create_pool()
    try:
        print("Upserting extra exercises…")
        for item in EXTRA_EXERCISES:
            eid = await _upsert_exercise(item)
            print(f"  #{eid} {item['name']}")

        beginner_days = [
            (
                "Жимы",
                "Первая тренировка недели сфокусирована на жимовых мышцах верхней части тела: грудь, плечи и трицепс.",
                [
                    ("Разминка", 1, 0, 0),
                    ("Жим лежа (Штанга)", 3, 10, 12),
                    ("Жим с плеч (Гантель)", 3, 12, 15),
                    ("Бабочка (Грудная клетка)", 3, 15, 20),
                    ("Разгибание на трицепс (Блок)", 3, 15, 20),
                ],
            ),
            (
                "Тяги",
                "Вторая тренировка недели сфокусирована на тяговых мышцах: спина, задние дельты и бицепс.",
                [
                    ("Разминка", 1, 0, 0),
                    ("Вертикальная тяга (Блок)", 3, 10, 12),
                    ("Тяга нижнего блока", 3, 12, 15),
                    ("Шраги (Гантели)", 3, 15, 20),
                    ("Сгибания «Молотки»", 3, 12, 15),
                    ("Тяга к подбородку", 3, 15, 20),
                ],
            ),
            (
                "Ноги",
                "Третья тренировка недели сфокусирована на нижней части тела: квадрицепс, бицепс бедра, ягодицы и икры.",
                [
                    ("Разминка", 1, 0, 0),
                    ("Жим ногами (Тренажер)", 3, 10, 12),
                    ("Сгибание ног лежа", 3, 12, 15),
                    ("Разгибание ног", 3, 15, 20),
                    ("Подъем на носки", 3, 12, 15),
                ],
            ),
        ]

        await _upsert_program(
            "Жимы/тяги/ноги (Начальный)",
            "Базовый комплекс из 3 тренировок в неделю для развития всех групп мышц:\n"
            "Жимы: грудь, плечи и трицепс\n"
            "Тяги: спина и бицепс\n"
            "Ноги: квадрицепсы, бицепс бедра, ягодицы и икры",
            "beginner",
            ["gain_muscle"],
            ["gym", "machine"],
            "cover1.jpg",
            beginner_days,
        )

        mid_full = [
            (
                "Всё тело A",
                "Комплекс на все группы мышц — акцент на базовые движения.",
                [
                    ("Разминка", 1, 0, 0),
                    ("Жим лежа (Штанга)", 3, 8, 12),
                    ("Вертикальная тяга (Блок)", 3, 10, 12),
                    ("Жим ногами (Тренажер)", 3, 10, 12),
                ],
            ),
            (
                "Всё тело B",
                "Второй день полного тела — гантели и тренажёры.",
                [
                    ("Разминка", 1, 0, 0),
                    ("Жим с плеч (Гантель)", 3, 10, 12),
                    ("Тяга нижнего блока", 3, 10, 12),
                    ("Сгибание ног лежа", 3, 12, 15),
                ],
            ),
            (
                "Всё тело C",
                "Третий день — объём и стабилизация.",
                [
                    ("Разминка", 1, 0, 0),
                    ("Бабочка (Грудная клетка)", 3, 12, 15),
                    ("Шраги (Гантели)", 3, 12, 15),
                    ("Подъем на носки", 3, 15, 20),
                ],
            ),
        ]
        await _upsert_program(
            "Всё тело (Средний)",
            "Три полноценные тренировки в неделю на всё тело. Средний уровень.",
            "intermediate",
            ["gain_muscle", "strength"],
            ["gym", "machine"],
            "cover2.jpg",
            mid_full,
        )

        mid_ppl = [
            (t, d.replace("Первая", "Основная").replace("Вторая", "Основная").replace("Третья", "Основная"), ex)
            for t, d, ex in beginner_days
        ]
        # bump volume slightly for intermediate
        mid_ppl2 = []
        for title, desc, exs in mid_ppl:
            mid_ppl2.append(
                (
                    title,
                    desc,
                    [(n, max(sets, 3), rmin or 8, rmax or 12) for n, sets, rmin, rmax in exs],
                )
            )
        await _upsert_program(
            "Жимы/тяги/ноги (Средний)",
            "Сплит жимы / тяги / ноги для среднего уровня. 3 комплекса в неделю.",
            "intermediate",
            ["gain_muscle", "strength"],
            ["gym", "machine"],
            "cover2.jpg",
            mid_ppl2,
        )

        # Also keep alias title visible if older seed used slash spacing
        await execute(
            """
            UPDATE programs SET title = 'Жимы/тяги/ноги (Начальный)', status = 'published', is_pro = FALSE
            WHERE title IN ('Жимы / ноги (Начальный)', 'Жимы/тяги/ноги (Начальный)')
              AND source = 'catalog'
            """
        )
        print("Done.")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
