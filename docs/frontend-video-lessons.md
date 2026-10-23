# TrainHub — видеоуроки (frontend)

Отдельный документ. Общий API: `docs/frontend-api.md`.  
Видео **упражнения в программе** (`days[].exercises[].video_url`): `docs/frontend-program-videos.md`.

Это **другой объект**. Программа = дни и упражнения. Видеоурок = отдельный ролик в библиотеке.  
Назначение урока клиенту ≠ назначение программы.

PRO / Robokassa / покупка тренера **сюда не входят**. Назначить можно только своему клиенту (уже есть связь тренер–клиент).

База: `http://51.20.92.246/api/v1/app`  
Админ: `http://51.20.92.246/api/v1/admin`  
Auth: `Authorization: Bearer <access_token>`  
Конверт: `{ "success": true, "data": … }`

Файлы: `multipart/form-data`. Остальное — JSON.  
Форматы: видео `mp4/mov/webm`, обложка `jpg/png/webp/gif`. Максимум ролика: 80 МБ (`VIDEO_LESSON_MAX_BYTES`).

---

## 1. Иерархия

```
Категория → Тема → Видео
Набор массы → Грудные мышцы → Bench press (Alex), Грудь (Daniel)
```

Один ролик — одна тема и один автор (`trainer` или `admin`).  
Назначение клиенту **не копирует файл**: пишется только связь.

Статусы: `draft` | `processing` | `pending_review` | `published` | `rejected` | `archived`.  
В общий каталог попадают только `published` + активные категория и тема.

---

## 2. Каталог (Coach и Client)

Все методы ниже — JWT `aud=app`.

| Method | Endpoint | Что |
|--------|----------|-----|
| GET | `/categories` | Активные категории, `topics_count`, `videos_count` |
| GET | `/categories/{id}` | Карточка категории |
| GET | `/categories/{id}/topics` | Темы категории |
| GET | `/topics/{id}/videos` | Опубликованные ролики темы |
| GET | `/videos` | Поиск и фильтры |
| GET | `/videos/{id}` | Карточка + `video_url` (если есть доступ) |
| GET | `/trainers/{id}/videos` | Опубликованные ролики тренера |

`GET /videos` query:

| Параметр | Также |
|----------|--------|
| `category_id` | `categoryId` |
| `topic_id` | `topicId` |
| `trainer_id` | `trainerId` |
| `level` | `beginner` / `intermediate` / `advanced` |
| `search` | название / описание |
| `page`, `page_size` | `limit` = синоним `page_size` |

На списке и карточке:

`id`, `title`, `description`, `thumbnail_url`, `video_url`, `has_video`, `duration_seconds`, `level`, `status`, `source_type`, `category_id`, `category_name`, `topic_id`, `topic_name`, `exercise_details`, `trainer` (`id`, `first_name`, `last_name`), `assigned_clients_count`.

Плеер: `has_video === false` или `video_url == null` → «Видео недоступно». Иначе нативный `<video src={video_url} controls />`.

Черновик / на модерации / отказ / архив в каталоге **не видны**.

---

## 3. Coach — мои видео

| Method | Endpoint | Что |
|--------|----------|-----|
| GET | `/trainer/videos` | Свои ролики, `?status=` |
| POST | `/trainer/videos` | Создать (`multipart`) |
| PATCH | `/trainer/videos/{id}` | Править своё (`multipart`) |
| POST | `/trainer/videos/{id}/submit` | На модерацию |
| DELETE | `/trainer/videos/{id}` | Архивировать. Назначения клиентов не ломаются |

`POST /trainer/videos` поля формы:

`title*`, `category_id*`, `topic_id*`, `description`, `level`, `duration_seconds`, `exercise_id`, `exercise_name`, `technique`, `equipment`, `muscles` (через запятую), `sets`, `reps`, `video_url` (если файл уже где-то лежит), `submit` (`true` — сразу на модерацию), файлы `video`, `thumbnail`.

Без файла/URL статус = `draft`. С файлом и `submit=true` → `pending_review`.  
После `published` смена названия, описания, темы или файла снова ставит `pending_review`.

Чужое видео править нельзя (`403`).

---

## 4. Coach — назначить клиенту

`link_id` — **id связи** из `GET /trainer/clients`, не `user.id` клиента.

| Method | Endpoint | Что |
|--------|----------|-----|
| GET | `/trainer/clients/{link_id}/videos` | Назначенные этому клиенту |
| POST | `/trainer/clients/{link_id}/videos` | Назначить |
| DELETE | `/trainer/clients/{link_id}/videos/{assignment_id}` | Снять назначение |

Тело назначения:

```json
{ "video_ids": [12, 15] }
```

Можно назначить:

1. своё **опубликованное** видео;
2. ролик из общей библиотеки (`source_type=admin`, `published`).

Повтор того же видео тому же клиенту новую строку не создаёт.  
Снятие убирает ролик из «Назначено тренером», исходный урок в каталоге остаётся.

Чужому клиенту или чужому ролику тренера — `403` / `404`.

---

## 5. Client — «Назначено тренером»

| Method | Endpoint | Что |
|--------|----------|-----|
| GET | `/me/assigned-videos` | Только мои активные назначения |
| GET | `/me/assigned-videos/{assignment_id}` | Карточка назначения + видео |
| GET | `/me/videos/{id}` | Урок с проверкой доступа |

`client_id` с клиента **не принимается** — берётся из JWT.

Карточка назначения: `id`, `assigned_at`, `status`, `assigned_by`, `video`.  
Если урок архивирован или назначение снято — `video.video_url` будет `null`.

Общий опубликованный ролик может быть и в каталоге, и здесь. Это одна запись видео, две полки в UI.

Чужой `assignment_id` → `404`, даже если id угадан.

---

## 6. Admin

JWT `aud=admin`.

| Method | Endpoint |
|--------|----------|
| GET/POST | `/categories` |
| PATCH | `/categories/{id}` |
| POST | `/categories/{id}/archive` — не удаляет темы и ролики |
| GET | `/categories/{id}/topics` |
| POST | `/topics` |
| PATCH | `/topics/{id}` — можно перенести в другую категорию |
| GET/POST | `/videos` |
| GET/PATCH | `/videos/{id}` |
| GET | `/videos/{id}/assignments` |
| POST | `/videos/{id}/approve` |
| POST | `/videos/{id}/reject` — `{ "reason": "…" }` |
| POST | `/videos/{id}/archive` |

Создание общего ролика: тот же `multipart`, что у тренера, плюс `publish=true` (по умолчанию).  
Опубликованное общее видео видно всем в каталоге без назначения.

`GET /admin/videos?status=pending_review` — очередь модерации.

Категорию с темами физически не удаляем: только архив (`is_active=false`) или перенос тем через `PATCH /topics/{id}`.

---

## 7. Экраны

**Каталог:** категории → темы → список роликов (несколько тренеров в одной теме).  
**Плеер:** название, описание, автор, категория/тема, длительность, `exercise_details` (техника, инвентарь, подходы).  
**Coach → клиент:** «Видеоуроки» → выбрать из «Мои» и «Общая библиотека» → `video_ids`.  
**Client:** вкладка «Назначено тренером» = `GET /me/assigned-videos`.

Уведомления (лента уже есть): `video_assigned`, `video_approved`, `video_rejected`, `video_unassigned`.

---

## 8. Не делать

- Не путать с `GET /programs/{id}` и `exercise.video_url`.
- Не копировать файл при назначении.
- Не строить оплату / marketplace тренера вокруг урока.
- Не слать `client_id` в URL личного кабинета — только токен.
- Не хардкодить URL роликов.
