from fastapi import APIRouter
from app.api.endpoints import navigation

api_router = APIRouter()
api_router.include_router(navigation.router, prefix="/navigation", tags=["Navigation"])
