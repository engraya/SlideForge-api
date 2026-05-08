from fastapi import APIRouter

from src.config import settings
from src.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
async def health() -> HealthResponse:
    return HealthResponse(status="ok", environment=settings.ENVIRONMENT)


@router.get("/ready", response_model=HealthResponse, summary="Readiness check")
async def ready() -> HealthResponse:
    return HealthResponse(status="ready", environment=settings.ENVIRONMENT)
