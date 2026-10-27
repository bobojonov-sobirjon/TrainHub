import json
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

import anyio

from app.core.config import settings
from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow
from app.services import notify
from app.services.storage import IMAGE_EXTENSIONS, VIDEO_EXTENSIONS, media_root, save_bytes

_YT_ID_RE = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:[^#]*&)?v=|embed/|shorts/|live/)|youtu\.be/)([A-Za-z0-9_-]{11})"
)


def youtube_video_id(url: str | None) -> str | None:
    if not url:
        return None
    match = _YT_ID_RE.search(url.strip())
    return match.group(1) if match else None


def normalize_youtube_url(url: str) -> str:
    video_id = youtube_video_id(url)
    if not video_id:
        raise AppError(
            "VALIDATION_ERROR",
            "Можно указать только ссылку YouTube (youtube.com / youtu.be)",
            http_status=422,
        )
    return f"https://www.youtube.com/watch?v={video_id}"


def youtube_thumbnail_url(url: str | None) -> str | None:
    video_id = youtube_video_id(url)
    if not video_id:
        return None
    return f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"


def _local_path_from_public(url: str) -> Path | None:
    marker = "/media/"
    if marker not in url:
        return None
    relative = url.split(marker, 1)[1]
    path = media_root() / relative
    return path if path.is_file() else None


async def _thumb_from_local_video(video_public_url: str, folder: str) -> str | None:
    if not shutil.which("ffmpeg"):
        return None
    source = _local_path_from_public(video_public_url)
    if source is None:
        return None
    tmp = Path(tempfile.mkstemp(suffix=".jpg")[1])
    try:
        result = await anyio.run_process(
            [
                "ffmpeg",
                "-y",
                "-ss",
                "1",
                "-i",
                str(source),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(tmp),
            ],
            check=False,
        )
        if result.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:
            return None
        data = await anyio.Path(tmp).read_bytes()
        return await save_bytes(
            data,
            folder=f"{folder}/cover",
            filename="auto-cover.jpg",
            allowed=IMAGE_EXTENSIONS,
        )
    except Exception:
        return None
    finally:
        tmp.unlink(missing_ok=True)


async def resolve_trainer_media(
    *,
    folder: str,
    video,
    thumbnail,
    video_url: str | None,
) -> tuple[str | None, str | None]:
    """Trainer: file upload and/or YouTube URL only. Auto-cover from YT or first video frame."""
    file_url, thumb_url = await save_lesson_media(folder, video, thumbnail)
    resolved = file_url
    if not resolved and video_url and video_url.strip():
        resolved = normalize_youtube_url(video_url)
    elif video_url and video_url.strip() and not file_url and not youtube_video_id(video_url):
        raise AppError(
            "VALIDATION_ERROR",
            "Можно указать только ссылку YouTube или загрузить файл видео",
            http_status=422,
        )

    if not thumb_url and resolved:
        thumb_url = youtube_thumbnail_url(resolved)
        if not thumb_url and file_url:
            thumb_url = await _thumb_from_local_video(file_url, folder)
    return resolved, thumb_url

VIDEO_STATUSES = {"draft", "processing", "pending_review", "published", "rejected", "archived"}
LEVELS = {"beginner", "intermediate", "advanced"}
MEANINGFUL_FIELDS = {
    "title",
    "description",
    "category_id",
    "topic_id",
    "level",
    "exercise_id",
    "exercise_details",
    "video_url",
}

_CYR = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "д": "d",
    "е": "e",
    "ё": "e",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "h",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "sch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}


def slugify(text: str) -> str:
    lowered = text.strip().lower()
    mapped = "".join(_CYR.get(ch, ch) for ch in lowered)
    mapped = re.sub(r"[^a-z0-9]+", "-", mapped).strip("-")
    return mapped[:80] or "item"


def _row(record: Any) -> dict:
    item = dict(record)
    details = item.get("exercise_details")
    if isinstance(details, str):
        item["exercise_details"] = json.loads(details)
    elif details is None:
        item["exercise_details"] = {}
    item["has_video"] = bool(item.get("video_url"))
    return item


def _validate_level(level: str | None) -> str | None:
    if level in (None, ""):
        return None
    if level not in LEVELS:
        raise AppError("VALIDATION_ERROR", "Уровень: beginner, intermediate или advanced", http_status=400)
    return level


