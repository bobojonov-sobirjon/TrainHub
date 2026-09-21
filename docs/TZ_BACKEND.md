# TrainHub — Backend texnik topshiriq (TZ)

**Mahsulot:** TrainHub (klient + trener + admin)  
**Hujjat turi:** backend TZ (modullar, entity, API, biznes qoidalar)  
**Holat:** to‘liq Figma qismi (auth login/register ekranlari hali yo‘q)  
**Versiya:** 0.2 · 2026-09-19  
**Til:** ilova UI — rus; API xabarlar — `ru` (keyin `uz`/`en` ixtiyoriy)

---

## 1. Maqsad

TrainHub — trener va klientlar uchun yagona fitness platforma.

**Klient:**

- home: vazn, progress %, davomat, oxirgi mashg‘ulot;
- mashg‘ulotlar tarixi, o‘lchamlar, tana progressi, foto-progress, shaxsiy izohlar;
- tayyor dasturlar katalogi, saqlash / dublikat;
- trenerlar marketplace + **klient PRO** (trener dasturlari, video, nazorat).

**Trener:**

- dashboard, klientlar bazasi, jonli sessiya;
- kalendar: yangi / rejalashtirish, takrorlash, eslatma, statuslar;
- o‘z profili, ixtisoslik, narx, bepul konsultatsiya;
- **trener PRO**: cheksiz klient, katalog, kengaytirilgan statistika, 24/7 support;
- to‘lov tarixi, karta, avto-yangilash, bekor qilish.

Backend yagona API. Rol: `client` | `trainer` | `admin`.

---

## 2. Rollar va ruxsatlar

| Rol | Kim | Asosiy huquq |
|-----|-----|----------------|
| `client` | oddiy foydalanuvchi | o‘z home, mashg‘ulotlar, o‘lcham, progress, izoh, katalog, klient PRO |
| `trainer` | murabbiy | klientlar, sessiya, kalendar, profil/narx, trener PRO |
| `admin` | ichki | katalog, FAQ/legal, trener verify, to‘lov, ticket |

**Muhim:**

- Bir user **ikkala rol**ga ega bo‘lishi mumkin.
- Trener klientni **bazadan qidirib** yoki **qo‘lda** qo‘shadi.
- Qo‘lda yaratilgan — `is_shadow = true`. Keyin merge.
- **Ikki xil PRO:** `pro_client` va `pro_trainer` — alohida tarif.

---

## 3. Qamrab olingan ekranlar

### 3.1 Klient — katalog / marketplace (qism 1)

| Ekran | Funksiya |
|-------|----------|
| Готовые тренировки | dasturlar katalogi + filter |
| Фильтр | level / maqsad / uskunа |
| Программа | detail, saqlash, tahrir, ulashish, dublikat, o‘chirish |
| Тренеры от профи | banner + dastur/trener tab + kategoriya (все / силовые / кардио / женский фитнес) |
| Профиль тренера | reyting, tajriba, dastur, haftalik reja |
| Программа тренера | narx, davomiylik, kunlar |

### 3.2 Klient — home / progress (qism 2)

| Ekran | Funksiya |
|-------|----------|
| Главная (Обзор) | vazn, progress %, kunlar, vazn grafigi, davomat kalendari, oxirgi mashg‘ulot |
| Тренировки | tarix, filter, sort, sessiya detail (mashq + setlar) |
| Замеры | asosiy parametrlar + tana o‘lchamlari, tahrirlash |
| Прогресс | vazn/yog‘/mushak/suv/BMI, tana parametrlari delta, foto-progress |
| Параметры тела | har bir o‘lcham + o‘zgarish |
| Фото-прогресс | oy/kun to‘plamlari (oldi/yon/orqa), + qo‘shish |
| Заметки | qidiruv, CRUD, empty |
| Уведомления | ro‘yxat / empty |

### 3.3 Trener — operatsion (qism 1+2)

