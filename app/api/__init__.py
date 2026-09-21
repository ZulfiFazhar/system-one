from fastapi import APIRouter
from app.api.health_route import router as health_router
from app.api.systemone_route import router as systemone_router

router = APIRouter()

router.include_router(health_router, tags=["health"])
router.include_router(systemone_router, prefix="/v1", tags=["systemone"])
