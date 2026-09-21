from fastapi import APIRouter

from app.api.admin import auth, billing, clients, content, dashboard, dictionaries, me, programs, users

router = APIRouter(prefix="/api/v1/admin")
router.include_router(auth.router)
router.include_router(me.router)
router.include_router(dashboard.router)
router.include_router(dictionaries.router)
router.include_router(users.router)
router.include_router(clients.router)
router.include_router(programs.router)
router.include_router(billing.router)
router.include_router(content.router)