| Ekran | Funksiya |
|-------|----------|
| Dashboard | 4 widget |
| Клиенты | ro‘yxat, filter, sort, qo‘shish (qidiruv / qo‘lda) |
| Профиль клиента | statistika, o‘lcham, davomat, tarix |
| Тип / live / yakun | sessiya |
| Упражнения | qidiruv, yaratish, uskunа/mushak |
| Уведомления | bugun / keyinroq |
| Календарь | kunlik slot, edit/delete, + |
| Назначить тренировку | sana, vaqt, klient, format, tur, mushak, izoh, eslatma |
| Детали тренировки | klient, qo‘ng‘iroq, tahrir, bekor, reja, Старт |
| Новая / запланированная | to‘liq forma + status + haftalik takror + eslatma |
| Выбор клиента | radio-ro‘yxat |
| Тип тренировки | 8 tur, multi-select |
| Отчёт / Внимание | statistika, no-show |

### 3.4 Trener — profil, PRO, yordam (qism 2)

| Ekran | Funksiya |
|-------|----------|
| Профиль | avatar, ism, «Персональный тренер», klient/tajriba/reyting, menyu |
| Личные данные | foto, FIO, telefon, email, tug‘ilgan kun, «о себе» 300, staj |
| Специализация и цены | maqsad chip, ish formati, narx, davomiylik, bepul konsultatsiya |
| Подписка PRO | tarif, foyda, faol muddat, boshqarish, qayta yoqish |
| История платежей | sana, summa, paid/refund, chek |
| Управление подпиской | oy/yil, karta, avto-yangilash, bekor modal |
| Уведомления (sozlama) | push/email + event flaglar |
| Настройки | parol, app versiya |
| Центр помощи | FAQ qidiruv, ticket |
| Условия / Конфиденциальность | CMS sahifalar |
| Выйти | logout tasdiq |

---

## 4. Spravochniklar (enums)

DB: `code` + `title_ru` (+ keyin i18n).

### 4.1 Level — `workout_level`

| code | UI |
|------|-----|
| `beginner` | Новичок |
| `intermediate` | Средний |
| `advanced` | Продвинутый |

### 4.2 Goal — `fitness_goal`

| code | UI |
|------|-----|
| `gain_muscle` | Нарастить мышцы / Набор массы |
| `strength` | Сила |
| `lose_weight` | Сбросить вес / Похудение |
| `maintain` | Поддержание формы |
| `definition` | Рельеф |
| `flexibility` | Гибкость |
| `rehab` | Реабилитация |
| `endurance` | Выносливость |

### 4.3 Equipment — `equipment`

| code | UI |
|------|-----|
| `none` | Нет (свой вес) |
| `dumbbells` | Гантели |
| `kettlebell` | Гиря |
| `plate` | Диск |
| `bench` | Скамья для жима |
| `machine` | Машина |
| `gym` | Тренажёрный зал |
| `other` | Другое |

### 4.4 Muscle group — `muscle_group`

| code | UI |
|------|-----|
| `neck` | Шея |
| `shoulders` | Плечи |
| `chest` | Грудь |
| `back` | Спина |
| `waist` | Талия / пресс |
| `glutes` | Ягодицы |
| `thighs` | Бёдра / ноги |
| `calves` | Икры |
| `biceps` | Бицепс |
| `triceps` | Трицепс |
| `forearms` | Предплечья |
| `arms` | Руки (filter guruhi) |
| `other` | Другое |

### 4.5 Training format — `training_format`

| code | UI |
|------|-----|
| `gym` | В зале |
| `online` | Онлайн |
| `hybrid` | Онлайн + офлайн |
| `home` | Дома (klient filter) |
| `visit` | Выезд к клиенту (trener ish formati) |

### 4.6 Client status

| code | UI |
|------|-----|
| `new` | Новые |
| `permanent` | Постоянные |
| `paused` | ixtiyoriy |
| `archived` | ixtiyoriy |

### 4.7 Session / event type — `workout_kind`

Kalendar va sessiya **multi-select** (ekran: «Силовая, Кардио +2»).

| code | UI |
|------|-----|
| `strength` | Силовая |
| `functional` | Функциональный тренинг |
| `cardio` | Кардио |
| `stretching` | Растяжка |
| `circuit` | Круговая |
| `interval` | Интервальная |
| `rehab` | Реабилитация |
| `endurance` | Выносливость |

### 4.8 Session start source

| code | UI |
|------|-----|
| `new` | Новая тренировка |
| `planned` | Запланированная |
| `ready_program` | Готовая тренировка |
| `trainer_program` | Тренировка от профи (klient PRO) |

