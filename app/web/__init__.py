from fastapi import APIRouter
from app.web.admin_web import router as admin_web_router
from app.web.home_web import router as home_web_router

web_router = APIRouter()
web_router.include_router(home_web_router)
web_router.include_router(admin_web_router)