async def _unique_category_slug(base: str, exclude_id: int | None = None) -> str:
    slug = base
    n = 2
    while True:
        row = await fetchrow(
            "SELECT id FROM video_categories WHERE slug = $1 AND ($2::bigint IS NULL OR id <> $2)",
            slug,
            exclude_id,
        )
        if row is None:
            return slug
        slug = f"{base}-{n}"
        n += 1


async def _unique_topic_slug(category_id: int, base: str, exclude_id: int | None = None) -> str:
    slug = base
    n = 2
    while True:
        row = await fetchrow(
            """
            SELECT id FROM video_topics
            WHERE category_id = $1 AND slug = $2 AND ($3::bigint IS NULL OR id <> $3)
            """,
            category_id,
            slug,
            exclude_id,
        )
        if row is None:
            return slug
        slug = f"{base}-{n}"
        n += 1


async def _require_category(category_id: int, *, active_only: bool = False) -> dict:
    row = await fetchrow("SELECT * FROM video_categories WHERE id = $1", category_id)
    if row is None:
        raise AppError("NOT_FOUND", "Категория не найдена", http_status=404)
    if active_only and not row["is_active"]:
        raise AppError("NOT_FOUND", "Категория не найдена", http_status=404)
    return dict(row)


async def _require_topic(topic_id: int, *, category_id: int | None = None, active_only: bool = False) -> dict:
    row = await fetchrow("SELECT * FROM video_topics WHERE id = $1", topic_id)
    if row is None:
        raise AppError("NOT_FOUND", "Тема не найдена", http_status=404)
    if category_id is not None and row["category_id"] != category_id:
        raise AppError("VALIDATION_ERROR", "Тема не относится к этой категории", http_status=400)
    if active_only and not row["is_active"]:
        raise AppError("NOT_FOUND", "Тема не найдена", http_status=404)
    return dict(row)


async def _require_link(trainer_id: int, link_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT id, trainer_id, client_id, status, archived_at
        FROM trainer_clients
        WHERE id = $1 AND trainer_id = $2
        """,
        link_id,
        trainer_id,
    )
    if row is None:
        raise AppError("NOT_FOUND", "Клиент не найден", http_status=404)
    if row["archived_at"] is not None or row["status"] == "archived":
        raise AppError("FORBIDDEN", "Связь с клиентом архивирована", http_status=403)
    return dict(row)


async def _audit(video_id: int, actor_id: int | None, action: str, from_status: str | None, to_status: str | None, reason: str | None = None) -> None:
    await execute(
        """
        INSERT INTO video_audit_log (video_id, actor_id, action, from_status, to_status, reason)
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        video_id,
        actor_id,
        action,
        from_status,
        to_status,
        reason,
    )


async def _maybe_fill_exercise_video(exercise_id: int | None, video_url: str | None) -> None:
    if not exercise_id or not video_url:
        return
    await execute(
        """
        UPDATE exercises
        SET video_url = $2
        WHERE id = $1 AND (video_url IS NULL OR video_url = '')
        """,
        exercise_id,
        video_url,
    )


async def save_lesson_media(folder: str, video, thumbnail) -> tuple[str | None, str | None]:
    video_url = None
    thumb_url = None
    if video is not None and video.filename:
        data = await video.read()
        video_url = await save_bytes(
            data,
            folder=f"{folder}/video",
            filename=video.filename,
            allowed=VIDEO_EXTENSIONS,
            max_bytes=settings.video_lesson_max_bytes,
        )
    if thumbnail is not None and thumbnail.filename:
        data = await thumbnail.read()
        thumb_url = await save_bytes(
            data,
            folder=f"{folder}/cover",
            filename=thumbnail.filename,
            allowed=IMAGE_EXTENSIONS,
        )
    return video_url, thumb_url


async def list_categories(*, public: bool) -> list[dict]:
    where = "WHERE c.is_active = TRUE" if public else ""
    rows = await fetch(
        f"""
        SELECT c.*,
            (SELECT COUNT(*) FROM video_topics t WHERE t.category_id = c.id AND t.is_active = TRUE) AS topics_count,
            (
                SELECT COUNT(*) FROM video_lessons v
                JOIN video_topics t ON t.id = v.topic_id
                WHERE v.category_id = c.id AND v.status = 'published'
                  AND t.is_active = TRUE
            ) AS videos_count
        FROM video_categories c
        {where}
        ORDER BY c.sort_order, c.id
        """
    )
    return [dict(r) for r in rows]


