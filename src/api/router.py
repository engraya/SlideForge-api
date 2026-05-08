from fastapi import APIRouter

from src.api.v1 import health, presentation

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(presentation.router)