### 4.9 Calendar / session status

| code | UI |
|------|-----|
| `scheduled` | Предстоящая |
| `in_progress` | Идёт |
| `completed` | Завершена |
| `cancelled` | Отменена |
| `no_show` | Пропущена |

### 4.10 Reminder offset

| code | UI |
|------|-----|
| `none` | Не напоминать |
| `1h` | За 1 час |
| `3h` | За 3 часа |

### 4.11 Marketplace trainer category

| code | UI |
|------|-----|
| `all` | Все |
| `strength` | Силовые |
| `cardio` | Кардио |
| `female` | Женский фитнес |

### 4.12 Photo angle

| code | UI |
|------|-----|
| `front` | Анфас |
| `side` | Сбоку |
| `back` | Сзади |

### 4.13 Notification type

| code | Kim | Misol |
|------|-----|--------|
| `workout_reminder` | ikkala | Тренировка через 30 мин / за 1 час |
| `feedback_request` | klient | Оставьте отзыв |
| `goal` | klient | Новая цель добавлена |
| `progress` | klient | Новый рекорд |
| `attention` | trener | Клиент пропустил |
| `invite` | klient | Тренер сизни bazaga qo‘shdi |
| `new_client_request` | trener | Новая заявка клиента |
| `client_report` | trener | Отчёты по клиентам |

### 4.14 Subscription audience

| code | Kim | Foyda (ekran) |
|------|-----|----------------|
| `pro_client` | klient | trener dasturlari, video, nazorat, «от профи» |
| `pro_trainer` | trener | чексиз клиент, готовые программы, расширенная статистика, приоритетная поддержка 24/7 |

### 4.15 Payment status

| code | UI |
|------|-----|
| `pending` | Ожидание |
| `paid` | Оплачено |
| `refunded` | Возврат / ошибка оплаты |
| `failed` | Ошибка |

### 4.16 Support ticket status

`open` | `in_progress` | `answered` | `closed`

---

## 5. Ma’lumotlar modeli

### 5.1 User

```
User
  id
  public_id              # ID450692330
  role_flags             # client / trainer
  first_name
  last_name
  email                  # unique, nullable
  phone                  # unique, E.164
  password_hash
  avatar_url
  gender                 # male | female | other | null
  birth_date
  height_cm
  is_shadow
  created_at
  updated_at
  last_login_at
```

```
NotificationPreference
  user_id
  push_enabled           # default true
  email_enabled          # default false
  workout_reminder       # default true
  new_client_request     # trainer, default true
  client_report          # trainer, default false
```

```
DeviceToken
  user_id
  platform               # ios | android
  token
  updated_at
```

### 5.2 TrainerProfile

```
TrainerProfile
  user_id                PK/FK
  bio                    # «О себе», max 300
  experience_years
  specializations[]      # fitness_goal M2M
  work_formats[]         # gym | online | visit
  session_price_amount   # 2500
  session_price_currency # RUB
  session_duration_min   # 60
  free_first_consult     # bool
  category               # strength | cardio | female | null
  rating_avg
  reviews_count
  clients_count
  programs_count
  is_verified
  cover_url
```

Marketplace karta: ism, avatar, reyting, dasturlar soni, kategoriya.

### 5.3 Subscription (ikkita PRO)

Checkout: oy **90.99 ₽**, yil **15 000 ₽**, yillik badge **~40%**.  
Boshqaruvda yillik **25%** chegirma ko‘rinishi mumkin — **manba: `SubscriptionPlan.discount_pct`**.

```
SubscriptionPlan
  id
  audience           # pro_client | pro_trainer
  code               # trainer_pro_month | trainer_pro_year | client_pro_month | client_pro_year
  period             # month | year
  price_amount
  currency           # RUB
  discount_pct       # 25 / 40, UI badge
  is_active

Subscription
  id
  user_id
  plan_id
  audience
  status             # active | expired | cancelled | pending
  starts_at
  ends_at            # UI: «Активна до 14 сентября 2026»
  auto_renew         # default true
  cancel_at_period_end
  payment_method_id
  provider           # stripe | yookassa | … (tanlanadi)
  external_id

PaymentMethod
  id
  user_id
  brand              # visa
  last4              # 4417
  exp_month
  exp_year
  provider_ref
  is_default

Payment
  id
  user_id
  subscription_id
  amount
  currency
  status             # paid | refunded | failed
  paid_at
  receipt_url        # «Подробнее» / chek
  external_id
```

