from __future__ import annotations

import time
from pathlib import Path

from src.config import settings
from src.exceptions import PresentationNotFoundError
from src.utils.logging import get_logger
from src.utils.security import generate_safe_filename, get_safe_file_path

logger = get_logger(__name__)


class FileService:
    """
    Manages the lifecycle of generated PPTX files.
    All file I/O goes through this service — no other module touches the filesystem.
    """

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = (output_dir or settings.OUTPUT_DIR).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def get_output_path(self, topic: str) -> tuple[Path, str]:
        """Returns (absolute_path, filename) with a UUID-safe filename."""
        filename = generate_safe_filename(topic)
        return self.output_dir / filename, filename

    def resolve_download_path(self, filename: str) -> Path:
        """
        Validates a server-supplied filename and returns the absolute path.
        Raises PresentationNotFoundError for missing files and for path traversal
        attempts (surfaces both as 404 so attackers learn nothing about structure).
        """
        try:
            path = get_safe_file_path(filename, self.output_dir)
        except ValueError as exc:
            logger.warning(
                "Path traversal attempt detected",
                extra={"pptx_file": filename, "error": str(exc)},
            )
            raise PresentationNotFoundError(
                detail="Presentation not found.",
                context={"filename": filename},
            ) from exc

        if not path.exists():
            raise PresentationNotFoundError(
                detail="Presentation not found or has expired.",
                context={"filename": filename},
            )

        return path

    def cleanup_expired_files(self) -> int:
        """Deletes .pptx files older than FILE_TTL_SECONDS. Returns count deleted."""
        now = time.time()
        deleted = 0

        for pptx_file in self.output_dir.glob("*.pptx"):
            try:
                age = now - pptx_file.stat().st_mtime
                if age > settings.FILE_TTL_SECONDS:
                    pptx_file.unlink()
                    deleted += 1
                    logger.info(
                        "Deleted expired file",
                        extra={"pptx_file": pptx_file.name, "age_seconds": int(age)},
                    )
            except OSError as exc:
                logger.error(
                    "Failed to delete expired file",
                    extra={"pptx_file": pptx_file.name, "error": str(exc)},
                )

        return deleted