async def get_category(category_id: int, *, public: bool) -> dict:
    items = await list_categories(public=public)
    for item in items:
        if item["id"] == category_id:
            return item
    raise AppError("NOT_FOUND", "Категория не найдена", http_status=404)


async def create_category(payload) -> dict:
    slug = await _unique_category_slug(slugify(payload.name))
    row = await fetchrow(
        """
        INSERT INTO video_categories (name, slug, description, thumbnail_url, sort_order, is_active)
        VALUES ($1, $2, $3, $4, COALESCE($5, 0), COALESCE($6, TRUE))
        RETURNING *
        """,
        payload.name,
        slug,
        payload.description,
        payload.thumbnail_url,
        payload.sort_order,
        payload.is_active,
    )
    return await get_category(row["id"], public=False)


async def update_category(category_id: int, payload) -> dict:
    current = await _require_category(category_id)
    name = payload.name if payload.name is not None else current["name"]
    slug = current["slug"]
    if payload.name and payload.name != current["name"]:
        slug = await _unique_category_slug(slugify(name), exclude_id=category_id)
    await execute(
        """
        UPDATE video_categories
        SET name = $2,
            slug = $3,
            description = COALESCE($4, description),
            thumbnail_url = COALESCE($5, thumbnail_url),
            sort_order = COALESCE($6, sort_order),
            is_active = COALESCE($7, is_active),
            updated_at = NOW()
        WHERE id = $1
        """,
        category_id,
        name,
        slug,
        payload.description,
        payload.thumbnail_url,
        payload.sort_order,
        payload.is_active,
    )
    return await get_category(category_id, public=False)


async def archive_category(category_id: int) -> dict:
    await _require_category(category_id)
    await execute("UPDATE video_categories SET is_active = FALSE, updated_at = NOW() WHERE id = $1", category_id)
    return await get_category(category_id, public=False)


async def list_topics(category_id: int, *, public: bool) -> list[dict]:
    await _require_category(category_id, active_only=public)
    extra = "AND t.is_active = TRUE" if public else ""
    rows = await fetch(
        f"""
        SELECT t.*,
            (
                SELECT COUNT(*) FROM video_lessons v
                WHERE v.topic_id = t.id AND v.status = 'published'
            ) AS videos_count
        FROM video_topics t
        WHERE t.category_id = $1 {extra}
        ORDER BY t.sort_order, t.id
        """,
        category_id,
    )
    return [dict(r) for r in rows]


async def create_topic(payload) -> dict:
    await _require_category(payload.category_id)
    exists = await fetchrow(
        "SELECT id FROM video_topics WHERE category_id = $1 AND lower(name) = lower($2)",
        payload.category_id,
        payload.name,
    )
    if exists:
        raise AppError("DUPLICATE", "Тема с таким названием уже есть в категории", http_status=409)
    slug = await _unique_topic_slug(payload.category_id, slugify(payload.name))
    row = await fetchrow(
        """
        INSERT INTO video_topics (category_id, name, slug, description, thumbnail_url, sort_order, is_active)
        VALUES ($1, $2, $3, $4, $5, COALESCE($6, 0), COALESCE($7, TRUE))
        RETURNING *
        """,
        payload.category_id,
        payload.name,
        slug,
        payload.description,
        payload.thumbnail_url,
        payload.sort_order,
        payload.is_active,
    )
    return dict(row)


async def update_topic(topic_id: int, payload) -> dict:
    current = await _require_topic(topic_id)
    category_id = payload.category_id or current["category_id"]
    if category_id != current["category_id"]:
        await _require_category(category_id)
    name = payload.name if payload.name is not None else current["name"]
    exists = await fetchrow(
        """
        SELECT id FROM video_topics
        WHERE category_id = $1 AND lower(name) = lower($2) AND id <> $3
        """,
        category_id,
        name,
        topic_id,
    )
    if exists:
        raise AppError("DUPLICATE", "Тема с таким названием уже есть в категории", http_status=409)
    slug = current["slug"]
    if name != current["name"] or category_id != current["category_id"]:
        slug = await _unique_topic_slug(category_id, slugify(name), exclude_id=topic_id)
    await execute(
        """
        UPDATE video_topics
        SET category_id = $2,
            name = $3,
            slug = $4,
            description = COALESCE($5, description),
            thumbnail_url = COALESCE($6, thumbnail_url),
            sort_order = COALESCE($7, sort_order),
            is_active = COALESCE($8, is_active),
            updated_at = NOW()
        WHERE id = $1
        """,
        topic_id,
        category_id,
        name,
        slug,
        payload.description,
        payload.thumbnail_url,
        payload.sort_order,
        payload.is_active,
    )
    row = await fetchrow("SELECT * FROM video_topics WHERE id = $1", topic_id)
    return dict(row)