**Trener PRO ochadi:**

- cheksiz klient (bepul limit — default **5**, sozlanadi);
- tayyor dasturlar katalogi trenerga;
- kengaytirilgan statistika;
- prioritet support 24/7.

**Klient PRO ochadi:**

- marketplace trener dasturlari (2–8 hafta va h.k.);
- video-instruksiya;
- trener nazorati;
- «Тренировка от профи».

Bepul: 1-hafta preview (ekran: «Доступно с PRO — недели 2–8»).

### 5.4 Program

```
Program
  id
  author_id              # null = platforma; trainer = muallif
  source                 # catalog | trainer | user_copy
  title
  slug
  cover_url
  description
  level
  goals[]
  equipment[]
  workouts_per_week
  duration_weeks
  is_pro
  price_amount           # null — umumiy PRO ochadi
  currency
  status                 # draft | published | archived
  saves_count
  created_at
```

```
ProgramWeek                  # «Неделя 1 — Адаптация»
  id
  program_id
  week_index                 # 1..N
  title
  is_preview                 # 1-hafta bepul
```

```
ProgramDay
  id
  program_id
  week_id                    # nullable
  title                      # Жимы / День 1 — Всё тело
  description
  sort_order
  duration_min               # 45, 30, 40
  focus_muscles[]
```

```
ProgramDayExercise
  id
  program_day_id
  exercise_id
  sort_order
  sets
  reps_min
  reps_max
  note
```

| Action | Backend |
|--------|---------|
| Сохранить программу | `UserProgram` |
| Дублировать | `Program.source=user_copy` |
| Редактировать | faqat o‘z copy / o‘z dasturi |
| Поделиться | `/p/{id}` yoki token |
| Удалить | soft-delete o‘z copy |

```
UserProgram
  user_id
  program_id
  saved_at
  unique(user_id, program_id)
```

### 5.5 Exercise

```
Exercise
  id
  owner_id
  name
  photo_url
  video_url
  equipment_id
  primary_muscle_id
  secondary_muscles[]
  exercise_type          # strength | cardio | mobility | other
  is_public
  created_at
```

### 5.6 Trainer ↔ Client

```
TrainerClient
  id
  trainer_id
  client_id
  status
  training_format
  goals[]
  invited_via            # search | manual | request
  created_at
  archived_at
```

```
ClientRequest                # «Новые заявки клиентов»
  id
  trainer_id
  client_id
  status                 # pending | accepted | rejected
  created_at
```

```
TrainerNote                  # trener → klient izohi (anketa)
  id
  trainer_client_id
  text
  created_by
  created_at
  deleted_at
```

```
BodyMeasurement
  id
  client_id
  recorded_by
  recorded_at
  weight_kg
  body_fat_pct
  muscle_mass_kg
  water_pct
  chest_cm
  back_cm
  waist_cm
  hips_cm
  thigh_cm
  calf_cm
  neck_cm
  shoulders_cm
  arm_cm
  forearm_cm
  # BMI = weight / (height_m^2), saqlanmasa ham hisoblanadi
```

Klient «Замеры»: jins, yosh, bo‘y, vazn + tana o‘lchamlari. Har qator oxirida ✓ = oxirgi qiymat kiritilgan.

### 5.7 WorkoutSession

```
WorkoutSession
  id
  trainer_id
  lead_client_id
  source                 # new | planned | ready_program | trainer_program
  kinds[]                # workout_kind M2M
  program_day_id
  calendar_event_id
  status
  started_at
  finished_at
  duration_sec
  calories
  distance_km
  notes
```

```
WorkoutSessionClient
  session_id
  client_id
  unique(session_id, client_id)
```

```
SessionExercise
  id
  session_id
  exercise_id
  sort_order
  status                 # pending | active | done | skipped
```

```
SessionSet
  id
  session_exercise_id
  set_index
  weight_kg
  reps
  is_warmup
  completed_at
```

Yakun modal: daqiqa, `exercises_done/total`, kcal.

### 5.8 CalendarEvent

