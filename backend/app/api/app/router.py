from fastapi import APIRouter

from app.api.app import (
    auth,
    billing,
    cabinet,
    calendar,
    catalog_api,
    clients,
    content,
    dictionaries,
    me,
    notifications,
    trainer,
)

router = APIRouter(prefix="/api/v1/app")
router.include_router(auth.router)
router.include_router(me.router)
router.include_router(dictionaries.router)
router.include_router(trainer.router)
router.include_router(clients.router)
router.include_router(calendar.router)
router.include_router(catalog_api.router)
router.include_router(cabinet.router)
router.include_router(billing.router)
router.include_router(content.router)
router.include_router(notifications.router)
