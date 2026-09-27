# TrainHub — Mobile Frontend API

Один документ для мобильной разработки. Экраны Figma разложены по ролям.

| | |
|---|---|
| **Coach** (роль `trainer`) | §5 — экраны C1–C22 |
| **Client** (роль `client`) | §6 — экраны L1–L16 |
| Общее | JWT, `/me`, словари, уведомления, billing, FAQ |

Swagger: http://51.20.92.246:8005/docs  
Теги: `Coach - …`, `Client`, `Shared - …`.

---

## 1. General

| | |
|---|---|
| Project | TrainHub |
| Framework | **FastAPI** (не Django). Контракт JSON + JWT |
| Content-Type | `application/json` (кроме upload: `multipart/form-data`) |
| Prefix | `/api/v1/app` |
| Auth | JWT `aud=app` |

**Base URL**

| Env | URL |
|-----|-----|
| Prod | `http://51.20.92.246:8005` |
| Prod (nginx) | `http://51.20.92.246` — те же `/api/…`, `/docs` |
| Dev | `http://127.0.0.1:8005` |

Полный путь = Base URL + `/api/v1/app` + endpoint.  
Пример: `POST http://51.20.92.246:8005/api/v1/app/auth/login`

---

## 2. Envelope и ошибки

Успех:

```json
{
  "success": true,
  "data": {}
}
```

Ошибка:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Текст на русском"
  }
}
```

Частые `code`: `INVALID_CREDENTIALS`, `FORBIDDEN`, `TRAINER_PRO_REQUIRED`, `RATE_LIMITED`, `NOT_FOUND`, `NO_ACTIVE_SUBSCRIPTION`.

`204 No Content` — тела нет (logout, change-password).

Пагинация в `data`:

```json
{
  "items": [],
  "total": 0,
  "page": 1,
  "page_size": 20
}
```

---

## 3. Authentication (JWT)

Все защищённые запросы:

```
Authorization: Bearer <access_token>
```

`access` живёт ~15 мин. По `401` вызвать refresh, затем повторить запрос.

`user.roles` содержит `"trainer"` (Coach) или `"client"` (Client). Чужой роли — `403 FORBIDDEN`.

### 3.1 Register

- METHOD: `POST`
- URL: `/api/v1/app/auth/register`
- Auth: нет
- Status: `201`

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| first_name | string | yes | — | 1–80 |
| last_name | string | no | `""` | max 80 |
| email | string | email **или** phone | — | EmailStr |
| phone | string | email **или** phone | — | max 20, `+7999…` |
| password | string | yes | — | 8–72 |
| role | string | yes | — | `"trainer"` или `"client"` |
| gender | string | no | null | `male` `female` `other` |
| birth_date | date | no | null | `YYYY-MM-DD` |

Coach:

```json
{
  "first_name": "Иван",
  "last_name": "Петров",
  "email": "ivan.coach@example.com",
  "phone": "+79991234567",
  "password": "Secret123!",
  "role": "trainer",
  "gender": "male",
  "birth_date": "1994-05-12"
}
```

Client:

```json
{
  "first_name": "Анна",
  "last_name": "Смирнова",
  "email": "anna.client@example.com",
  "phone": "+79005551122",
  "password": "Secret123!",
  "role": "client",
  "gender": "female",
  "birth_date": "1998-03-21"
}
```

Response `data` (`TokenPair`):

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 4,
    "public_id": "TH000000004",
    "email": "ivan.coach@example.com",
    "phone": "+79991234567",
    "first_name": "Иван",
    "last_name": "Петров",
    "avatar_url": null,
    "gender": "male",
    "birth_date": "1994-05-12",
    "height_cm": null,
    "weight_goal_kg": null,
    "roles": ["trainer"]
  }
}
```

### 3.2 Login

- METHOD: `POST`
- URL: `/api/v1/app/auth/login`
- Auth: нет

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| login | string | yes | email **или** телефон, min 3 |
| password | string | yes | |

```json
{
  "login": "ivan.coach@example.com",
  "password": "Secret123!"
}
```

Response: тот же `TokenPair`.

