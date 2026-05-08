from __future__ import annotations

from typing import Any


class SlideForgeError(Exception):
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, detail: str, context: dict[str, Any] | None = None) -> None:
        self.detail = detail
        self.context = context or {}
        super().__init__(detail)


class AIServiceError(SlideForgeError):
    status_code = 502
    error_code = "AI_SERVICE_ERROR"


class AIParsingError(AIServiceError):
    status_code = 502
    error_code = "AI_PARSING_ERROR"


class PresentationGenerationError(SlideForgeError):
    status_code = 500
    error_code = "PRESENTATION_GENERATION_ERROR"


class PresentationNotFoundError(SlideForgeError):
    status_code = 404
    error_code = "PRESENTATION_NOT_FOUND"


class RateLimitError(SlideForgeError):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"


class InputValidationError(SlideForgeError):
    status_code = 422
    error_code = "INPUT_VALIDATION_ERROR"
