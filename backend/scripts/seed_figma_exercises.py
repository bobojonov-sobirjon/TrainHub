"""Seed public catalog exercises from Figma assets (Готовая тренировка).

Idempotent by exercise name. Copies PNGs into media/exercises/{id}/.

Run from backend dir:
  .venv/bin/python scripts/seed_figma_exercises.py
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.connection import execute, fetchrow
from app.db.pool import close_pool, create_pool
from app.services.storage import media_root, public_url

ASSETS = Path(__file__).resolve().parent / "figma_exercises"

EXERCISES: list[dict] = [
    {"name": "Разминка", "primary_muscle": "full_body", "equipment": "bodyweight", "exercise_type": "stretching", "file": "warm.png"},
    {"name": "Жим лежа (Штанга)", "primary_muscle": "chest", "equipment": "barbell", "exercise_type": "strength", "file": "bench.png"},
    {"name": "Жим лежа (Гантели)", "primary_muscle": "chest", "equipment": "dumbbell", "exercise_type": "strength", "file": "ex2.png"},
    {"name": "Бабочка (Грудные мышцы)", "primary_muscle": "chest", "equipment": "machine", "exercise_type": "strength", "file": "ex1.png"},
    {"name": "Разгибание на трицепс", "primary_muscle": "arms", "equipment": "cable", "exercise_type": "strength", "file": "ex3.png"},
    {"name": "Вертикальная тяга", "primary_muscle": "back", "equipment": "machine", "exercise_type": "strength", "file": "ex4.png"},
    {"name": "Тяга нижнего блока", "primary_muscle": "back", "equipment": "cable", "exercise_type": "strength", "file": "ex5.png"},
    {"name": "Шраги (Гантели)", "primary_muscle": "traps", "equipment": "dumbbell", "exercise_type": "strength", "file": "circle1.png"},
    {"name": "Жимы ногами", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "ex2.png"},
    {"name": "Сгибание ног лежа", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "ex3.png"},
    {"name": "Разгибание ног", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "ex4.png"},
    {"name": "Подъем носков стоя", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "ex5.png"},
    {"name": "Жим гантелей сидя", "primary_muscle": "shoulders", "equipment": "dumbbell", "exercise_type": "strength", "file": "ex1.png"},
    {"name": "Разведение гантелей в стороны", "primary_muscle": "shoulders", "equipment": "dumbbell", "exercise_type": "strength", "file": "circle1.png"},
    {"name": "Жим в тренажере (грудь)", "primary_muscle": "chest", "equipment": "machine", "exercise_type": "strength", "file": "bench.png"},
]


async def _upsert(item: dict) -> int:
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

    src = ASSETS / item["file"]
    if not src.exists():
        print(f"  skip media (missing {src.name})")
        return exercise_id

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
    print(f"  #{exercise_id} {item['name']} → {url}")
    return exercise_id


async def _seed_program(exercise_ids: dict[str, int]) -> None:
    title = "Жимы/тяги/ноги (Начальный)"
    existing = await fetchrow(
        "SELECT id FROM programs WHERE title = $1 AND source = 'catalog' LIMIT 1",
        title,
    )
    cover_src = Path(__file__).resolve().parents[3] / "app" / "assets" / "images" / "bg_ready.png"
    if existing:
        program_id = int(existing["id"])
        if cover_src.exists():
            dest_dir = media_root() / "programs" / str(program_id)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / "cover.png"
            shutil.copyfile(cover_src, dest)
            url = public_url(f"programs/{program_id}/cover.png")
            await execute("UPDATE programs SET cover_url = $2 WHERE id = $1", program_id, url)
            print(f"Program already exists #{program_id} (cover refreshed)")
        else:
            print(f"Program already exists #{program_id}")
        return

    row = await fetchrow(
        """
        INSERT INTO programs (
            author_id, source, title, description, level, goals, equipment,
            workouts_per_week, duration_weeks, is_pro, status
        ) VALUES (
            NULL, 'catalog', $1, $2, 'beginner',
            ARRAY['gain_muscle'], ARRAY['gym','machine'],
            3, 4, FALSE, 'published'
        )
        RETURNING id
        """,
        title,
        "Базовый комплекс 3 раза в неделю на все группы мышц.\n"
        "• Жимы: грудь / плечи / трицепс\n"
        "• Тяги: спина / бицепс\n"
        "• Ноги: квадрицепс / бицепс бедра / икры",
    )
    program_id = int(row["id"])
    if cover_src.exists():
        dest_dir = media_root() / "programs" / str(program_id)
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / "cover.png"
        shutil.copyfile(cover_src, dest)
        await execute(
            "UPDATE programs SET cover_url = $2 WHERE id = $1",
            program_id,
            public_url(f"programs/{program_id}/cover.png"),
        )
    week = await fetchrow(
        """
        INSERT INTO program_weeks (program_id, week_index, title, is_preview)
        VALUES ($1, 1, 'Неделя 1', TRUE)
        RETURNING id
        """,
        program_id,
    )
    week_id = int(week["id"])

    days = [
        ("Жимы", "Фокус на грудь, плечи и трицепс", ["Разминка", "Жим лежа (Штанга)", "Жим лежа (Гантели)", "Бабочка (Грудные мышцы)", "Разгибание на трицепс"]),
        ("Тяги", "Фокус на спину и бицепс", ["Разминка", "Вертикальная тяга", "Тяга нижнего блока", "Шраги (Гантели)"]),
        ("Ноги", "Фокус на квадрицепс, бицепс бедра и икры", ["Разминка", "Жимы ногами", "Сгибание ног лежа", "Разгибание ног", "Подъем носков стоя"]),
    ]
    for di, (day_title, desc, names) in enumerate(days, start=1):
        day = await fetchrow(
            """
            INSERT INTO program_days (program_id, week_id, title, description, sort_order, duration_min, focus_muscles)
            VALUES ($1, $2, $3, $4, $5, 60, $6)
            RETURNING id
            """,
            program_id,
            week_id,
            day_title,
            desc,
            di,
            [day_title.lower()],
        )
        day_id = int(day["id"])
        for oi, name in enumerate(names, start=1):
            eid = exercise_ids.get(name)
            if not eid:
                continue
            await execute(
                """
                INSERT INTO program_day_exercises (
                    program_day_id, exercise_id, sort_order, sets, reps_min, reps_max
                ) VALUES ($1, $2, $3, 3, 12, 15)
                """,
                day_id,
                eid,
                oi,
            )
    print(f"Program created #{program_id}")


async def main() -> None:
    if not ASSETS.exists():
        raise SystemExit(f"Assets folder missing: {ASSETS}")
    await create_pool()
    try:
        ids: dict[str, int] = {}
        print("Seeding Figma exercises…")
        for item in EXERCISES:
            ids[item["name"]] = await _upsert(item)
        await _seed_program(ids)
        print("Done.")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