### 3.3 Refresh

- METHOD: `POST`
- URL: `/api/v1/app/auth/refresh`

| Field | Type | Required |
|-------|------|----------|
| refresh_token | string | yes |

```json
{ "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh" }
```

Response: новая пара JWT + `user`.

### 3.4 Logout (экран «Выйти из аккаунта»)

- METHOD: `POST`
- URL: `/api/v1/app/auth/logout`
- Status: `204`

```json
{ "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh" }
```

### 3.5 Google / Apple (Firebase Auth) / Telegram

Мобилка входит через **Firebase Auth** (Google или Apple), затем шлёт **Firebase ID token** на backend.

| Method | URL | Body |
|--------|-----|------|
| POST | `/auth/google` | `id_token` — Firebase ID token после Google Sign-In (или native Google ID token); `role` default `"client"`, для Coach `"trainer"` |
| POST | `/auth/apple` | `identity_token` — Firebase ID token после Apple Sign-In (или native Apple token); `first_name`, `last_name` optional; `role` default `"client"` |
| POST | `/auth/telegram/send-code` | `identifier` string required — телефон или `@username` |
| POST | `/auth/telegram/verify` | `identifier`, `code` required; `role` default `"client"` |

```json
{ "id_token": "<firebase_id_token>", "role": "client" }
```

```json
{ "identity_token": "<firebase_id_token>", "first_name": "Анна", "last_name": "Смирнова", "role": "client" }
```

Сервер проверяет токен через Firebase Admin (`project_id=trainhub-75989`). Если `iss` не Firebase — падает на native Google/Apple verify.

Telegram send-code (первый вход):

```json
{
  "success": true,
  "data": {
    "requires_bot_start": true,
    "bot_url": "https://t.me/trainhub_otp_bot?start=login_abc..."
  }
}
```

Если бот уже открыт — код в личку, `requires_bot_start=false`. Verify при успехе → `TokenPair`.

### 3.6 Password

| Method | URL | Auth | Body |
|--------|-----|------|------|
| POST | `/auth/change-password` | Bearer | `old_password` string, `new_password` string min 8 → `204` |
| POST | `/auth/password-reset/request` | нет | `login` string |
| POST | `/auth/password-reset/confirm` | нет | `token` string, `new_password` string min 8 → `204` |

---

## 4. Общие (оба приложения)

### GET `/me`

Bearer. `UserPublic`: `id`, `public_id`, `email`, `phone`, `first_name`, `last_name`, `avatar_url`, `gender`, `birth_date`, `height_cm`, `weight_goal_kg`, `roles`.

### PATCH `/me`

Все optional. Email/телефон **не** меняются.

| Field | Type | Notes |
|-------|------|-------|
| first_name | string | max 80 |
| last_name | string | max 80 |
| gender | string | `male` `female` `other` |
| birth_date | date | |
| height_cm | decimal | |
| weight_goal_kg | decimal | |

### POST `/me/avatar`

`multipart/form-data`, поле `file` (JPEG/PNG/WebP). Response: `UserPublic`.

### GET `/dictionaries`

`data.items[]`: `category`, `code`, `title_ru`, `sort_order`.  
Категории: `level`, `fitness_goal`, `muscle_group`, `equipment`, `training_format`, `workout_kind`.

### Notifications

| Method | URL | Query / Body |
|--------|-----|--------------|
| GET | `/notifications` | `tab` default `"today"` (`today` \| `later`) |
| GET | `/notifications/unread-count` | `{ "unread_count": 5 }` |
| POST | `/notifications/{id}/read` | нет тела → `{ "ok": true }` |
| POST | `/notifications/read-all` | нет тела |

```json
{
  "id": 1,
  "type": "workout",
  "title": "Тренировка",
  "body": "Напоминание…",
  "is_read": false,
  "scheduled_at": null,
  "created_at": "2026-09-23T14:20:00Z"
}
```

### Devices + FCM push

После логина приложение регистрирует **FCM registration token**:

```json
{
  "platform": "ios",
  "token": "<fcm_registration_token>",
  "device_name": "iPhone 15",
  "app_version": "1.0.0"
}
```

