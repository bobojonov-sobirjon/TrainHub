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
from app.core.tags import TAG_DESCRIPTIONS, TAG_ORDER
from app.db.pool import close_pool, create_pool
from app.deps.redis import close_redis
from app.services.storage import ensure_media_dir, media_root


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    ensure_media_dir()
    from app.services.firebase import init_firebase

    init_firebase()
    await create_pool()
    from app.services.telegram_auth import start_telegram_listener

    telegram_task = await start_telegram_listener()
    yield
    if telegram_task:
        telegram_task.cancel()
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
            "Две роли приложения: **Coach** (тренер) и **Client** (клиент). "
            "Теги Swagger сгруппированы: `Coach - …`, `Client - …`, `Shared - …`, `Admin - …`. "
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