```
CalendarEvent
  id
  trainer_id
  client_id
  session_id
  starts_at
  ends_at
  duration_min
  format                 # gym | online | visit
  kinds[]
  focus_muscles[]
  status                 # scheduled | completed | cancelled | no_show
  note
  reminder               # none | 1h | 3h
  repeat_weekly          # bool
  rrule                  # agar weekly: FREQ=WEEKLY
  repeat_until
  created_at
```

**«Назначить» / «Новая» maydonlari:**

- sana, vaqt dan–gacha (yoki start + duration);
- klient (majburiy yangi/reja);
- format;
- turlar (multi);
- mushaklar;
- status (yaratishda odatda `scheduled`);
- `repeat_weekly`;
- `reminder`;
- izoh.

**Detail actions:** Изменить, Отменить, телефон (klient.phone), **Начать тренировку** → session.

**Haftalik takror:** parent event + generated occurrences (yoki har bir occurrence alohida qator, `parent_id`).

### 5.9 Notifications

```
Notification
  id
  user_id
  type
  title
  body
  payload_json
  is_read
  group                  # today | later   (scheduled_at vs now)
  scheduled_at
  created_at
```

Reminder: `CalendarEvent.reminder` + `NotificationPreference.workout_reminder` + `push_enabled`.

### 5.10 Attention

```
AttentionItem
  id
  trainer_id
  client_id
  reason                 # missed_session | inactive | open_task
  ref_type / ref_id
  is_resolved
  created_at
```

Vaqti o‘tgan `scheduled` + session yo‘q → `no_show` + attention.

### 5.11 Review

```
TrainerReview
  id
  trainer_id
  client_id
  rating                 # 1–5
  text
  created_at
```

### 5.12 Klient shaxsiy izohlar (Заметки)

Trener izohidan **alohida**. Klient o‘zi yozadi.

```
PersonalNote
  id
  user_id
  title                  # «План на следующую неделю»
  body
  created_at
  updated_at
  deleted_at
```

Empty: «У вас пока нет заметок».

### 5.13 Foto-progress

```
PhotoProgressSet
  id
  user_id
  taken_on               # 2026-02-05
  month_label            # «1 месяц», «2 месяца» — taken_on − first_set
  created_at
```

```
PhotoProgressImage
  id
  set_id
  angle                  # front | side | back
  image_url
  sort_order
```

Bir setda odatda 3 foto. `+` yangi set.

### 5.14 Help / legal / support

```
FaqArticle
  id
  slug
  question
  answer
  audience               # trainer | client | all
  sort_order
  is_published
```

FAQ misol (ekran):

- Как добавить нового клиента?
- Как изменить тренировку?
- Как работает подписка PRO?
- Как изменить цену занятия?
- Как удалить аккаунт и клиентов?

```
LegalDocument
  id
  type                   # terms | privacy
  version
  body_md
  published_at
```

**Условия:** общие положения, аккаунт тренера, PRO (автопродление), ограничение ответственности.  
**Конфиденциальность:** какие данные, зачем, хранение, права.

```
SupportTicket
  id
  user_id
  subject
  message
  status
  created_at
```

SLA matn: 24 soat. Trener PRO — prioritet navbat.

---

## 6. API (REST, `/api/v1`)

Umumiy:

- `Authorization: Bearer <access>`
- Pagination: `page`, `page_size` → `{ count, next, previous, results }`
- Xato: `{ "detail", "code" }`
- Vaqt: ISO-8601 UTC

---

### 6.1 Auth (ekranlar qisman: parol + logout)

Login/register UI yo‘q, lekin profil uchun kerak:

```
POST /auth/login
POST /auth/refresh
POST /auth/logout                    # token revoke
POST /auth/change-password
  body: { old_password, new_password }

POST /auth/register                  # ekran kelganda
POST /auth/otp/*                     # ekran kelganda
```

---

### 6.2 Spravochniklar

```
GET /dictionaries
  → levels, goals, equipment, muscles, formats,
    client_statuses, workout_kinds, reminders,
    trainer_categories, photo_angles, plans
```

---

### 6.3 Me (profil)