def _video_select() -> str:
    return """
        SELECT v.*,
            c.name AS category_name, c.slug AS category_slug, c.is_active AS category_active,
            t.name AS topic_name, t.slug AS topic_slug, t.is_active AS topic_active,
            u.first_name AS trainer_first_name, u.last_name AS trainer_last_name,
            (
                SELECT COUNT(*) FROM client_video_assignments a
                WHERE a.video_id = v.id AND a.status = 'active'
            ) AS assigned_clients_count
        FROM video_lessons v
        JOIN video_categories c ON c.id = v.category_id
        JOIN video_topics t ON t.id = v.topic_id
        LEFT JOIN users u ON u.id = v.trainer_id
    """


def _serialize_video(record: Any) -> dict:
    item = _row(record)
    item["trainer"] = None
    if item.get("trainer_id"):
        item["trainer"] = {
            "id": item["trainer_id"],
            "first_name": item.get("trainer_first_name"),
            "last_name": item.get("trainer_last_name"),
        }
    item.pop("trainer_first_name", None)
    item.pop("trainer_last_name", None)
    return item


async def get_video_row(video_id: int) -> dict:
    row = await fetchrow(_video_select() + " WHERE v.id = $1", video_id)
    if row is None:
        raise AppError("NOT_FOUND", "Видео не найдено", http_status=404)
    return _serialize_video(row)


def _is_publicly_playable(video: dict) -> bool:
    return bool(
        video["status"] == "published"
        and video.get("category_active")
        and video.get("topic_active")
        and video.get("video_url")
    )


async def list_public_videos(
    *,
    category_id: int | None,
    topic_id: int | None,
    trainer_id: int | None,
    level: str | None,
    search: str | None,
    page_size: int,
    offset: int,
) -> tuple[list[dict], int]:
    clauses = [
        "v.status = 'published'",
        "c.is_active = TRUE",
        "t.is_active = TRUE",
    ]
    args: list[Any] = []
    if category_id:
        args.append(category_id)
        clauses.append(f"v.category_id = ${len(args)}")
    if topic_id:
        args.append(topic_id)
        clauses.append(f"v.topic_id = ${len(args)}")
    if trainer_id:
        args.append(trainer_id)
        clauses.append(f"v.trainer_id = ${len(args)}")
    if level:
        args.append(_validate_level(level))
        clauses.append(f"v.level = ${len(args)}")
    if search:
        args.append(f"%{search.strip()}%")
        clauses.append(f"(v.title ILIKE ${len(args)} OR v.description ILIKE ${len(args)})")
    where = " AND ".join(clauses)
    total = await fetchrow(f"SELECT COUNT(*) AS total FROM video_lessons v JOIN video_categories c ON c.id = v.category_id JOIN video_topics t ON t.id = v.topic_id WHERE {where}", *args)
    args.extend([page_size, offset])
    rows = await fetch(
        _video_select() + f" WHERE {where} ORDER BY v.published_at DESC NULLS LAST, v.id DESC LIMIT ${len(args) - 1} OFFSET ${len(args)}",
        *args,
    )
    return [_serialize_video(r) for r in rows], int(total["total"])


async def topic_videos(topic_id: int, page_size: int, offset: int) -> tuple[list[dict], int]:
    await _require_topic(topic_id, active_only=True)
    return await list_public_videos(
        category_id=None,
        topic_id=topic_id,
        trainer_id=None,
        level=None,
        search=None,
        page_size=page_size,
        offset=offset,
    )


async def trainer_public_videos(trainer_id: int, page_size: int, offset: int) -> tuple[list[dict], int]:
    return await list_public_videos(
        category_id=None,
        topic_id=None,
        trainer_id=trainer_id,
        level=None,
        search=None,
        page_size=page_size,
        offset=offset,
    )


