from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TrainerProfileIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "bio": "Силовой тренер, 8 лет стажа",
                    "experience_years": 8,
                    "specializations": ["strength", "lose_weight"],
                    "work_formats": ["gym", "online"],
                    "session_price_amount": "3500.00",
                    "session_duration_min": 60,
                    "free_first_consult": True,
                    "category": "strength",
                }
            ]
        }
    )

    bio: str | None = Field(default=None, max_length=300, description="О себе, до 300 символов", examples=["Силовой тренер, 8 лет стажа"])
    experience_years: int | None = Field(default=None, description="Опыт в годах", examples=[8])
    specializations: list[str] = Field(default_factory=list, description="Коды специализаций из справочника fitness_goal", examples=[["strength", "lose_weight"]])
    work_formats: list[str] = Field(default_factory=list, description="Коды форматов из справочника training_format", examples=[["gym", "online"]])
    session_price_amount: Decimal | None = Field(default=None, description="Цена сессии", examples=["3500.00"])
    session_duration_min: int | None = Field(default=None, ge=15, le=180, description="Длительность сессии, 15–180 мин", examples=[60])
    free_first_consult: bool | None = Field(default=None, description="Бесплатная первая консультация", examples=[True])
    category: str | None = Field(default=None, description="Категория тренера", examples=["strength"])


class TrainerProfileOut(BaseModel):
    user_id: int
    bio: str | None
    experience_years: int | None
    specializations: list[str]
    work_formats: list[str]
    session_price_amount: Decimal | None
    session_duration_min: int
    free_first_consult: bool
    category: str | None
    rating_avg: Decimal
    reviews_count: int
    clients_count: int = 0


class DashboardOut(BaseModel):
    clients_count: int
    today_done: int
    today_planned: int
    month_sessions: int
    attention_count: int


class MeasurementIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "weight_kg": "78.4",
                    "body_fat_pct": "18.2",
                    "muscle_mass_kg": "34.1",
                    "water_pct": "55.0",
                    "chest_cm": "102.0",
                    "back_cm": "110.0",
                    "waist_cm": "82.0",
                    "hips_cm": "96.0",
                    "thigh_cm": "58.0",
                    "calf_cm": "38.0",
                    "neck_cm": "38.0",
                    "shoulders_cm": "118.0",
                    "arm_cm": "36.0",
                    "forearm_cm": "29.0",
                }
            ]
        }
    )

    weight_kg: Decimal | None = Field(default=None, description="Вес, кг", examples=["78.4"])
    body_fat_pct: Decimal | None = Field(default=None, description="Жир, %", examples=["18.2"])
    muscle_mass_kg: Decimal | None = Field(default=None, description="Мышечная масса, кг", examples=["34.1"])
    water_pct: Decimal | None = Field(default=None, description="Вода, %", examples=["55.0"])
    chest_cm: Decimal | None = Field(default=None, description="Грудь, см", examples=["102.0"])
    back_cm: Decimal | None = Field(default=None, description="Спина, см", examples=["110.0"])
    waist_cm: Decimal | None = Field(default=None, description="Талия, см", examples=["82.0"])
    hips_cm: Decimal | None = Field(default=None, description="Бёдра, см", examples=["96.0"])
    thigh_cm: Decimal | None = Field(default=None, description="Бедро, см", examples=["58.0"])
    calf_cm: Decimal | None = Field(default=None, description="Икра, см", examples=["38.0"])
    neck_cm: Decimal | None = Field(default=None, description="Шея, см", examples=["38.0"])
    shoulders_cm: Decimal | None = Field(default=None, description="Плечи, см", examples=["118.0"])
    arm_cm: Decimal | None = Field(default=None, description="Рука, см", examples=["36.0"])
    forearm_cm: Decimal | None = Field(default=None, description="Предплечье, см", examples=["29.0"])


class ClientManualIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "first_name": "Анна",
                    "last_name": "Смирнова",
                    "email": "anna@example.com",
                    "phone": "+79001234567",
                    "birth_date": "1998-03-21",
                    "gender": "female",
                    "goals": ["lose_weight", "definition"],
                    "training_format": "gym",
                    "measurements": {"weight_kg": "62.0", "waist_cm": "70.0"},
                    "notes": ["Начала тренировки в сентябре"],
                    "contraindications": ["Боль в колене"],
                }
            ]
        }
    )

    first_name: str = Field(description="Имя клиента", examples=["Анна"])
    last_name: str = Field(default="", description="Фамилия", examples=["Смирнова"])
    email: str | None = Field(default=None, description="Email, необязателен для теневого аккаунта", examples=["anna@example.com"])
    phone: str | None = Field(default=None, description="Телефон", examples=["+79001234567"])
    birth_date: date | None = Field(default=None, description="Дата рождения", examples=["1998-03-21"])
    gender: str | None = Field(default=None, description="Пол: male, female, other", examples=["female"])
    goals: list[str] = Field(default_factory=list, description="Цели из справочника fitness_goal", examples=[["lose_weight"]])
    training_format: str | None = Field(default=None, description="Формат из справочника training_format", examples=["gym"])
    measurements: MeasurementIn | None = Field(default=None, description="Стартовые замеры")
    notes: list[str] = Field(default_factory=list, description="Заметки тренера", examples=[["Начала тренировки в сентябре"]])
    contraindications: list[str] = Field(default_factory=list, description="Противопоказания", examples=[["Боль в колене"]])


class ClientAddIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"user_id": 42}]})

    user_id: int = Field(description="ID существующего пользователя-клиента", examples=[42], ge=1)


class ClientPatchIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"status": "permanent", "goals": ["gain_muscle"], "training_format": "online"}]}
    )

    status: str | None = Field(default=None, description="Статус связи: new, permanent, paused, archived", examples=["permanent"])
    goals: list[str] | None = Field(default=None, description="Цели клиента", examples=[["gain_muscle"]])
    training_format: str | None = Field(default=None, description="Формат тренировок", examples=["online"])


class ClientCard(BaseModel):
    id: int
    client_id: int
    public_id: str
    first_name: str
    last_name: str
    avatar_url: str | None
    gender: str | None
    status: str
    training_format: str | None
    created_at: datetime


class CalendarIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "client_id": 12,
                    "starts_at": "2026-09-20T10:00:00+05:00",
                    "ends_at": "2026-09-20T11:00:00+05:00",
                    "format": "gym",
                    "kinds": ["strength"],
                    "focus_muscles": ["chest", "triceps"],
                    "note": "Жимовая тренировка",
                    "reminder": "1h",
                    "repeat_weekly": False,
                    "status": "scheduled",
                }
            ]
        }
    )

    client_id: int | None = Field(default=None, description="ID клиента. Пусто — личная тренировка тренера", examples=[12])
    starts_at: datetime = Field(description="Начало в ISO-8601", examples=["2026-09-20T10:00:00+05:00"])
    ends_at: datetime = Field(description="Окончание в ISO-8601", examples=["2026-09-20T11:00:00+05:00"])
    format: str | None = Field(default=None, description="Формат: gym, online, hybrid, home, visit", examples=["gym"])
    kinds: list[str] = Field(default_factory=list, description="Типы тренировки из workout_kind", examples=[["strength"]])
    focus_muscles: list[str] = Field(default_factory=list, description="Целевые мышцы из muscle_group", examples=[["chest", "triceps"]])
    note: str | None = Field(default=None, description="Комментарий к событию", examples=["Жимовая тренировка"])
    reminder: str = Field(default="none", description="Напоминание: none, 15m, 1h, 1d", examples=["1h"])
    repeat_weekly: bool = Field(default=False, description="Повторять каждую неделю", examples=[False])
    status: str = Field(default="scheduled", description="Статус: scheduled, cancelled, done", examples=["scheduled"])


class SetIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"weight_kg": "60.0", "reps": 10, "is_warmup": False}]})

    weight_kg: Decimal | None = Field(default=None, description="Вес, кг", examples=["60.0"])
    reps: int | None = Field(default=None, description="Повторения", examples=[10])
    is_warmup: bool = Field(default=False, description="Разминочный подход", examples=[False])


class SessionCreateIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "source": "new",
                    "client_ids": [12],
                    "kinds": ["strength"],
                    "program_day_id": None,
                    "calendar_event_id": None,
                }
            ]
        }
    )

    source: str = Field(default="new", description="Источник: new, planned, program", examples=["new"])
    client_ids: list[int] = Field(default_factory=list, description="Клиенты сессии (для тренера)", examples=[[12]])
    kinds: list[str] = Field(default_factory=list, description="Типы тренировки", examples=[["strength"]])
    program_day_id: int | None = Field(default=None, description="День программы, если старт из программы", examples=[5])
    calendar_event_id: int | None = Field(default=None, description="Событие календаря, если старт из плана", examples=[8])


class ExerciseCreateIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "Жим лёжа",
                    "equipment": "bench",
                    "primary_muscle": "chest",
                    "secondary_muscles": ["triceps", "shoulders"],
                    "exercise_type": "strength",
                    "photo_url": "https://cdn.example.com/bench-press.jpg",
                    "video_url": "https://cdn.example.com/bench-press.mp4",
                }
            ]
        }
    )

    name: str = Field(description="Название упражнения", examples=["Жим лёжа"])
    equipment: str | None = Field(default=None, description="Код оборудования из справочника equipment", examples=["bench"])
    primary_muscle: str | None = Field(default=None, description="Основная мышца из muscle_group", examples=["chest"])
    secondary_muscles: list[str] = Field(default_factory=list, description="Дополнительные мышцы", examples=[["triceps", "shoulders"]])
    exercise_type: str = Field(default="strength", description="Тип из workout_kind", examples=["strength"])
    photo_url: str | None = Field(default=None, description="URL фото", examples=["https://cdn.example.com/bench-press.jpg"])
    video_url: str | None = Field(default=None, description="URL видео", examples=["https://cdn.example.com/bench-press.mp4"])


class ProgramCreateIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Жимы / ноги (Начальный)",
                    "description": "Программа для новичка, 3 тренировки в неделю",
                    "level": "beginner",
                    "goals": ["gain_muscle"],
                    "equipment": ["gym"],
                    "workouts_per_week": 3,
                    "duration_weeks": 8,
                    "is_pro": False,
                    "source": "catalog",
                    "status": "published",
                }
            ]
        }
    )

    title: str = Field(description="Название программы", examples=["Жимы / ноги (Начальный)"])
    description: str | None = Field(default=None, description="Описание", examples=["Программа для новичка, 3 тренировки в неделю"])
    level: str | None = Field(default=None, description="Уровень: beginner, intermediate, advanced", examples=["beginner"])
    goals: list[str] = Field(default_factory=list, description="Цели из fitness_goal", examples=[["gain_muscle"]])
    equipment: list[str] = Field(default_factory=list, description="Оборудование из equipment", examples=[["gym"]])
    workouts_per_week: int | None = Field(default=None, description="Тренировок в неделю", examples=[3])
    duration_weeks: int | None = Field(default=None, description="Длительность в неделях", examples=[8])
    is_pro: bool = Field(default=False, description="Только для PRO", examples=[False])
    source: str = Field(default="catalog", description="Источник: catalog, trainer, user_copy", examples=["catalog"])
    status: str = Field(default="published", description="Статус: draft, published, archived", examples=["published"])


class ProgramDayIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "title": "Жимы",
                    "description": "Первая тренировка недели",
                    "duration_min": 45,
                    "focus_muscles": ["chest", "shoulders"],
                }
            ]
        }
    )

    title: str = Field(description="Название дня", examples=["Жимы"])
    description: str | None = Field(default=None, description="Описание дня", examples=["Первая тренировка недели"])
    duration_min: int | None = Field(default=None, ge=1, le=300, description="Длительность в минутах", examples=[45])
    focus_muscles: list[str] = Field(default_factory=list, description="Коды мышц из muscle_group", examples=[["chest", "shoulders"]])
    sort_order: int | None = Field(default=None, description="Порядок. Если пусто — в конец списка", examples=[1])


class ProgramDayExerciseIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"exercise_id": 1, "sets": 3, "reps_min": 8, "reps_max": 12, "note": "Контроль техники"}]
        }
    )

    exercise_id: int = Field(description="ID упражнения из каталога", examples=[1], ge=1)
    sets: int | None = Field(default=None, ge=1, le=30, description="Количество подходов", examples=[3])
    reps_min: int | None = Field(default=None, ge=1, le=100, description="Повторения от", examples=[8])
    reps_max: int | None = Field(default=None, ge=1, le=100, description="Повторения до", examples=[12])
    note: str | None = Field(default=None, description="Заметка к упражнению", examples=["Контроль техники"])
    sort_order: int | None = Field(default=None, description="Порядок в дне", examples=[0])


class NoteIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"title": "Питание", "body": "Добавить белок на завтрак"}]})

    title: str = Field(description="Заголовок заметки", examples=["Питание"])
    body: str = Field(default="", description="Текст заметки", examples=["Добавить белок на завтрак"])


class TicketIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"subject": "Не приходит чек", "message": "Оплатил PRO, чек на почту не пришёл."}]}
    )

    subject: str = Field(description="Тема обращения", examples=["Не приходит чек"])
    message: str = Field(description="Текст обращения", examples=["Оплатил PRO, чек на почту не пришёл."])


class CheckoutIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"plan_id": 1}]})

    plan_id: int = Field(description="ID тарифа из GET /plans", examples=[1], ge=1)


class FaqIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "slug": "kak-otmenit-podpisku",
                    "question": "Как отменить подписку?",
                    "answer": "Откройте профиль → подписка → отменить автопродление.",
                    "audience": "all",
                    "sort_order": 10,
                    "is_published": True,
                }
            ]
        }
    )

    slug: str = Field(description="ЧПУ-идентификатор латиницей", examples=["kak-otmenit-podpisku"])
    question: str = Field(description="Вопрос", examples=["Как отменить подписку?"])
    answer: str = Field(description="Ответ", examples=["Откройте профиль → подписка → отменить автопродление."])
    audience: str = Field(default="all", description="Аудитория: all, trainer, client", examples=["all"])
    sort_order: int = Field(default=0, description="Порядок сортировки, меньше — выше", examples=[10])
    is_published: bool = Field(default=True, description="Опубликовать сразу", examples=[True])


class FaqPublishIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"is_published": True}]})

    is_published: bool = Field(description="true — опубликовать, false — скрыть", examples=[True])


class LegalIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"body_md": "# Пользовательское соглашение\n\nТекст документа.", "version": "1.1"}]}
    )

    body_md: str = Field(
        default="",
        description="Текст документа. Если заполнен, ранее загруженный файл снимается.",
        examples=["# Пользовательское соглашение\n\nТекст документа."],
    )
    version: str = Field(default="1.0", description="Версия документа", examples=["1.1"])


class NotificationPrefsIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "push_enabled": True,
                    "email_enabled": True,
                    "workout_reminder": True,
                    "new_client_request": True,
                    "client_report": False,
                }
            ]
        }
    )

    push_enabled: bool | None = Field(default=None, description="Push-уведомления", examples=[True])
    email_enabled: bool | None = Field(default=None, description="Email-уведомления", examples=[True])
    workout_reminder: bool | None = Field(default=None, description="Напоминание о тренировке", examples=[True])
    new_client_request: bool | None = Field(default=None, description="Заявка нового клиента (тренер)", examples=[True])
    client_report: bool | None = Field(default=None, description="Отчёт клиента (тренер)", examples=[False])


class UserBlockIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"is_blocked": True, "reason": "Нарушение правил сообщества"}]}
    )

    is_blocked: bool = Field(description="true — заблокировать, false — разблокировать", examples=[True])
    reason: str | None = Field(default=None, description="Причина блокировки", examples=["Нарушение правил сообщества"])


class TrainerVerifyIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"is_verified": True}]})

    is_verified: bool = Field(description="true — верифицировать тренера, false — снять верификацию", examples=[True])


class ProfilePatchIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "first_name": "Иван",
                    "last_name": "Петров",
                    "gender": "male",
                    "birth_date": "1994-05-12",
                    "height_cm": "180.0",
                }
            ]
        }
    )

    first_name: str | None = Field(default=None, max_length=80, description="Имя", examples=["Иван"])
    last_name: str | None = Field(default=None, max_length=80, description="Фамилия", examples=["Петров"])
    gender: str | None = Field(default=None, description="Пол: male, female, other", examples=["male"])
    birth_date: date | None = Field(default=None, description="Дата рождения", examples=["1994-05-12"])
    height_cm: Decimal | None = Field(default=None, description="Рост, см", examples=["180.0"])


class SessionExerciseIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"exercise_id": 7, "rest_sec": 90}]})

    exercise_id: int = Field(description="ID упражнения", examples=[7], ge=1)
    rest_sec: int | None = Field(default=None, description="Отдых после упражнения, сек", examples=[90])


class TicketStatusIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"status": "in_progress"}]})

    status: str = Field(description="Статус: open, in_progress, answered, closed", examples=["in_progress"])


class WebhookMockIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"event_id": "evt_test_001", "user_id": 3, "plan_id": 1}]}
    )

    event_id: str = Field(description="Идемпотентный ID события провайдера", examples=["evt_test_001"])
    user_id: int = Field(description="ID пользователя, которому начислить подписку", examples=[3], ge=1)
    plan_id: int = Field(description="ID тарифа", examples=[1], ge=1)


class ClientSearchIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"query": "ivan"}]})

    query: str = Field(description="Поиск по имени, email или телефону", examples=["ivan"], min_length=1)


class ClientNoteIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"text": "Клиент пропустил тренировку в пятницу"}]})

    text: str = Field(description="Текст заметки тренера", examples=["Клиент пропустил тренировку в пятницу"])
