"""Seed Figma-like Progress stats for nbekdev@gmail.com only (idempotent).

Matches Figma Progress cards:
- Вес 78,5 (−2,3) · Жир 14,5% (−1,8) · Мышцы 60,7 (+1,5) · ИМТ ~24.5
- Параметры: плечи/грудь/талия/бёдра + sparklines
- Фото прогресс: 2 сета (1 и 2 месяца назад)

Run:  .venv/bin/python scripts/seed_nbekdev_stats.py
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.connection import fetchrow
from app.db.pool import close_pool, create_pool
from app.db.transactions import transaction
from app.services.cabinet import home, progress
from app.services.storage import media_root, public_url

EMAIL = "nbekdev@gmail.com"
MARKER = "seed:nbekdev_stats"
NOW = datetime.now(timezone.utc)
REPO = Path(__file__).resolve().parents[3]

# Figma Progress summary (current)
FIGMA = {
    "weight_kg": 78.5,
    "body_fat_pct": 14.5,
    "muscle_mass_kg": 60.7,
    "water_pct": 55.0,
    "shoulders_cm": 125.0,
    "chest_cm": 107.0,
    "waist_cm": 83.0,
    "hips_cm": 98.0,
    "thigh_cm": 58.0,
    "back_cm": 96.0,
    "calf_cm": 37.0,
    "neck_cm": 38.0,
    "arm_cm": 36.5,
    "arm_left_cm": 36.0,
    "arm_right_cm": 37.0,
    "forearm_cm": 29.5,
}
# Previous row → Figma deltas: −2.3 / −1.8 / +1.5 / body ±
PREV = {
    "weight_kg": 80.8,
    "body_fat_pct": 16.3,
    "muscle_mass_kg": 59.2,
    "water_pct": 54.2,
    "shoulders_cm": 122.0,
    "chest_cm": 108.5,
    "waist_cm": 81.0,
    "hips_cm": 99.5,
    "thigh_cm": 60.5,
    "back_cm": 97.0,
    "calf_cm": 37.5,
    "neck_cm": 38.2,
    "arm_cm": 35.8,
    "arm_left_cm": 35.5,
    "arm_right_cm": 36.2,
    "forearm_cm": 29.2,
}
# height so BMI ≈ 24.5 at 78.5 kg
HEIGHT_CM = 179.0
GOAL_KG = 76.0

PHOTO_SOURCES = [
    REPO / "app" / "assets" / "images" / "client1.png",
    REPO / "app" / "assets" / "images" / "client2.png",
    REPO / "app" / "assets" / "images" / "trainer1.png",
]


def _lerp(a: float, b: float, t: float) -> float:
    return round(a + (b - a) * t, 1)


async def _insert_measurement(conn, uid: int, at: datetime, row: dict) -> None:
    await conn.execute(
        """
        INSERT INTO body_measurements (
            client_id, recorded_by, recorded_at, weight_kg, body_fat_pct, muscle_mass_kg, water_pct,
            chest_cm, back_cm, waist_cm, hips_cm, thigh_cm, calf_cm, neck_cm, shoulders_cm,
            arm_cm, arm_left_cm, arm_right_cm, forearm_cm
        ) VALUES (
            $1,$1,$2,$3,$4,$5,$6,
            $7,$8,$9,$10,$11,$12,$13,$14,
            $15,$16,$17,$18
        )
        """,
        uid,
        at,
        row["weight_kg"],
        row["body_fat_pct"],
        row["muscle_mass_kg"],
        row["water_pct"],
        row["chest_cm"],
        row["back_cm"],
        row["waist_cm"],
        row["hips_cm"],
        row["thigh_cm"],
        row["calf_cm"],
        row["neck_cm"],
        row["shoulders_cm"],
        row["arm_cm"],
        row["arm_left_cm"],
        row["arm_right_cm"],
        row["forearm_cm"],
    )


def _blend(start: dict, end: dict, t: float) -> dict:
    return {k: _lerp(float(start[k]), float(end[k]), t) for k in end}


async def _seed_photos(conn, uid: int) -> None:
    old = await conn.fetch("SELECT id FROM photo_progress_sets WHERE user_id = $1", uid)
    for row in old:
        await conn.execute("DELETE FROM photo_progress_sets WHERE id = $1", row["id"])

    srcs = [p for p in PHOTO_SOURCES if p.exists()]
    if len(srcs) < 3:
        # pad with first available
        while len(srcs) < 3 and srcs:
            srcs.append(srcs[0])
    if not srcs:
        print("  photos: no local assets — skip")
        return

    dest_dir = media_root() / "progress" / str(uid)
    dest_dir.mkdir(parents=True, exist_ok=True)

    sets = [
        (date.today() - timedelta(days=32), "1m"),
        (date.today() - timedelta(days=62), "2m"),
    ]
    angles = ("front", "side", "back")
    for taken_on, tag in sets:
        aset = await conn.fetchrow(
            "INSERT INTO photo_progress_sets (user_id, taken_on) VALUES ($1,$2) RETURNING id",
            uid,
            taken_on,
        )
        for i, angle in enumerate(angles):
            src = srcs[i % len(srcs)]
            name = f"{tag}_{angle}{src.suffix.lower()}"
            dest = dest_dir / name
            shutil.copyfile(src, dest)
            url = public_url(f"progress/{uid}/{name}")
            await conn.execute(
                """
                INSERT INTO photo_progress_images (set_id, angle, image_url, sort_order)
                VALUES ($1,$2,$3,$4)
                """,
                aset["id"],
                angle,
                url,
                i,
            )
    print(f"  photos: 2 sets → {dest_dir}")


async def seed() -> None:
    await create_pool()
    user = await fetchrow("SELECT id FROM users WHERE email = $1", EMAIL)
    if not user:
        raise SystemExit(f"User not found: {EMAIL}")
    uid = int(user["id"])

    link = await fetchrow(
        """
        SELECT id, trainer_id FROM trainer_clients
        WHERE client_id = $1 AND archived_at IS NULL
        ORDER BY id DESC LIMIT 1
        """,
        uid,
    )
    trainer_id = int(link["trainer_id"]) if link else None

    async with transaction() as conn:
        old_events = await conn.fetch(
            "SELECT id FROM calendar_events WHERE client_id = $1 AND note = $2",
            uid,
            MARKER,
        )
        for ev in old_events:
            await conn.execute("DELETE FROM workout_sessions WHERE calendar_event_id = $1", ev["id"])
            await conn.execute("DELETE FROM calendar_events WHERE id = $1", ev["id"])

        old_sessions = await conn.fetch(
            "SELECT id FROM workout_sessions WHERE lead_client_id = $1 AND notes = $2",
            uid,
            MARKER,
        )
        for s in old_sessions:
            await conn.execute("DELETE FROM workout_sessions WHERE id = $1", s["id"])

        await conn.execute("DELETE FROM body_measurements WHERE client_id = $1", uid)

        await conn.execute(
            "UPDATE users SET weight_goal_kg = $2, height_cm = $3 WHERE id = $1",
            uid,
            Decimal(str(GOAL_KG)),
            Decimal(str(HEIGHT_CM)),
        )
        if link:
            await conn.execute(
                "UPDATE trainer_clients SET target_weight_kg = $2 WHERE id = $1",
                link["id"],
                Decimal(str(GOAL_KG)),
            )

        # History for chart/sparklines (older → prev), then Figma current
        # Weight arc similar to Figma: ~80 → dip ~77 → 78.5
        history_days = [42, 35, 28, 21, 14, 7]
        start = {
            "weight_kg": 82.0,
            "body_fat_pct": 18.0,
            "muscle_mass_kg": 57.5,
            "water_pct": 53.0,
            "shoulders_cm": 119.0,
            "chest_cm": 110.0,
            "waist_cm": 88.0,
            "hips_cm": 101.0,
            "thigh_cm": 63.0,
            "back_cm": 99.0,
            "calf_cm": 38.5,
            "neck_cm": 38.5,
            "arm_cm": 34.5,
            "arm_left_cm": 34.0,
            "arm_right_cm": 34.8,
            "forearm_cm": 28.5,
        }
        # mid dip around day 14-ish toward 77 kg (Figma tooltip)
        dip = {**_blend(start, PREV, 0.7), "weight_kg": 77.0, "body_fat_pct": 15.2, "muscle_mass_kg": 58.8}

        for i, days_ago in enumerate(history_days):
            t = i / max(1, len(history_days) - 1)
            if days_ago >= 21:
                row = _blend(start, dip, t / 0.6 if t < 0.6 else 1.0)
            else:
                row = _blend(dip, PREV, (t - 0.5) / 0.5 if t >= 0.5 else 0.0)
            # explicit checkpoints
            if days_ago == 28:
                row = {**_blend(start, dip, 0.55), "weight_kg": 79.0}
            if days_ago == 14:
                row = dip
            if days_ago == 7:
                row = PREV
            await _insert_measurement(conn, uid, NOW - timedelta(days=days_ago), row)

        await _insert_measurement(conn, uid, NOW - timedelta(hours=2), FIGMA)

        await _seed_photos(conn, uid)

        pub_ex = await conn.fetch(
            "SELECT id FROM exercises WHERE is_public = TRUE ORDER BY id LIMIT 8"
        )
        if not pub_ex:
            pub_ex = await conn.fetch("SELECT id FROM exercises ORDER BY id LIMIT 8")
        ex_ids = [int(r["id"]) for r in pub_ex]

        attendance_plan = [
            (-26, "completed"),
            (-24, "completed"),
            (-21, "no_show"),
            (-19, "completed"),
            (-17, "completed"),
            (-14, "completed"),
            (-12, "no_show"),
            (-10, "completed"),
            (-7, "completed"),
            (-5, "completed"),
            (-3, "no_show"),
            (-1, "completed"),
            (2, "scheduled"),
            (5, "scheduled"),
        ]
        for days, status in attendance_plan:
            start_at = (NOW + timedelta(days=days)).replace(hour=10, minute=0, second=0, microsecond=0)
            end = start_at + timedelta(hours=1)
            ev = await conn.fetchrow(
                """
                INSERT INTO calendar_events (
                    trainer_id, client_id, starts_at, ends_at, duration_min, format, kinds,
                    focus_muscles, status, note, reminder
                ) VALUES ($1,$2,$3,$4,60,'gym',ARRAY['strength'],ARRAY['chest'],$5,$6,'1h')
                RETURNING id
                """,
                trainer_id,
                uid,
                start_at,
                end,
                status,
                MARKER,
            )
            if status not in ("completed", "no_show"):
                continue
            sess_status = "completed" if status == "completed" else "cancelled"
            finished = start_at + timedelta(minutes=55)
            s = await conn.fetchrow(
                """
                INSERT INTO workout_sessions (
                    trainer_id, lead_client_id, source, kinds, calendar_event_id,
                    status, started_at, finished_at, duration_sec, calories, notes
                ) VALUES ($1,$2,'calendar',ARRAY['strength'],$3,$4,$5,$6,$7,$8,$9)
                RETURNING id
                """,
                trainer_id,
                uid,
                ev["id"],
                sess_status,
                start_at,
                finished if sess_status == "completed" else None,
                3300 if sess_status == "completed" else None,
                420 if sess_status == "completed" else None,
                MARKER,
            )
            await conn.execute(
                """
                INSERT INTO workout_session_clients (session_id, client_id)
                VALUES ($1,$2) ON CONFLICT DO NOTHING
                """,
                s["id"],
                uid,
            )
            await conn.execute(
                "UPDATE calendar_events SET session_id = $1 WHERE id = $2",
                s["id"],
                ev["id"],
            )
            if sess_status != "completed" or not ex_ids:
                continue
            age = abs(days)
            base = 40 + max(0, 26 - age) * 0.8
            for order, eid in enumerate(ex_ids[:4], start=1):
                se = await conn.fetchrow(
                    """
                    INSERT INTO session_exercises (session_id, exercise_id, sort_order, rest_sec, status)
                    VALUES ($1,$2,$3,90,'done') RETURNING id
                    """,
                    s["id"],
                    eid,
                    order,
                )
                for si in range(1, 4):
                    await conn.execute(
                        """
                        INSERT INTO session_sets (
                            session_exercise_id, set_index, weight_kg, reps, is_warmup, completed_at
                        ) VALUES ($1,$2,$3,$4,FALSE,$5)
                        """,
                        se["id"],
                        si,
                        round(base + order * 2.5 + si * 2.5, 1),
                        12 - si,
                        start_at + timedelta(minutes=order * 12 + si),
                    )

    h = await home(uid)
    p = await progress(uid)
    cur = p["current"] or {}
    prev = p["previous"] or {}
    print(f"OK {EMAIL} id={uid}")
    print(
        f"  вес={cur.get('weight_kg')} (Δ {float(cur.get('weight_kg') or 0) - float(prev.get('weight_kg') or 0):+.1f}) "
        f"жир={cur.get('body_fat_pct')} мышцы={cur.get('muscle_mass_kg')} "
        f"рост={h.get('height_cm')} ИМТ≈{float(cur.get('weight_kg') or 0) / ((HEIGHT_CM / 100) ** 2):.1f}"
    )
    print(
        f"  плечи={cur.get('shoulders_cm')} грудь={cur.get('chest_cm')} "
        f"талия={cur.get('waist_cm')} бёдра={cur.get('thigh_cm')} "
        f"фото={len(p.get('photo_sets') or [])}"
    )
    await close_pool()


if __name__ == "__main__":
    asyncio.run(seed())
