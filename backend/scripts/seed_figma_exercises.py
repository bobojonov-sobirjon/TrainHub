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

from app.db.connection import execute, fetch, fetchrow
from app.db.pool import close_pool, create_pool
from app.services.storage import media_root, public_url

ASSETS = Path(__file__).resolve().parent / "figma_exercises"

# HQ Photoroom exports from Figma (transparent PNG, ~300–1024px) — not the old 24–52px circle crops.
EXERCISES: list[dict] = [
    {"name": "Разминка", "primary_muscle": "full_body", "equipment": "bodyweight", "exercise_type": "stretching", "file": "hq_warm.png"},
    {"name": "Жим лежа (Штанга)", "primary_muscle": "chest", "equipment": "barbell", "exercise_type": "strength", "file": "hq_bench.png"},
    {"name": "Жим с плеч (Гантель)", "primary_muscle": "shoulders", "equipment": "dumbbell", "exercise_type": "strength", "file": "hq_shoulder.png"},
    {"name": "Бабочка (Грудная клетка)", "primary_muscle": "chest", "equipment": "machine", "exercise_type": "strength", "file": "hq_butterfly.png"},
    {"name": "Бабочка (Грудные мышцы)", "primary_muscle": "chest", "equipment": "machine", "exercise_type": "strength", "file": "hq_butterfly.png"},
    {"name": "Разгибания на трицепс (блок)", "primary_muscle": "arms", "equipment": "cable", "exercise_type": "strength", "file": "hq_tricep.png"},
    {"name": "Разгибание на трицепс", "primary_muscle": "arms", "equipment": "cable", "exercise_type": "strength", "file": "hq_tricep.png"},
    {"name": "Вертикальная тяга (блок)", "primary_muscle": "back", "equipment": "machine", "exercise_type": "strength", "file": "hq_lat.png"},
    {"name": "Вертикальная тяга", "primary_muscle": "back", "equipment": "machine", "exercise_type": "strength", "file": "hq_lat.png"},
    {"name": "Тяга нижнего блока к поясу (Блок)", "primary_muscle": "back", "equipment": "cable", "exercise_type": "strength", "file": "hq_row.png"},
    {"name": "Тяга нижнего блока", "primary_muscle": "back", "equipment": "cable", "exercise_type": "strength", "file": "hq_row.png"},
    {"name": "Шраги (Гантель)", "primary_muscle": "traps", "equipment": "dumbbell", "exercise_type": "strength", "file": "hq_shrug.png"},
    {"name": "Шраги (Гантели)", "primary_muscle": "traps", "equipment": "dumbbell", "exercise_type": "strength", "file": "hq_shrug.png"},
    {"name": "Сгибание Молоток (Гантель)", "primary_muscle": "arms", "equipment": "dumbbell", "exercise_type": "strength", "file": "hq_hammer.png"},
    {"name": "Тяга к подбородку", "primary_muscle": "shoulders", "equipment": "barbell", "exercise_type": "strength", "file": "hq_upright.png"},
    {"name": "Жим ногами (Тренажёр)", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "hq_legpress.png"},
    {"name": "Жим ногами (Тренажер)", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "hq_legpress.png"},
    {"name": "Жимы ногами", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "hq_legpress.png"},
    {"name": "Сгибание ног лежа (Тренажёр)", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "hq_legcurl.png"},
    {"name": "Сгибание ног лежа", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "hq_legcurl.png"},
    {"name": "Разгибание ног (Тренажёр)", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "hq_legext.png"},
    {"name": "Разгибание ног", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "hq_legext.png"},
    {"name": "Подъем носков стоя (Тренажёр)", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "hq_calf.png"},
    {"name": "Подъем на носки", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "hq_calf.png"},
    {"name": "Подъем носков стоя", "primary_muscle": "legs", "equipment": "machine", "exercise_type": "strength", "file": "hq_calf.png"},
    {"name": "Жим гантелей сидя", "primary_muscle": "shoulders", "equipment": "dumbbell", "exercise_type": "strength", "file": "hq_shoulder.png"},
]


async def _apply_photo(exercise_id: int, src: Path) -> str:
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
    return url


async def _upsert(item: dict) -> int:
    existing = await fetchrow(
        "SELECT id FROM exercises WHERE name = $1 AND is_public = TRUE AND owner_id IS NULL LIMIT 1",
        item["name"],
    )
    if existing is None:
        # Fuzzy: same public catalog title with slight punctuation differences.
        existing = await fetchrow(
            """
            SELECT id FROM exercises
            WHERE is_public = TRUE AND owner_id IS NULL
              AND lower(name) = lower($1)
            LIMIT 1
            """,
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

    url = await _apply_photo(exercise_id, src)
    print(f"  #{exercise_id} {item['name']} → {url}")
    return exercise_id


async def _refresh_matching_photos() -> None:
    """Push HQ art onto any catalog exercise whose name contains the Figma title stem."""
    stems: list[tuple[str, str]] = [
        ("разминк", "hq_warm.png"),
        ("жим лежа", "hq_bench.png"),
        ("бабочк", "hq_butterfly.png"),
        ("трицепс", "hq_tricep.png"),
        ("вертикальн", "hq_lat.png"),
        ("нижнего блока", "hq_row.png"),
        ("шраг", "hq_shrug.png"),
        ("молоток", "hq_hammer.png"),
        ("подбородк", "hq_upright.png"),
        ("жим нога", "hq_legpress.png"),
        ("жимы нога", "hq_legpress.png"),
        ("сгибание ног", "hq_legcurl.png"),
        ("разгибание ног", "hq_legext.png"),
        ("носк", "hq_calf.png"),
        ("жим с плеч", "hq_shoulder.png"),
        ("жим гантелей сидя", "hq_shoulder.png"),
    ]
    for stem, file_name in stems:
        src = ASSETS / file_name
        if not src.exists():
            continue
        rows = await fetch(
            """
            SELECT id, name FROM exercises
            WHERE is_public = TRUE
              AND lower(name) LIKE '%' || $1 || '%'
            """,
            stem.lower(),
        )
        for row in rows:
            url = await _apply_photo(int(row["id"]), src)
            print(f"  match #{row['id']} {row['name']} → {url}")


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
        print("Refreshing matching catalog photos…")
        await _refresh_matching_photos()
        await _seed_program(ids)
        print("Done.")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