async def public_video_detail(video_id: int, user_id: int, roles: list[str]) -> dict:
    video = await get_video_row(video_id)
    if _is_publicly_playable(video):
        return video
    if video.get("trainer_id") == user_id:
        return video
    assigned = await fetchrow(
        """
        SELECT id FROM client_video_assignments
        WHERE video_id = $1 AND client_id = $2 AND status = 'active'
        """,
        video_id,
        user_id,
    )
    if assigned and video["status"] == "published":
        return video
    raise AppError("NOT_FOUND", "Видео не найдено", http_status=404)


async def list_admin_videos(
    *,
    status: str | None,
    source_type: str | None,
    category_id: int | None,
    search: str | None,
    page_size: int,
    offset: int,
) -> tuple[list[dict], int]:
    clauses = ["TRUE"]
    args: list[Any] = []
    if status:
        if status not in VIDEO_STATUSES:
            raise AppError("VALIDATION_ERROR", "Некорректный статус", http_status=400)
        args.append(status)
        clauses.append(f"v.status = ${len(args)}")
    if source_type:
        args.append(source_type)
        clauses.append(f"v.source_type = ${len(args)}")
    if category_id:
        args.append(category_id)
        clauses.append(f"v.category_id = ${len(args)}")
    if search:
        args.append(f"%{search.strip()}%")
        clauses.append(f"(v.title ILIKE ${len(args)} OR v.description ILIKE ${len(args)})")
    where = " AND ".join(clauses)
    total = await fetchrow(f"SELECT COUNT(*) AS total FROM video_lessons v WHERE {where}", *args)
    args.extend([page_size, offset])
    rows = await fetch(
        _video_select() + f" WHERE {where} ORDER BY v.updated_at DESC, v.id DESC LIMIT ${len(args) - 1} OFFSET ${len(args)}",
        *args,
    )
    return [_serialize_video(r) for r in rows], int(total["total"])


async def list_trainer_videos(trainer_id: int, status: str | None, page_size: int, offset: int) -> tuple[list[dict], int]:
    clauses = ["v.trainer_id = $1"]
    args: list[Any] = [trainer_id]
    if status:
        if status not in VIDEO_STATUSES:
            raise AppError("VALIDATION_ERROR", "Некорректный статус", http_status=400)
        args.append(status)
        clauses.append(f"v.status = ${len(args)}")
    where = " AND ".join(clauses)
    total = await fetchrow(f"SELECT COUNT(*) AS total FROM video_lessons v WHERE {where}", *args)
    args.extend([page_size, offset])
    rows = await fetch(
        _video_select() + f" WHERE {where} ORDER BY v.updated_at DESC, v.id DESC LIMIT ${len(args) - 1} OFFSET ${len(args)}",
        *args,
    )
    return [_serialize_video(r) for r in rows], int(total["total"])


def _exercise_details(
    *,
    exercise_name: str | None,
    technique: str | None,
    equipment: str | None,
    muscles: list[str] | None,
    sets: int | None,
    reps: int | None,
) -> dict:
    details: dict[str, Any] = {}
    if exercise_name:
        details["name"] = exercise_name
    if technique:
        details["technique"] = technique
    if equipment:
        details["equipment"] = equipment
    if muscles:
        details["muscles"] = muscles
    if sets is not None:
        details["sets"] = sets
    if reps is not None:
        details["reps"] = reps
    return details


async def create_video(
    *,
    actor_id: int | None,
    source_type: str,
    trainer_id: int | None,
    title: str,
    description: str | None,
    category_id: int,
    topic_id: int,
    level: str | None,
    duration_seconds: int | None,
    exercise_id: int | None,
    exercise_details: dict,
    video_url: str | None,
    thumbnail_url: str | None,
    submit: bool,
    publish: bool,
) -> dict:
    title = (title or "").strip()
    if not title:
        raise AppError("VALIDATION_ERROR", "Укажите название видео", http_status=400)
    await _require_topic(topic_id, category_id=category_id)
    level = _validate_level(level)
    if exercise_id:
        ex = await fetchrow("SELECT id, name FROM exercises WHERE id = $1", exercise_id)
        if ex is None:
            raise AppError("NOT_FOUND", "Упражнение не найдено", http_status=404)
        exercise_details.setdefault("name", ex["name"])
    if source_type == "admin" and publish and video_url:
        status = "published"
    elif submit and video_url:
        status = "pending_review"
    elif video_url:
        status = "draft"
    else:
        status = "draft"
    row = await fetchrow(
        """
        INSERT INTO video_lessons (
            title, description, trainer_id, category_id, topic_id, source_type,
            video_url, thumbnail_url, duration_seconds, level, exercise_id,
            exercise_details, status, published_at
        )
        VALUES (
            $1, $2, $3, $4, $5, $6,
            $7, $8, $9, $10, $11,
            $12::jsonb, $13, CASE WHEN $13 = 'published' THEN NOW() ELSE NULL END
        )
        RETURNING id
        """,
        title,
        description,
        trainer_id,
        category_id,
        topic_id,
        source_type,
        video_url,
        thumbnail_url,
        duration_seconds,
        level,
        exercise_id,
        json.dumps(exercise_details),
        status,
    )
    await _audit(row["id"], actor_id, "create", None, status, None)
    if status == "published":
        await _maybe_fill_exercise_video(exercise_id, video_url)
    return await get_video_row(row["id"])