| Method | URL | Body |
|--------|-----|------|
| GET | `/me/devices` | |
| POST | `/me/devices` | `platform`: `ios`\|`android`\|`web`; `token` FCM, 8–4096; `device_name` optional; `app_version` optional |
| DELETE | `/me/devices/{device_id}` | |

Сервер шлёт FCM, когда появляется уведомление (заявка, принятие/отклонение, новая/отменённая тренировка).  
Учитывает `/me/notification-preferences`: `push_enabled`, `workout_reminder`, `new_client_request`.  
Мёртвые FCM-токены удаляются сами. Push-пейлоад: `notification.title/body` + `data.type` и связанные id.

### Billing (PRO)

`audience`: Coach → **`pro_trainer`**, Client → **`pro_client`**.

| Method | URL | Body |
|--------|-----|------|
| GET | `/plans?audience=…` | |
| GET | `/me/subscription?audience=…` | |
| POST | `/me/subscription/checkout` | `{ "plan_id": 1 }` mock |
| PATCH | `/me/subscription` | `plan_id` optional, `auto_renew` optional |
| POST | `/me/subscription/cancel` | нет — до конца периода |
| POST | `/me/subscription/resume` | нет |
| GET | `/payments` | история |
| GET | `/payments/{id}` | чек |
| POST | `/payments/{id}/retry` | только `status=failed` |
| GET | `/me/payment-methods` | |
| POST | `/me/payment-methods` | `brand` default `card`; `last4` 4 цифры; `is_default` default true |
| DELETE | `/me/payment-methods/{id}` | |

План: `id`, `audience`, `code`, `period` (`month`\|`year`), `price_amount`, `currency`, `discount_pct`.

### FAQ / Support / Legal

| Method | URL | Query / Body |
|--------|-----|--------------|
| GET | `/faq` | `q`, `audience=trainer` \| `client` \| `all` |
| GET | `/faq/{slug}` | |
| GET | `/support/tickets` | мои обращения |
| POST | `/support/tickets` | `subject` string, `message` string |
| GET | `/legal/{doc_type}` | `terms` \| `privacy` |

### MeasurementIn (оба)

Все поля optional, decimal:  
`weight_kg`, `body_fat_pct`, `muscle_mass_kg`, `water_pct`, `chest_cm`, `back_cm`, `waist_cm`, `hips_cm`, `thigh_cm`, `calf_cm`, `neck_cm`, `shoulders_cm`, `arm_cm`, `arm_left_cm`, `arm_right_cm`, `forearm_cm`.

---

## 5. Coach — экраны Figma → API

Роль JWT: `trainer`.

### C1. Dashboard

| Method | URL | Query | Зачем |
|--------|-----|-------|-------|
| GET | `/me` | | имя, avatar, public_id |
| GET | `/trainer/dashboard` | | счётчики |
| GET | `/notifications/unread-count` | | badge |
| GET | `/trainer/calendar` | `date_from`, `date_to` | сегодня |
| GET | `/trainer/attention` | | внимание |
| GET | `/trainer/reports` | `period=month` \| `week` | отчёт |

```json
{
  "clients_count": 24,
  "today_done": 2,
  "today_planned": 5,
  "month_sessions": 18,
  "attention_count": 3
}
```

Пустые тексты рисует фронт, если счётчики `0`.

### C2. Тренировки сегодня / календарь

GET `/trainer/calendar`  
Query: `date_from` datetime optional, `date_to` datetime optional, `week` datetime optional (понедельник недели).

```json
{
  "id": 10,
  "client_id": 12,
  "first_name": "Анна",
  "last_name": "Смирнова",
  "avatar_url": null,
  "phone": "+7900…",
  "client_since": "2025-02-12T00:00:00Z",
  "starts_at": "2026-09-23T10:00:00+05:00",
  "ends_at": "2026-09-23T11:00:00+05:00",
  "duration_min": 60,
  "format": "gym",
  "kinds": ["strength"],
  "focus_muscles": ["chest"],
  "status": "scheduled",
  "note": "Жимовая",
  "reminder": "1h",
  "repeat_weekly": false,
  "session_id": null
}
```

