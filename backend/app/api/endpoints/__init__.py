from fastapi import APIRouter
from . import dashboard, gee, users

api_router = APIRouter()
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(gee.router, prefix="/gee", tags=["earth-engine"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
