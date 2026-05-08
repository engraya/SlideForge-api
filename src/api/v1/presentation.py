import uuid
from pathlib import Path
from typing import Annotated, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import FileResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config import settings
from src.dependencies import get_file_service, get_gemini_provider, get_presentation_service
from src.exceptions import IntelliSlideError, PresentationNotFoundError
from src.schemas.presentation import (
    GenerationStatus,
    PPTRequest,
    PPTResponse,
)
from src.services.ai_service import GeminiProvider
from src.services.file_service import FileService
from src.services.presentation_service import PresentationService
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/presentations", tags=["presentations"])
limiter = Limiter(key_func=get_remote_address)

# In-memory job store: {str(job_id): PPTResponse}
# Single-worker safe. Replace values with Redis for horizontal scaling.
_job_store: dict[str, PPTResponse] = {}


@router.post(
    "",
    response_model=PPTResponse,
    status_code=202,
    summary="Generate a new presentation",
)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def create_presentation(
    request: Request,
    body: PPTRequest,
    background_tasks: BackgroundTasks,
    ai_provider: Annotated[GeminiProvider, Depends(get_gemini_provider)],
    file_service: Annotated[FileService, Depends(get_file_service)],
    pptx_service: Annotated[PresentationService, Depends(get_presentation_service)],
) -> PPTResponse:
    """
    Accepts a generation request and returns a job_id immediately (202 Accepted).
    Poll GET /presentations/{job_id}/status until status is 'ready', then
    GET /presentations/{job_id}/download to retrieve the file.
    """
    job_id = uuid.uuid4()
    output_path, filename = file_service.get_output_path(body.topic)

    response = PPTResponse(
        job_id=job_id,
        status=GenerationStatus.PENDING,
        message="Presentation generation queued.",
        filename=filename,
    )
    _job_store[str(job_id)] = response

    logger.info(
        "Presentation job created",
        extra={
            "job_id": str(job_id),
            "topic": body.topic,
            "num_slides": body.num_slides,
            "language": body.language,
        },
    )

    background_tasks.add_task(
        _generate_presentation_task,
        job_id=str(job_id),
        body=body,
        output_path=output_path,
        filename=filename,
        ai_provider=ai_provider,
        pptx_service=pptx_service,
    )

    return response


@router.get(
    "/{job_id}/status",
    response_model=PPTResponse,
    summary="Poll generation status",
)
async def get_status(job_id: uuid.UUID) -> PPTResponse:
    """Returns the current status of a generation job: pending → processing → ready | failed."""
    stored = _job_store.get(str(job_id))
    if not stored:
        raise PresentationNotFoundError(
            detail=f"Job {job_id} not found.",
            context={"job_id": str(job_id)},
        )
    return stored


@router.get(
    "/{job_id}/download",
    summary="Download a completed presentation",
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.presentationml.presentation": {}
            }
        },
        404: {"description": "Job not found or not yet ready"},
    },
)
async def download_presentation(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    file_service: Annotated[FileService, Depends(get_file_service)],
) -> FileResponse:
    """
    Secure download endpoint. The URL contains only a UUID — the filename is
    looked up from _job_store (server-generated). The client never controls
    which file path gets served. resolve_download_path() is a second layer of
    defense even though the filename is already trusted.
    """
    stored = _job_store.get(str(job_id))
    if not stored:
        raise PresentationNotFoundError(
            detail=f"Job {job_id} not found.",
            context={"job_id": str(job_id)},
        )

    if stored.status != GenerationStatus.READY:
        raise PresentationNotFoundError(
            detail=f"Presentation not ready. Current status: {stored.status}",
            context={"job_id": str(job_id), "status": stored.status},
        )

    assert stored.filename is not None
    file_path = file_service.resolve_download_path(stored.filename)

    background_tasks.add_task(file_service.cleanup_expired_files)

    logger.info(
        "Presentation downloaded",
        extra={"job_id": str(job_id), "filename": stored.filename},
    )

    return FileResponse(
        path=str(file_path),
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".presentationml.presentation"
        ),
        filename=stored.filename,
    )


async def _generate_presentation_task(
    job_id: str,
    body: PPTRequest,
    output_path: Path,
    filename: str,
    ai_provider: GeminiProvider,
    pptx_service: PresentationService,
) -> None:
    """
    Background task: calls Gemini, builds PPTX, updates job store.
    All exceptions are caught here — background tasks cannot propagate to the client.
    """
    _job_store[job_id] = _job_store[job_id].model_copy(
        update={"status": GenerationStatus.PROCESSING, "message": "Generating slide content..."}
    )

    try:
        logger.info("Background task started", extra={"job_id": job_id})

        slides = ai_provider.generate_slides(
            topic=body.topic,
            num_slides=body.num_slides,
            language=body.language.value,
        )

        _job_store[job_id] = _job_store[job_id].model_copy(
            update={"message": "Building PowerPoint file..."}
        )

        pptx_service.build(
            slides=slides,
            output_path=output_path,
            theme=body.theme,
        )

        _job_store[job_id] = _job_store[job_id].model_copy(
            update={
                "status": GenerationStatus.READY,
                "message": "Presentation ready for download.",
                "download_url": f"/api/v1/presentations/{job_id}/download",
            }
        )
        logger.info(
            "Background task completed",
            extra={"job_id": job_id, "filename": filename},
        )

    except IntelliSlideError as exc:
        logger.error(
            "Presentation generation failed",
            extra={
                "job_id": job_id,
                "error_code": exc.error_code,
                "detail": exc.detail,
                "context": exc.context,
            },
        )
        _job_store[job_id] = _job_store[job_id].model_copy(
            update={
                "status": GenerationStatus.FAILED,
                "message": f"Generation failed: {exc.detail}",
            }
        )
    except Exception as exc:
        logger.error(
            "Unexpected error in background task",
            extra={"job_id": job_id, "error": str(exc)},
        )
        _job_store[job_id] = _job_store[job_id].model_copy(
            update={
                "status": GenerationStatus.FAILED,
                "message": "An unexpected error occurred.",
            }
        )
