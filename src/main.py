from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.api.router import api_router
from src.config import settings
from src.exceptions import IntelliSlideError
from src.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    configure_logging(settings.LOG_LEVEL)
    logger.info(
        "IntelliSlide AI API starting",
        extra={"environment": settings.ENVIRONMENT, "log_level": settings.LOG_LEVEL},
    )
    settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    yield
    logger.info("IntelliSlide AI API shutting down")


def create_app() -> FastAPI:
    limiter = Limiter(key_func=get_remote_address)

    app = FastAPI(
        title="IntelliSlide AI API",
        description="Generate PowerPoint presentations from a topic using Google Gemini.",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.exception_handler(IntelliSlideError)
    async def intellislide_error_handler(
        request: Request, exc: IntelliSlideError
    ) -> JSONResponse:
        logger.error(
            "Application error",
            extra={
                "error_code": exc.error_code,
                "detail": exc.detail,
                "path": request.url.path,
                "context": exc.context,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"error_code": exc.error_code, "detail": exc.detail},
        )

    app.include_router(api_router)

    return app


app = create_app()