`status`: `scheduled` \| `in_progress` \| `completed` \| `cancelled` \| `no_show`.  
`reminder`: `none` \| `1h` \| `3h`.

| Method | URL | Body |
|--------|-----|------|
| GET | `/trainer/calendar/{event_id}` | |
| POST | `/trainer/calendar` | CalendarIn |
| PATCH | `/trainer/calendar/{event_id}` | CalendarIn (полная модель) |
| POST | `/trainer/calendar/{event_id}/cancel` | нет → `cancelled` |
| POST | `/trainer/calendar/{event_id}/no-show` | нет → неявка |
| DELETE | `/trainer/calendar/{event_id}` | нет |
| POST | `/trainer/calendar/{event_id}/start-session` | нет → живая сессия |

**CalendarIn**

| Field | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| client_id | int \| null | no | null | пусто = личная тренировка тренера |
| starts_at | datetime | yes | | ISO-8601 |
| ends_at | datetime | yes | | |
| format | string | no | null | `gym` `online` `hybrid` `home` `visit` |
| kinds | string[] | no | `[]` | из `workout_kind` |
| focus_muscles | string[] | no | `[]` | из `muscle_group` |
| note | string | no | null | max 200 |
| reminder | string | no | `none` | `none` `1h` `3h` |
| repeat_weekly | bool | no | false | копии на 12 недель |
| status | string | no | `scheduled` | |

```json
{
  "client_id": 12,
  "starts_at": "2026-09-20T10:00:00+05:00",
  "ends_at": "2026-09-20T11:00:00+05:00",
  "format": "gym",
  "kinds": ["strength"],
  "focus_muscles": ["chest", "triceps"],
  "note": "Жимовая тренировка",
  "reminder": "1h",
  "repeat_weekly": false,
  "status": "scheduled"
}
```

### C3. Живая сессия

| Method | URL | Body |
|--------|-----|------|
| POST | `/sessions` | `source` default `new`; `client_ids` int[]; `kinds` string[]; `program_day_id` optional; `calendar_event_id` optional |
| GET | `/sessions/{session_id}` | |
| POST | `/sessions/{session_id}/exercises` | `exercise_id` int required; `rest_sec` int optional |
| POST | `/sessions/{session_id}/exercises/{se_id}/sets` | `weight_kg` decimal optional; `reps` int optional; `is_warmup` bool default false |
| GET | `/sessions/{session_id}/previous/{exercise_id}` | query `client_id` optional |
| POST | `/sessions/{session_id}/complete` | нет |

### C4. Отчёт

GET `/trainer/reports?period=month`  
`period`: `week` \| `month` (default `month`).

```json
{
  "period": "month",
  "sessions_count": 18,
  "calories_total": 12400,
  "hours_total": 16.5,
  "by_kind": [{ "kind": "strength", "total": 10 }],
  "gender": { "male_count": 8, "female_count": 6, "total": 14 },
  "new_clients": 2,
  "left_clients": 1
}
```

### C5. Клиенты (список)

GET `/trainer/clients`

| Query | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| q | string | no | | имя, телефон, public_id |
| gender | string | no | | `male` `female` |
| format | string | no | | `gym` `online` … |
| status | string | no | | `new` `permanent` `paused` `archived` |
| sort | string | no | `newest` | `newest` `oldest` `alpha` `male_first` `female_first` |
| page | int | no | 1 | |
| page_size | int | no | 20 | |

В item: `goals_count`, `avatar_url`, `gender`, `status`, `training_format`.

### C6. Добавить клиента (поиск)

- POST `/trainer/clients/search` — `{ "query": "ivan" }` min 1. Есть `already_added`.
- POST `/trainer/clients` — `{ "user_id": 42 }`. Бесплатный лимит **5** → `403 TRAINER_PRO_REQUIRED`.

### C7. Добавить клиента вручную

