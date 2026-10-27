"""Seed one ready program for nbek@gmail.com (idempotent).

- Archives other published non-pro catalog/demo noise so the list shows 1 item
- Creates/updates «Жимы/тяги/ноги (Начальный)» authored by nbek
- Copies cover from app assets into media (then app can drop bundled covers)

Run:  .venv/bin/python scripts/seed_nbek_ready_program.py
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

REPO = Path(__file__).resolve().parents[3]
COVER_CANDIDATES = [
    Path(__file__).resolve().parent / "figma_exercises" / "cover2.png",
    Path(__file__).resolve().parent / "figma_exercises" / "cover2.jpg",
    Path(__file__).resolve().parent / "figma_exercises" / "cover1.jpg",
    REPO / "app" / "assets" / "images" / "ready" / "cover2.png",
    REPO / "app" / "assets" / "images" / "ready" / "cover1.png",
]

TITLE = "Жимы/тяги/ноги (Начальный)"
NBEK_EMAIL = "nbek@gmail.com"

DAYS = [
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


async def _set_cover(program_id: int) -> None:
    src = next((p for p in COVER_CANDIDATES if p.exists()), None)
    if src is None:
        print("  cover source missing — skip")
        return
    dest_dir = media_root() / "programs" / str(program_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"cover{src.suffix.lower()}"
    shutil.copyfile(src, dest)
    url = public_url(f"programs/{program_id}/{dest.name}")
    await execute("UPDATE programs SET cover_url = $2 WHERE id = $1", program_id, url)
    print(f"  cover ← {src.name} → {url}")


async def _replace_days(program_id: int) -> None:
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

    name_to_id = {r["name"]: int(r["id"]) for r in await fetch("SELECT id, name FROM exercises WHERE is_public = TRUE")}

    for di, (title, desc, exercises) in enumerate(DAYS, start=1):
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


async def main() -> None:
    await create_pool()
    try:
        user = await fetchrow("SELECT id FROM users WHERE email = $1", NBEK_EMAIL)
        if not user:
            raise SystemExit(f"User {NBEK_EMAIL} not found")
        author_id = int(user["id"])
        print(f"nbek user_id={author_id}")

        # Keep marketplace clean: one ready (non-pro) program for demo.
        archived = await execute(
            """
            UPDATE programs
            SET status = 'archived'
            WHERE status = 'published'
              AND is_pro = FALSE
              AND NOT (author_id = $1 AND title = $2)
            """,
            author_id,
            TITLE,
        )
        print(f"archived other non-pro published programs: {archived}")

        existing = await fetchrow(
            """
            SELECT id FROM programs
            WHERE author_id = $1 AND title = $2
            ORDER BY id DESC LIMIT 1
            """,
            author_id,
            TITLE,
        )
        description = (
            "Базовый комплекс из 3 тренировок в неделю для развития всех групп мышц:\n"
            "Жимы: грудь, плечи и трицепс\n"
            "Тяги: спина и бицепс\n"
            "Ноги: квадрицепсы, бицепс бедра, ягодицы и икры"
        )
        if existing:
            program_id = int(existing["id"])
            await execute(
                """
                UPDATE programs SET
                    source = 'trainer',
                    description = $2,
                    level = 'beginner',
                    goals = $3,
                    equipment = $4,
                    workouts_per_week = 3,
                    duration_weeks = 4,
                    is_pro = FALSE,
                    status = 'published'
                WHERE id = $1
                """,
                program_id,
                description,
                ["gain_muscle"],
                ["gym", "machine"],
            )
            print(f"Updated program #{program_id}")
        else:
            # Prefer reclaiming catalog twin if present
            twin = await fetchrow(
                "SELECT id FROM programs WHERE title = $1 AND source = 'catalog' ORDER BY id DESC LIMIT 1",
                TITLE,
            )
            if twin:
                program_id = int(twin["id"])
                await execute(
                    """
                    UPDATE programs SET
                        author_id = $2,
                        source = 'trainer',
                        description = $3,
                        level = 'beginner',
                        goals = $4,
                        equipment = $5,
                        workouts_per_week = 3,
                        duration_weeks = 4,
                        is_pro = FALSE,
                        status = 'published'
                    WHERE id = $1
                    """,
                    program_id,
                    author_id,
                    description,
                    ["gain_muscle"],
                    ["gym", "machine"],
                )
                print(f"Reassigned catalog program #{program_id} → nbek")
            else:
                row = await fetchrow(
                    """
                    INSERT INTO programs (
                        author_id, source, title, description, level, goals, equipment,
                        workouts_per_week, duration_weeks, is_pro, status
                    ) VALUES (
                        $1, 'trainer', $2, $3, 'beginner', $4, $5, 3, 4, FALSE, 'published'
                    ) RETURNING id
                    """,
                    author_id,
                    TITLE,
                    description,
                    ["gain_muscle"],
                    ["gym", "machine"],
                )
                program_id = int(row["id"])
                print(f"Created program #{program_id}")

        # Drop nbek draft junk titled "k" if empty placeholder
        await execute(
            """
            UPDATE programs SET status = 'archived'
            WHERE author_id = $1 AND title = 'k' AND status = 'draft'
            """,
            author_id,
        )

        await _set_cover(program_id)
        await _replace_days(program_id)

        pub = await fetch(
            """
            SELECT id, title, author_id, status, cover_url, source
            FROM programs WHERE status = 'published' AND is_pro = FALSE ORDER BY id
            """
        )
        print("published non-pro:")
        for p in pub:
            print(" ", dict(p))
        print("Done.")
    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