```
GET  /me
PATCH /me
  body: first_name, last_name, email, phone, birth_date, gender, height_cm, avatar

POST /me/avatar                      # multipart

GET  /me/notification-preferences
PATCH /me/notification-preferences
  body: { push_enabled, email_enabled, workout_reminder, new_client_request, client_report }

POST /me/devices
  body: { platform, token }
```

---

### 6.4 Trener profili (o‘zi)

```
GET  /trainer/profile
PATCH /trainer/profile
  body: {
    bio, experience_years,
    specializations[], work_formats[],
    session_price_amount, session_duration_min,
    free_first_consult, category
  }
```

Validatsiya: `bio` ≤ 300; narx > 0; davomiylik 15–180.

---

### 6.5 Katalog

```
GET /programs
  ?level=&goal=&equipment=&source=&is_pro=&q=&author_id=
GET /programs/{id}
POST /programs/{id}/save
DELETE /programs/{id}/save
POST /programs/{id}/duplicate
PATCH /programs/{id}
DELETE /programs/{id}
GET /programs/{id}/share
```

PRO bo‘lmasa `weeks` da `is_preview=false` yopiq: `locked=true`.  
Filter count: «Показать 15 результатов».

---

### 6.6 Marketplace

```
GET /trainers
  ?q=&category=strength|cardio|female&sort=rating|clients|newest
  → { avatar, name, rating, programs_count, category }

GET /trainers/{id}
  → profile + stats + programs[] + weeks preview

GET /trainers/{id}/reviews
```

Tab «Программы» / «Тренеры» — `source=trainer` vs `GET /trainers`.

---

### 6.7 Subscription + to‘lov

```
GET  /plans?audience=pro_client|pro_trainer

GET  /me/subscription?audience=
POST /me/subscription/checkout
  body: { plan_id, payment_method_id? }
POST /me/subscription/resume
PATCH /me/subscription
  body: { plan_id?, auto_renew?, payment_method_id? }
POST /me/subscription/cancel
  → cancel_at_period_end=true, ends_at saqlanadi
  # modal: «PRO до 14 сентября, функции до этой даты»

GET  /me/payments
GET  /me/payments/{id}/receipt      # redirect yoki file

GET  /me/payment-methods
POST /me/payment-methods
PATCH /me/payment-methods/{id}
DELETE /me/payment-methods/{id}

POST /webhooks/payments
```

Bekor modal: Остаться / Отменить.

---

### 6.8 Trener dashboard

```
GET /trainer/dashboard
  → {
      trainer: { name, public_id, avatar },
      unread_notifications,
      clients: { count, hint },
      today_workouts: { done, planned },
      month_report: { sessions_count },
      attention: { count, hint }
    }
```

Profil header: `{ clients_count, experience_years, rating_avg }`.

---

### 6.9 Klientlar (trener)

```
GET /trainer/clients
  ?q=&gender=&format=&status=&sort=alpha|newest|oldest

GET /trainer/clients/{id}

POST /trainer/clients/search
  body: { query }

POST /trainer/clients
  body: { user_id }

POST /trainer/clients/manual
  body: { first_name, last_name, email, phone, birth_date,
          gender, goals[], training_format, measurements, notes[] }

PATCH /trainer/clients/{id}
DELETE /trainer/clients/{id}

GET  /trainer/clients/{id}/measurements
POST /trainer/clients/{id}/measurements
GET  /trainer/clients/{id}/measurements/chart?metric=&from=&to=

GET  /trainer/clients/{id}/notes
POST /trainer/clients/{id}/notes
DELETE /trainer/clients/{id}/notes/{note_id}

GET /trainer/clients/{id}/stats
GET /trainer/clients/{id}/sessions

GET  /trainer/requests
POST /trainer/requests/{id}/accept
POST /trainer/requests/{id}/reject
```

Qidiruv: ≥3 belgi; yo‘q — «Пользователь не найден»; `already_added`.

**Trener PRO limitsiz klient.** Bepul: `clients_count >= FREE_CLIENT_LIMIT` → `403 trainer_pro_required`.

---

### 6.10 Mashqlar

```
GET /exercises?q=&equipment=&muscle=&scope=global|mine|recent
POST /exercises
GET /exercises/{id}
PATCH /exercises/{id}
DELETE /exercises/{id}
```

---

### 6.11 Sessiya