POST `/trainer/clients/manual`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| first_name | string | yes | |
| last_name | string | no | |
| email | string | email **или** phone | |
| phone | string | email **или** phone | |
| birth_date | date | no | |
| gender | string | no | |
| goals | string[] | no | коды `fitness_goal` |
| training_format | string | no | |
| measurements | object | no | MeasurementIn |
| notes | string[] | no | заметки тренера |
| contraindications | string[] | no | |

### C8. Внимание

- GET `/trainer/attention` — `id`, `reason`, `created_at`, `client_id`, имя, `phone`, `avatar_url`, `training_format`, `last_session_at`, `days_inactive`.
- POST `/trainer/attention/{item_id}/resolve` — без тела.

### C9. Карточка клиента

`{link_id}` — id связи `trainer_clients`, **не** `user.id`.

| Method | URL | Body |
|--------|-----|------|
| GET | `/trainer/clients/{link_id}` | |
| PATCH | `/trainer/clients/{link_id}` | optional: `status`, `goals[]`, `training_format`, `target_weight_kg` |
| DELETE | `/trainer/clients/{link_id}` | архив → `{ "ok": true }` |
| GET | `.../{link_id}/measurements` | |
| POST | `.../{link_id}/measurements` | MeasurementIn |
| GET | `.../{link_id}/measurements/chart` | `metric`, `from`, `to` |
| GET | `.../{link_id}/stats` | |
| GET | `.../{link_id}/sessions` | `kind`, `page` |
| GET | `.../{link_id}/notes` | |
| POST | `.../{link_id}/notes` | `{ "text": "…" }` |
| DELETE | `.../{link_id}/notes/{note_id}` | |

Карточка: профиль, `goals`, `target_weight_kg`, `height_cm`, `subscription_ends_at`, `notes[]`, `contraindications[]`, `last_measurement`.

### C10. Заявки клиентов

| Method | URL | Query |
|--------|-----|-------|
| GET | `/trainer/requests` | `status` default `pending`; `page`, `page_size` |
| POST | `/trainer/requests/{request_id}/accept` | нет тела |
| POST | `/trainer/requests/{request_id}/reject` | нет тела |

### C11. Готовые программы

GET `/programs`

| Query | Type | Default | Notes |
|-------|------|---------|-------|
| level | string | | `beginner` … |
| goal | string | | код цели |
| equipment | string | | |
| source | string | | `catalog` `trainer` `user_copy` |
| author_id | int | | |
| q | string | | поиск |
| is_pro | bool | | |
| page | int | 1 | |
| page_size | int | 20 | |

`data.total` → «Показать N результатов».

- GET `/programs/{id}` — если `is_pro` и нет подписки: дни `locked=true`
- POST / DELETE `/programs/{id}/save`
- POST `/programs/{id}/duplicate`
- GET `/programs/{id}/share` → `{ program_id, share_token }`
- GET `/programs/shared/{token}`

### C12. Создать / править программу

| Method | URL | Body |
|--------|-----|------|
| POST | `/programs` | ProgramCreateIn; сервер ставит `source=trainer` |
| PATCH | `/programs/{id}` | своя |
| DELETE | `/programs/{id}` | архив своей |
| POST | `/programs/{id}/days` | ProgramDayIn |
| PATCH | `/programs/{id}/days/{day_id}` | |
| DELETE | `/programs/{id}/days/{day_id}` | |
| POST | `/programs/{id}/days/{day_id}/exercises` | `exercise_id`, `sets`, `reps_min`, `reps_max`, `note` |
| PATCH / DELETE | `.../exercises/{item_id}` | |

**ProgramCreateIn:** `title` required; `description`, `level`, `goals[]`, `equipment[]`, `workouts_per_week`, `duration_weeks`, `is_pro` default false, `status` default `published`.

**Упражнения:** GET/POST `/exercises`, PATCH/DELETE `/exercises/{id}` (только свои). Query GET: `q`, `equipment`, `muscle`.

**ProgramDayIn:** `title` required; `description`; `duration_min` 1–300; `focus_muscles[]`; `sort_order`.

### C13. Marketplace / PRO баннер