async def update_video(
    video_id: int,
    *,
    actor_id: int,
    as_admin: bool,
    title: str | None,
    description: str | None,
    category_id: int | None,
    topic_id: int | None,
    level: str | None,
    duration_seconds: int | None,
    exercise_id: int | None,
    exercise_details: dict | None,
    video_url: str | None,
    thumbnail_url: str | None,
) -> dict:
    current = await get_video_row(video_id)
    if not as_admin and current.get("trainer_id") != actor_id:
        raise AppError("FORBIDDEN", "Можно менять только своё видео", http_status=403)
    if current["status"] == "archived" and not as_admin:
        raise AppError("FORBIDDEN", "Архивное видео нельзя редактировать", http_status=403)

    new_title = title.strip() if title is not None else current["title"]
    new_description = description if description is not None else current["description"]
    new_category = category_id or current["category_id"]
    new_topic = topic_id or current["topic_id"]
    await _require_topic(new_topic, category_id=new_category)
    new_level = _validate_level(level) if level is not None else current["level"]
    new_duration = duration_seconds if duration_seconds is not None else current["duration_seconds"]
    new_exercise = exercise_id if exercise_id is not None else current["exercise_id"]
    new_details = exercise_details if exercise_details is not None else current["exercise_details"]
    new_video = video_url if video_url is not None else current["video_url"]
    new_thumb = thumbnail_url if thumbnail_url is not None else current["thumbnail_url"]

    changed = {
        "title": new_title != current["title"],
        "description": new_description != current["description"],
        "category_id": new_category != current["category_id"],
        "topic_id": new_topic != current["topic_id"],
        "level": new_level != current["level"],
        "exercise_id": new_exercise != current["exercise_id"],
        "exercise_details": new_details != current["exercise_details"],
        "video_url": new_video != current["video_url"],
    }
    meaningful = any(changed[key] for key in MEANINGFUL_FIELDS if key in changed)
    new_status = current["status"]
    if not as_admin and current["status"] == "published" and meaningful:
        new_status = "pending_review"

    await execute(
        """
        UPDATE video_lessons
        SET title = $2,
            description = $3,
            category_id = $4,
            topic_id = $5,
            level = $6,
            duration_seconds = $7,
            exercise_id = $8,
            exercise_details = $9::jsonb,
            video_url = $10,
            thumbnail_url = $11,
            status = $12,
            published_at = CASE WHEN $12 = 'published' THEN COALESCE(published_at, NOW()) ELSE published_at END,
            updated_at = NOW()
        WHERE id = $1
        """,
        video_id,
        new_title,
        new_description,
        new_category,
        new_topic,
        new_level,
        new_duration,
        new_exercise,
        json.dumps(new_details or {}),
        new_video,
        new_thumb,
        new_status,
    )
    if new_status != current["status"]:
        await _audit(video_id, actor_id, "update", current["status"], new_status, None)
    return await get_video_row(video_id)


async def submit_video(trainer_id: int, video_id: int) -> dict:
    video = await get_video_row(video_id)
    if video.get("trainer_id") != trainer_id:
        raise AppError("FORBIDDEN", "Можно отправлять только своё видео", http_status=403)
    if not video.get("video_url"):
        raise AppError("VALIDATION_ERROR", "Сначала загрузите видеофайл", http_status=400)
    if video["status"] not in {"draft", "rejected"}:
        raise AppError("VALIDATION_ERROR", "На модерацию можно отправить черновик или отклонённое видео", http_status=400)
    await execute(
        "UPDATE video_lessons SET status = 'pending_review', rejection_reason = NULL, updated_at = NOW() WHERE id = $1",
        video_id,
    )
    await _audit(video_id, trainer_id, "submit", video["status"], "pending_review", None)
    return await get_video_row(video_id)