```
POST /sessions
  body: { source, client_ids[], kinds[], program_day_id?, calendar_event_id?, exercises? }

GET /sessions/{id}
PATCH /sessions/{id}

POST /sessions/{id}/exercises
PATCH /sessions/{id}/exercises/{eid}
POST /sessions/{id}/exercises/{eid}/sets
PATCH /sessions/{id}/sets/{set_id}
DELETE /sessions/{id}/sets/{set_id}

POST /sessions/{id}/complete
GET /sessions/{id}/previous/{exercise_id}?client_id=
```

---

### 6.12 Kalendar

```
GET /trainer/calendar?date=&from=&to=

POST /trainer/calendar
  body: {
    client_id, starts_at, ends_at,
    format, kinds[], focus_muscles[],
    note, reminder, repeat_weekly, status
  }

PATCH /trainer/calendar/{id}
DELETE /trainer/calendar/{id}
POST /trainer/calendar/{id}/cancel     # status=cancelled
POST /trainer/calendar/{id}/start-session
```

Repeat o‘zgartirish: `scope=this|this_and_future|all`.

---

### 6.13 Hisobot / attention / notifications

```
GET /trainer/reports?period=month&date=
GET /trainer/attention
POST /trainer/attention/{id}/resolve

GET /notifications?tab=today|later
POST /notifications/{id}/read
POST /notifications/read-all
```

---

### 6.14 Klient home + mashg‘ulotlar

```
GET /client/home
  → {
      weight_kg, progress_pct, days_in_program,
      weight_chart: [{ date, value }],
      attendance_30d: [{ date, status: present|missed|none }],
      last_session: { id, minutes, exercises, kcal, date }
    }

GET /client/sessions
  ?kind=&format=&with_trainer=true|false
  &duration_min=&duration_max=
  &sort=newest|oldest|duration_asc|duration_desc

GET /client/sessions/{id}
  → header (date, minutes, sets, kcal) + exercises[] + sets[]
```

Filter: вид (зал/дом/улица), длительность, с тренером.  
Sort: сначала новые / старые / от коротких / от длинных.

---

### 6.15 Klient o‘lcham / progress / foto / izoh

```
GET  /client/measurements
POST /client/measurements
PATCH /client/measurements/{id}
GET  /client/measurements/current
  → basic { gender, age, height, weight } + parts[] + bmi

GET /client/progress
  → {
      weight, fat_pct, muscle_kg, water_pct, bmi,
      deltas, charts, body_params[], photo_sets_preview
    }

GET  /client/photo-progress
POST /client/photo-progress          # multipart 1–3 image + taken_on + angles
GET  /client/photo-progress/{id}
DELETE /client/photo-progress/{id}

GET  /client/notes?q=
POST /client/notes                   # { title, body }
PATCH /client/notes/{id}
DELETE /client/notes/{id}
```

---

### 6.16 Help / legal

```
GET /faq?q=&audience=
GET /faq/{slug}

GET /legal/terms
GET /legal/privacy

POST /support/tickets
  body: { subject, message }
GET /support/tickets
```

App versiya: `GET /meta` → `{ ios_min, android_min, latest }` — sozlamada `2.4.1` client hardcode ham bo‘lishi mumkin.

---

## 7. Biznes qoidalar

1. Katalog dasturi o‘zgarmas; tahrir = avval `duplicate`.
2. Save idempotent.
3. **Klient PRO** yo‘q: trener dasturi 1-hafta preview, qolgani `locked`.
4. Default: **obuna ochadi audience bo‘yicha barcha PRO kontent**. Yakka dastur xaridi yo‘q.
5. **Trener PRO** yo‘q: `FREE_CLIENT_LIMIT` (5). Yangi klient — `403`.
6. Shadow client merge: telefon/email/public_id mos kelsa.
7. `new` → `permanent`: N=3 completed session yoki qo‘lda.
8. Bugungi widget: shu kun event + completed session.
9. Kcal: MVP MET yoki `duration × weight × k`.
10. Kalendar overlap: ruxsat + `has_conflict` flag (yoki 409 — default flag).
11. `ends_at` o‘tdi, session yo‘q → `no_show` + Attention.
12. `repeat_weekly=true`: kelasi occurrence’lar generate (horizon 12 hafta).
13. Reminder job: `starts_at - offset`, pref va push yoqilgan bo‘lsa.
14. Bekor qilingan obuna: `ends_at` gacha funksiya ishlaydi.
15. Refund qatori to‘lov tarixida `refunded`.
16. Custom exercise `is_public=false`.
17. Media: foto 10 MB, video 100 MB; progress foto 3 angle / set.
18. Qidiruv: telefon 6–11 raqam, email iexact, public_id exact.
19. Soft delete: program copy, notes, custom exercise, photo set.
20. Trener faqat o‘z klientini; klient faqat o‘zini.
21. `bio` ≤ 300. Ticketga javob 24 soat (PRO — prioritet).
22. Logout: refresh+access blacklist / family revoke.
23. Parol: old_password tekshiruv, min 8.
24. Klient `progress_pct`: maqsad vaznga nisbatan (start → target). Target yo‘q bo‘lsa 0 yoki vazn dinamikasi.
25. Foto «N месяц»: birinchi set sanasidan oy farqi.
26. Trener `free_first_consult`: birinchi `CalendarEvent` narxsiz flag (to‘lov moduli keyin).