| Method | URL | Query |
|--------|-----|-------|
| GET | `/programs?source=trainer` | как C11 |
| GET | `/trainers` | `category`, `q`, `sort=rating\|clients\|newest`, `page` |
| GET | `/trainers/{id}` | профиль + `programs[]` |
| GET | `/trainers/{id}/reviews` | |
| GET | `/plans?audience=pro_trainer` | |
| GET | `/me/subscription?audience=pro_trainer` | |

### C14. Профиль тренера (hub)

GET `/me` + GET `/trainer/profile` + GET `/me/subscription?audience=pro_trainer`

```json
{
  "user_id": 4,
  "bio": "Силовой тренер",
  "experience_years": 10,
  "specializations": ["strength"],
  "work_formats": ["gym", "online"],
  "session_price_amount": "2500.00",
  "session_duration_min": 60,
  "free_first_consult": true,
  "category": "strength",
  "rating_avg": "4.9",
  "reviews_count": 12,
  "clients_count": 24
}
```

### C15. Личные данные

GET/PATCH `/me`, POST `/me/avatar`, GET/PATCH `/trainer/profile` (`bio` max 300, `experience_years`).

### C16. Специализация и цены

GET + PATCH `/trainer/profile`

| Field | Type | Notes |
|-------|------|-------|
| specializations | string[] | коды `fitness_goal` |
| work_formats | string[] | коды `training_format` |
| session_price_amount | decimal | |
| session_duration_min | int | 15–180 |
| free_first_consult | bool | |
| category | string | |

Чипы: GET `/dictionaries`.

### C17. Подписка PRO

`audience=pro_trainer`. См. §4 Billing.

### C18. Настройки уведомлений

GET + PATCH `/me/notification-preferences` — все bool optional:

| Field | Смысл |
|-------|-------|
| push_enabled | Push |
| email_enabled | Email |
| workout_reminder | Напоминания о тренировках |
| new_client_request | Новые заявки клиентов |
| client_report | Отчёты по клиентам |

### C19. Настройки / пароль

POST `/auth/change-password` `{ "old_password", "new_password" }` → 204.  
Версия приложения — только client-side.

### C20–C22. FAQ / legal / logout

- GET `/faq?audience=trainer`, GET `/faq/{slug}`
- POST `/support/tickets` `{ "subject", "message" }`
- GET `/legal/{doc_type}` — `terms` \| `privacy`
- POST `/auth/logout` `{ "refresh_token" }` → 204

---

## 6. Client — экраны Figma → API

Роль JWT: `client`.

### L1. Обзор (home)

- GET `/client/home` — цифры и блоки
- GET `/me` — имя, avatar (в `home` их нет)

```json
{
  "weight_kg": "68.4",
  "body_fat_pct": "22.1",
  "weight_goal_kg": "62.0",
  "progress_pct": 48.3,
  "weight_delta_30d": "-1.2",
  "streak": 12,
  "unread_count": 3,
  "days_in_program": 84,
  "weight_chart": [
    { "date": "2026-09-01", "weight_kg": "70.1" },
    { "date": "2026-09-22", "weight_kg": "68.4" }
  ],
  "attendance_30d": [
    { "date": "2026-09-20", "status": "completed" }
  ],
  "last_session": {
    "id": 88,
    "duration_sec": 3900,
    "calories": 420,
    "finished_at": "2026-09-22T19:05:00Z",
    "kinds": ["strength"],
    "exercises_count": 6,
    "sets_count": 18,
    "trainer_name": "Иван Петров",
    "top_sets": [
      { "name": "Жим лёжа", "weight_kg": "60.0", "reps": 8 }
    ]
  },
  "trainer_notes": [
    {
      "id": 3,
      "text": "Белок 1.6 г/кг",
      "created_at": "2026-09-20T10:00:00Z",
      "trainer_id": 4,
      "trainer_name": "Иван Петров"
    }
  ]
}
```

`trainer_notes` в home — последние 5. Полный список: GET `/client/trainer-notes`.  
Цель веса: PATCH `/me` `{ "weight_goal_kg": 62 }`.

### L2. Тренировки (история)

GET `/client/sessions`