async def archive_trainer_video(trainer_id: int, video_id: int) -> dict:
    video = await get_video_row(video_id)
    if video.get("trainer_id") != trainer_id:
        raise AppError("FORBIDDEN", "Можно архивировать только своё видео", http_status=403)
    await execute(
        "UPDATE video_lessons SET status = 'archived', updated_at = NOW() WHERE id = $1",
        video_id,
    )
    await _audit(video_id, trainer_id, "archive", video["status"], "archived", None)
    return await get_video_row(video_id)


async def approve_video(admin_id: int, video_id: int) -> dict:
    video = await get_video_row(video_id)
    if not video.get("video_url"):
        raise AppError("VALIDATION_ERROR", "У видео нет файла", http_status=400)
    await execute(
        """
        UPDATE video_lessons
        SET status = 'published', rejection_reason = NULL, published_at = NOW(), updated_at = NOW()
        WHERE id = $1
        """,
        video_id,
    )
    await _audit(video_id, admin_id, "approve", video["status"], "published", None)
    await _maybe_fill_exercise_video(video.get("exercise_id"), video.get("video_url"))
    if video.get("trainer_id"):
        await notify.create_notification(
            video["trainer_id"],
            ntype="video_approved",
            title="Видеоурок опубликован",
            body=f"«{video['title']}» прошло модерацию",
            payload={"video_id": video_id},
        )
    return await get_video_row(video_id)


async def reject_video(admin_id: int, video_id: int, reason: str) -> dict:
    video = await get_video_row(video_id)
    await execute(
        """
        UPDATE video_lessons
        SET status = 'rejected', rejection_reason = $2, updated_at = NOW()
        WHERE id = $1
        """,
        video_id,
        reason,
    )
    await _audit(video_id, admin_id, "reject", video["status"], "rejected", reason)
    if video.get("trainer_id"):
        await notify.create_notification(
            video["trainer_id"],
            ntype="video_rejected",
            title="Видеоурок отклонён",
            body=reason,
            payload={"video_id": video_id, "reason": reason},
        )
    return await get_video_row(video_id)


async def archive_admin_video(admin_id: int, video_id: int) -> dict:
    video = await get_video_row(video_id)
    await execute("UPDATE video_lessons SET status = 'archived', updated_at = NOW() WHERE id = $1", video_id)
    await _audit(video_id, admin_id, "archive", video["status"], "archived", None)
    return await get_video_row(video_id)


async def list_video_assignments(video_id: int) -> list[dict]:
    await get_video_row(video_id)
    rows = await fetch(
        """
        SELECT a.*,
            cu.first_name AS client_first_name, cu.last_name AS client_last_name,
            tu.first_name AS trainer_first_name, tu.last_name AS trainer_last_name
        FROM client_video_assignments a
        JOIN users cu ON cu.id = a.client_id
        JOIN users tu ON tu.id = a.trainer_id
        WHERE a.video_id = $1
        ORDER BY a.assigned_at DESC
        """,
        video_id,
    )
    return [dict(r) for r in rows]


def _assignable(video: dict, trainer_id: int) -> bool:
    if video["status"] != "published":
        return False
    if video["source_type"] == "admin":
        return True
    return video.get("trainer_id") == trainer_id


async def list_client_assignments(trainer_id: int, link_id: int) -> list[dict]:
    link = await _require_link(trainer_id, link_id)
    return await _assignments_for_client(link["client_id"], trainer_id=trainer_id)


