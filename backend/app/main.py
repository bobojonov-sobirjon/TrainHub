from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles

from app.api.admin.router import router as admin_router
from app.api.app.router import router as app_router
from app.api.health import router as health_router
from app.core.config import settings
from app.core.exceptions import (
    AppError,
    app_error_handler,
    validation_error_handler,
)
from app.core.logging import setup_logging
from app.db.pool import close_pool, create_pool
from app.deps.redis import close_redis
from app.services.storage import ensure_media_dir, media_root

TAG_ORDER = [
    "Health",
    "App - Auth",
    "App - Profile",
    "App - Dictionaries",
    "App - Trainer",
    "App - Trainers",
    "App - Clients",
    "App - Calendar",
    "App - Exercises",
    "App - Programs",
    "App - Sessions",
    "App - Client",
    "App - Billing",
    "App - FAQ",
    "App - Legal",
    "App - Support",
    "App - Notifications",
    "Admin - Auth",
    "Admin - Profile",
    "Admin - Dashboard",
    "Admin - Dictionaries",
    "Admin - Users",
    "Admin - Clients",
    "Admin - Programs",
    "Admin - Exercises",
    "Admin - Billing",
    "Admin - FAQ",
    "Admin - Legal",
    "Admin - Tickets",
]

TAG_DESCRIPTIONS = {
    "Health": "Проверка доступности API и подключения к PostgreSQL.",
    "App - Auth": "Регистрация, вход, обновление и отзыв JWT приложения (клиент/тренер).",
    "App - Profile": "Текущий пользователь приложения.",
    "App - Dictionaries": "Справочники: уровень, цели, мышцы, оборудование, форматы.",
    "App - Trainer": "Кабинет тренера: профиль, дашборд, отчёты, внимание.",
    "App - Trainers": "Публичный каталог тренеров для клиентов.",
    "App - Clients": "Клиенты тренера: поиск, добавление, замеры, заметки.",
    "App - Calendar": "Календарь тренировок тренера: создание, отмена, старт сессии.",
    "App - Exercises": "Каталог упражнений: публичные и пользовательские.",
    "App - Programs": "Готовые и собственные программы, сохранение и копирование.",
    "App - Sessions": "Живые тренировки: старт, подходы, завершение.",
    "App - Client": "Кабинет клиента: дом, замеры, фотопрогресс, заметки, история.",
    "App - Billing": "Тарифы, подписка, оплата и mock-webhook.",
    "App - FAQ": "Публичные статьи FAQ.",
    "App - Legal": "Пользовательское соглашение и политика конфиденциальности.",
    "App - Support": "Обращения в поддержку от пользователя.",
    "App - Notifications": "Уведомления и настройки рассылок.",
    "Admin - Auth": "Вход администратора, refresh и выход. Только роль admin.",
    "Admin - Profile": "Текущий администратор.",
    "Admin - Dashboard": "Сводка по пользователям, сессиям и подпискам.",
    "Admin - Dictionaries": "Справочники для админ-панели (те же коды, что в приложении).",
    "Admin - Users": "Пользователи: список, карточка, блокировка, верификация тренера.",
    "Admin - Clients": "Связи тренер–клиент.",
    "Admin - Programs": "Каталог программ: создание, правка, архив, дни и упражнения дня.",
    "Admin - Exercises": "Каталог упражнений: создание, правка, удаление.",
    "Admin - Billing": "Тарифы, платежи и подписки.",
    "Admin - FAQ": "Управление статьями FAQ.",
    "Admin - Legal": "Редактор юридических документов: текст или файл PDF/DOC/DOCX.",
    "Admin - Tickets": "Обращения поддержки и смена статуса.",
}


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    ensure_media_dir()
    await create_pool()
    yield
    await close_redis()
    await close_pool()


def _promote_examples(schema: dict) -> None:
    for spec in schema.get("components", {}).get("schemas", {}).values():
        examples = spec.get("examples")
        if isinstance(examples, list) and examples and "example" not in spec:
            spec["example"] = examples[0]
        for prop in spec.get("properties", {}).values():
            if isinstance(prop.get("examples"), list) and prop["examples"] and "example" not in prop:
                prop["example"] = prop["examples"][0]
    for path_item in schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue
            content = operation.get("requestBody", {}).get("content", {})
            json_body = content.get("application/json")
            if not json_body:
                continue
            ref = (json_body.get("schema") or {}).get("$ref", "")
            name = ref.rsplit("/", 1)[-1]
            model = schema.get("components", {}).get("schemas", {}).get(name, {})
            example = model.get("example")
            if example is None and isinstance(model.get("examples"), list) and model["examples"]:
                example = model["examples"][0]
            if example is not None:
                json_body["example"] = example


def custom_openapi(app: FastAPI) -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title="TrainHub API",
        version="1.0.0",
        description=(
            "API мобильного приложения (`/api/v1/app`) и админ-панели (`/api/v1/admin`). "
            "Авторизация: Bearer JWT. App-токены и admin-токены разделены (`aud=app` / `aud=admin`). "
            "Для POST, PUT и PATCH в схемах указаны описания полей и примеры тела запроса. "
            "DELETE и часть POST не принимают тело — все параметры в пути."
        ),
        routes=app.routes,
    )
    schema["tags"] = [{"name": name, "description": TAG_DESCRIPTIONS.get(name, "")} for name in TAG_ORDER]
    _promote_examples(schema)
    app.openapi_schema = schema
    return app.openapi_schema


def create_app() -> FastAPI:
    app = FastAPI(
        title="TrainHub API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    app.include_router(health_router)
    app.include_router(app_router)
    app.include_router(admin_router)
    ensure_media_dir()
    app.mount("/media", StaticFiles(directory=str(media_root())), name="media")
    app.openapi = lambda: custom_openapi(app)
    return app


app = create_app()
