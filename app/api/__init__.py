from fastapi import APIRouter
from app.api.admin_route import router as admin_router, admin_ui_router
from app.api.health_route import router as health_router
from app.api.home_route import router as home_router
from app.api.systemone_route import router as systemone_router

router = APIRouter()

router.include_router(home_router, tags=["home"])
router.include_router(health_router, tags=["health"])
router.include_router(systemone_router, prefix="/v1", tags=["systemone"])
router.include_router(admin_router, prefix="/api/admin", tags=["admin"])
router.include_router(admin_ui_router, tags=["admin-ui"])

