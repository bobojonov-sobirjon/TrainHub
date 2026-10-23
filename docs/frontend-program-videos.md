# TrainHub — программы и видео упражнений (frontend)

Отдельный документ. Общий API: `docs/frontend-api.md`. Оплата PRO: `docs/frontend-robokassa.md`.

Видео **не** отдельная платформа и не «полный видеокурс тренера».  
Это ссылка у упражнения: `video_url`. Игрок открывает URL (или показывает «нет видео»).

PRO — подписка TrainHub, не подписка на видео.

База: `http://51.20.92.246/api/v1/app`  
Auth: `Authorization: Bearer <access_token>`

---

## 1. Каталог → карточка → видео

```
GET /programs?q=&level=&goal=&equipment=
        ↓
GET /programs/{id}
        ↓
день → упражнение.video_url
        ↓
плеер  /  «Видео недоступно»
```

Список программ **не** содержит видео. Только обложка `cover_url`.

---

## 2. `GET /programs/{id}`

У каждого упражнения в `days[].exercises[]`:

| Поле | Смысл |
|------|--------|
| `id` | id строки в дне программы |
| `exercise_id` | id упражнения |
| `name` | название |
| `sets`, `reps_min`, `reps_max`, `note` | план подхода |
| `video_url` | URL ролика или `null` |
| `has_video` | `true`, если `video_url` не пустой |
| `photo_url`, `photo_urls` | фото |
| `equipment`, `primary_muscle`, `secondary_muscles`, `exercise_type` | справочники |

Если день `locked: true` (PRO без подписки) — `exercises` пустой. Видео не отдаём.

Пример элемента:

```json
{
  "id": 11,
  "exercise_id": 3,
  "name": "Жим гантелей",
  "sets": 3,
  "reps_min": 8,
  "reps_max": 12,
  "note": null,
  "video_url": "http://51.20.92.246/media/…",
  "has_video": true,
  "photo_url": null,
  "photo_urls": [],
  "equipment": "dumbbells",
  "primary_muscle": "chest",
  "secondary_muscles": [],
  "exercise_type": "strength"
}
```

---

## 3. Одно упражнение

`GET /exercises` — каталог (тоже `video_url`, `has_video`).  
`GET /exercises/{exercise_id}` — карточка для живой сессии.

Не хардкодить URL роликов. Только поле с бэкенда.

Нет файла в Postgres: в БД метаданные и ссылка, файл в `/media/` или внешний URL.

---

## 4. Плеер

- `has_video === false` или `video_url == null` → текст «Видео недоступно», не битый iframe.
- Play / pause / seek / fullscreen — нативный player (`<video src={video_url} controls />` или аналог).
- Ошибка загрузки — retry / «не удалось загрузить».
- Видео упражнения в программе — это `video_url` у упражнения, не библиотека уроков.
- Библиотека видеоуроков (категории / темы / назначение): [frontend-video-lessons.md](frontend-video-lessons.md).

---

## 5. Старт тренировки из дня программы

Как раньше: `POST /sessions` с `program_day_id`.  
Вес и повторы — `POST .../sets`, прошлый результат — `GET /sessions/{id}/previous/{exercise_id}`.

Видео в сессии: по `exercise_id` взять `video_url` из карточки программы или `GET /exercises/{id}`.