async def assign_videos(trainer_id: int, link_id: int, video_ids: list[int]) -> list[dict]:
    link = await _require_link(trainer_id, link_id)
    unique_ids = list(dict.fromkeys(video_ids))
    created: list[dict] = []
    for video_id in unique_ids:
        video = await get_video_row(video_id)
        if not _assignable(video, trainer_id):
            raise AppError(
                "FORBIDDEN",
                "Можно назначить только опубликованное своё видео или ролик из общей библиотеки",
                http_status=403,
            )
        existing = await fetchrow(
            "SELECT * FROM client_video_assignments WHERE client_id = $1 AND video_id = $2",
            link["client_id"],
            video_id,
        )
        if existing and existing["status"] == "active":
            created.append(await _assignment_card(existing["id"]))
            continue
        if existing:
            await execute(
                """
                UPDATE client_video_assignments
                SET status = 'active', trainer_id = $2, assigned_at = NOW(), revoked_at = NULL, updated_at = NOW()
                WHERE id = $1
                """,
                existing["id"],
                trainer_id,
            )
            assignment_id = existing["id"]
        else:
            row = await fetchrow(
                """
                INSERT INTO client_video_assignments (client_id, trainer_id, video_id)
                VALUES ($1, $2, $3)
                RETURNING id
                """,
                link["client_id"],
                trainer_id,
                video_id,
            )
            assignment_id = row["id"]
        created.append(await _assignment_card(assignment_id))
        await notify.create_notification(
            link["client_id"],
            ntype="video_assigned",
            title="Новый видеоурок",
            body=f"Тренер назначил видео «{video['title']}»",
            payload={"video_id": video_id, "assignment_id": assignment_id},
        )
    return created


async def revoke_assignment(trainer_id: int, link_id: int, assignment_id: int) -> dict:
    link = await _require_link(trainer_id, link_id)
    row = await fetchrow(
        """
        SELECT * FROM client_video_assignments
        WHERE id = $1 AND client_id = $2 AND trainer_id = $3
        """,
        assignment_id,
        link["client_id"],
        trainer_id,
    )
    if row is None:
        raise AppError("NOT_FOUND", "Назначение не найдено", http_status=404)
    await execute(
        """
        UPDATE client_video_assignments
        SET status = 'revoked', revoked_at = NOW(), updated_at = NOW()
        WHERE id = $1
        """,
        assignment_id,
    )
    video = await get_video_row(row["video_id"])
    await notify.create_notification(
        link["client_id"],
        ntype="video_unassigned",
        title="Видеоурок снят",
        body=f"«{video['title']}» больше не назначено",
        payload={"video_id": row["video_id"], "assignment_id": assignment_id},
    )
    return await _assignment_card(assignment_id)


async def _assignment_card(assignment_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT a.id, a.client_id, a.trainer_id, a.video_id, a.assigned_at, a.status, a.revoked_at,
            a.created_at, a.updated_at,
            tu.first_name AS assigned_by_first_name, tu.last_name AS assigned_by_last_name
        FROM client_video_assignments a
        JOIN users tu ON tu.id = a.trainer_id
        WHERE a.id = $1
        """,
        assignment_id,
    )
    if row is None:
        raise AppError("NOT_FOUND", "Назначение не найдено", http_status=404)
    item = dict(row)
    video = await get_video_row(item["video_id"])
    playable = item["status"] == "active" and video["status"] == "published"
    if not playable:
        video = {**video, "video_url": None, "has_video": False}
    item["video"] = video
    item["assigned_by"] = {
        "id": item["trainer_id"],
        "first_name": item.pop("assigned_by_first_name"),
        "last_name": item.pop("assigned_by_last_name"),
    }
    return item


async def _assignments_for_client(client_id: int, *, trainer_id: int | None = None) -> list[dict]:
    args: list[Any] = [client_id]
    extra = ""
    if trainer_id is not None:
        args.append(trainer_id)
        extra = f"AND a.trainer_id = ${len(args)}"
    rows = await fetch(
        f"""
        SELECT a.id
        FROM client_video_assignments a
        WHERE a.client_id = $1 AND a.status = 'active' {extra}
        ORDER BY a.assigned_at DESC
        """,
        *args,
    )
    return [await _assignment_card(r["id"]) for r in rows]


async def my_assigned_videos(user_id: int) -> list[dict]:
    return await _assignments_for_client(user_id)


async def my_assignment(user_id: int, assignment_id: int) -> dict:
    card = await _assignment_card(assignment_id)
    if card["client_id"] != user_id:
        raise AppError("NOT_FOUND", "Назначение не найдено", http_status=404)
    return card


async def my_video(user_id: int, video_id: int, roles: list[str]) -> dict:
    return await public_video_detail(video_id, user_id, roles)


def parse_muscles(raw: str | None) -> list[str] | None:
    if not raw:
        return None
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    return parts or None


def build_details(
    exercise_name: str | None,
    technique: str | None,
    equipment: str | None,
    muscles: str | None,
    sets: int | None,
    reps: int | None,
) -> dict:
    return _exercise_details(
        exercise_name=exercise_name,
        technique=technique,
        equipment=equipment,
        muscles=parse_muscles(muscles),
        sets=sets,
        reps=reps,
    )
