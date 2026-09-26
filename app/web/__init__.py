from fastapi import APIRouter
from app.web.home_web import router as home_web_router

web_router = APIRouter()
web_router.include_router(home_web_router)