---

## 8. Empty / hint matnlar

| Joy | Shart | Matn (ru) |
|-----|--------|-----------|
| Клиенты | 0 | Пока нет клиентов |
| Сегодня | 0/0 | Плана на сегодня нет |
| Отчёт | 0 | За этот месяц |
| Внимание | 0 | Задач нет |
| Уведомления | 0 | Уведомлений пока нет |
| Qidiruv user | no match | Пользователь не найден |
| Заметки | 0 | У вас пока нет заметок |
| FAQ | no match | Не нашли ответ? |

API `empty_code` / `hint` qaytarsin.

---

## 9. Non-functional

| Band | Talab |
|------|--------|
| Stack | Django + DRF + PostgreSQL + Redis |
| Auth | JWT access + refresh |
| Fayl | S3-compatible |
| Push | FCM + APNs |
| To‘lov | provider alohida tanlanadi (YooKassa / Stripe / CloudPayments) — webhook majburiy |
| Job | Celery: reminder, no_show, subscription expire, repeat generate, receipt |
| Til | `Accept-Language` |
| Legal | terms/privacy versiyalanadi |
| Admin | user, program, exercise, plan, payment, FAQ, ticket, trener verify |
| Test | filter, save/duplicate, session complete, calendar repeat, checkout/cancel, notes, photo set, PRO lock |

---

## 10. Hali ochiq

- [ ] Login / register / OTP / onboarding (ekran yo‘q)
- [ ] Chat
- [ ] Trener dastur yaratish wizard (to‘liq constructor)
- [ ] Video player / streaming
- [ ] Admin panel UI
- [ ] Akkauntni o‘chirish oqimi (FAQ da bor, alohida ekran yo‘q)
- [ ] To‘lov provayderi aniq tanlov

Parol almashtirish, logout, PRO checkout/boshqaruv — **yozilgan**.

---

## 11. Implementatsiya tartibi

1. User, dictionaries, media, `/me`, password, logout  
2. Program katalog + filter + save/duplicate + week lock  
3. TrainerClient + search/manual + measurements  
4. Exercise + live session + complete  
5. Calendar (assign, repeat, reminder, start)  
6. Dashboard / reports / attention / notifications + prefs  
7. Trainer profile + specialization/price  
8. Plans + checkout + payments + cancel/resume  
9. Client home, sessions filter/sort, progress, photo, personal notes  
10. FAQ, legal, support tickets  
11. Auth register/OTP — ekran kelgach  

---

## 12. O‘zgarishlar jurnali

| Ver | Sana | Nima |
|-----|------|------|
| 0.1 | 2026-09-19 | Qism 1: katalog, dastur, marketplace, dashboard, klientlar, sessiya, mashq, kalendar, hisobot, e’tibor |
| 0.2 | 2026-09-19 | Qism 2: kalendar forma (tur, mushak, repeat, reminder, status), klient picker, 8 workout kind, trener profil/narx/consult, **alohida client vs trainer PRO**, to‘lov tarixi/karta/avto-renew/cancel, sozlamalar, FAQ/legal/ticket, **klient home**, sessiya filter/sort, o‘lcham+BMI+tarkib, foto-progress, shaxsiy izohlar |