| Query | Type | Required | Default | Notes |
|-------|------|----------|---------|-------|
| q | string | no | | имя упражнения или вид |
| date_from | datetime | no | | ISO-8601 |
| date_to | datetime | no | | |
| kind | string | no | | код `workout_kind` |
| muscle | string | no | | код `muscle_group` |
| format | string | no | | зарезервирован |
| with_trainer | bool | no | | `true` — с тренером |
| with_records | bool | no | | только с рекордами веса |
| duration_min | int | no | | минуты |
| duration_max | int | no | | минуты |
| sort | string | no | `newest` | `newest` `oldest` `duration_asc` `duration_desc` |
| page | int | no | 1 | |
| page_size | int | no | 20 | |

```json
{
  "id": 88,
  "source": "new",
  "kinds": ["strength"],
  "status": "completed",
  "started_at": "2026-09-22T18:00:00Z",
  "finished_at": "2026-09-22T19:05:00Z",
  "duration_sec": 3900,
  "calories": 420,
  "trainer_id": 4,
  "trainer_name": "Иван Петров",
  "sets_count": 18
}
```

### L3. Карточка тренировки

- GET `/client/sessions/{session_id}`
- GET `/sessions/{session_id}` — тот же объект (Shared)
- GET `/sessions/{session_id}/previous/{exercise_id}`

Если клиент сам ведёт тренировку:

| Method | URL | Body |
|--------|-----|------|
| POST | `/sessions` | `source` default `new`; `kinds[]`; `program_day_id` optional |
| POST | `/sessions/{id}/exercises` | `exercise_id`, `rest_sec` optional |
| POST | `/sessions/{id}/exercises/{se_id}/sets` | `weight_kg`, `reps`, `is_warmup` |
| POST | `/sessions/{id}/complete` | |

### L4–L5. Замеры

| Method | URL | Body |
|--------|-----|------|
| GET | `/client/measurements` | список |
| POST | `/client/measurements` | MeasurementIn |
| PATCH | `/client/measurements/{id}` | те же поля, optional |

```json
{
  "weight_kg": 68.4,
  "waist_cm": 74,
  "hips_cm": 98,
  "arm_left_cm": 28.5,
  "arm_right_cm": 29.0
}
```

### L6. Параметры тела / график

- GET `/client/progress` — текущий vs предыдущий замер + фотосеты
- GET `/client/measurements/chart?metric=weight_kg`

`metric`: `weight_kg`, `body_fat_pct`, `muscle_mass_kg`, `water_pct`, `chest_cm`, `back_cm`, `waist_cm`, `hips_cm`, `thigh_cm`, `calf_cm`, `neck_cm`, `shoulders_cm`, `arm_cm`, `arm_left_cm`, `arm_right_cm`, `forearm_cm`.

```json
{
  "metric": "weight_kg",
  "points": [
    { "recorded_at": "2026-08-01T00:00:00Z", "value": "74.0" },
    { "recorded_at": "2026-09-22T00:00:00Z", "value": "68.4" }
  ]
}
```

Рост / цель: GET + PATCH `/me` (`height_cm`, `weight_goal_kg`).

### L7. Фотопрогресс

| Method | URL | Body |
|--------|-----|------|
| GET | `/client/photo-progress` | сеты + `images[]` (`id`, `angle`, `image_url`) |
| POST | `/client/photo-progress` | `multipart/form-data` |

| Form | Type | Required | Default | Notes |
|------|------|----------|---------|-------|
| taken_on | date | yes | | `YYYY-MM-DD` |
| angles | string | no | `front` | `front,side,back` |
| files | file[] | yes | | до 3 JPEG/PNG |

Ответ: `{ "id", "taken_on", "images": [{ "id", "angle", "image_url" }] }`.  
DELETE фотосета нет.

### L8. Уведомления

См. §4. `tab=today` / `tab=later`.

### L9–L10. Заметки

- GET `/client/notes?q=` — массив, **без пагинации**. `q` optional.
- GET `/client/trainer-notes` — read-only. Поля: `id`, `text`, `created_at`, `trainer_id`, `trainer_name`.
- Отдельного GET `/client/notes/{id}` нет.

