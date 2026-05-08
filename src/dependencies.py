from functools import lru_cache

from src.services.ai_service import GeminiProvider
from src.services.file_service import FileService
from src.services.presentation_service import PresentationService


@lru_cache(maxsize=1)
def get_gemini_provider() -> GeminiProvider:
    return GeminiProvider()


@lru_cache(maxsize=1)
def get_file_service() -> FileService:
    return FileService()


@lru_cache(maxsize=1)
def get_presentation_service() -> PresentationService:
    return PresentationService()