```json
{
  "id": 5,
  "title": "Самочувствие",
  "body": "После приседа колено…",
  "created_at": "2026-09-21T09:00:00Z",
  "updated_at": "2026-09-21T09:00:00Z"
}
```

| Method | URL | Body |
|--------|-----|------|
| POST | `/client/notes` | `title` required; `body` default `""` |
| PATCH | `/client/notes/{id}` | полная модель: `title` + `body` |
| DELETE | `/client/notes/{id}` | нет тела → `{ "ok": true }` |

### L11. Каталог программ

Те же Shared API, что у Coach (§5 C11): `/programs`, save, duplicate, share.

### L12. Тренеры / отзыв / закладка

| Method | URL | Query / Body |
|--------|-----|--------------|
| GET | `/trainers` | `category`, `q`, `sort=rating\|clients\|newest`, `page` |
| GET | `/trainers/{id}` | профиль + программы |
| GET | `/trainers/{id}/reviews` | |
| POST | `/trainers/{id}/reviews` | `rating` decimal 1–5 required; `text` default `""` max 1000 |
| GET | `/me/trainer-bookmarks` | |
| POST | `/trainers/{id}/bookmark` | нет тела |
| DELETE | `/trainers/{id}/bookmark` | нет тела |

### L13. Заявка тренеру

POST `/trainers/{trainer_id}/request` — тело **не нужно**. Статус `pending`.  
Тренер видит в GET `/trainer/requests`.

### L14. Профиль клиента

GET/PATCH `/me`, POST `/me/avatar`, GET `/me/subscription?audience=pro_client`.

### L15. Подписка PRO

`audience=pro_client`. См. §4 Billing.

### L16. Настройки / FAQ / legal / logout

GET + PATCH `/me/notification-preferences`, POST `/auth/change-password`, GET `/faq?audience=client`, POST `/support/tickets`, GET `/legal/{doc_type}`, POST `/auth/logout`.

---

## 7. Чеклист

### Coach

| # | Экран | Главные API |
|---|-------|-------------|
| C1 | Dashboard | `/trainer/dashboard`, calendar, attention, reports, `/me` |
| C2 | Календарь | `/trainer/calendar*` |
| C3 | Живая сессия | `/sessions*` |
| C4 | Отчёт | `/trainer/reports` |
| C5 | Клиенты | `GET /trainer/clients` |
| C6 | Поиск клиента | `POST …/search`, `POST /trainer/clients` |
| C7 | Ручное добавление | `POST …/manual` |
| C8 | Внимание | `/trainer/attention` |
| C9 | Карточка клиента | `/trainer/clients/{link_id}*` |
| C10 | Заявки | `/trainer/requests*` |
| C11 | Каталог программ | `/programs`, `/dictionaries` |
| C12 | Создать программу | `POST/PATCH /programs`, days, exercises |
| C13 | Marketplace + PRO | `/trainers`, `/plans` |
| C14–C16 | Профиль / цены | `/me`, `/trainer/profile` |
| C17 | PRO | billing `pro_trainer` |
| C18–C22 | Settings, FAQ, legal, logout | prefs, FAQ, legal, logout |

### Client

| # | Экран | Главные API |
|---|-------|-------------|
| L1 | Обзор | `GET /client/home`, `/me` |
| L2 | История тренировок | `GET /client/sessions` |
| L3 | Карточка тренировки | `GET /client/sessions/{id}` |
| L4–L5 | Замеры | `GET/POST/PATCH /client/measurements` |
| L6 | График | `GET /client/progress`, `/client/measurements/chart` |
| L7 | Фотопрогресс | `GET/POST /client/photo-progress` |
| L8 | Уведомления | `/notifications*` |
| L9–L10 | Заметки | `/client/notes*`, `/client/trainer-notes` |
| L11 | Программы | `/programs*` |
| L12 | Тренеры | `/trainers*`, reviews, bookmark |
| L13 | Заявка | `POST /trainers/{id}/request` |
| L14–L16 | Профиль, PRO, settings | `/me`, billing `pro_client`, FAQ, legal |
