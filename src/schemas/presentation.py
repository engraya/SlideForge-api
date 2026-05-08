from __future__ import annotations

import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LanguageCode(str, Enum):
    ENGLISH = "English"
    ARABIC = "Arabic"
    FRENCH = "French"
    SPANISH = "Spanish"
    GERMAN = "German"
    PORTUGUESE = "Portuguese"
    CHINESE = "Chinese"
    JAPANESE = "Japanese"
    HINDI = "Hindi"


class PresentationTheme(str, Enum):
    PROFESSIONAL = "professional"
    MINIMAL = "minimal"
    VIBRANT = "vibrant"


class GenerationStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class PPTRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=3,
        max_length=300,
        description="The subject matter for the presentation.",
        examples=["The Future of Renewable Energy"],
    )
    num_slides: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Number of slides to generate (1-20).",
    )
    language: LanguageCode = Field(
        default=LanguageCode.ENGLISH,
        description="Language for slide content.",
    )
    theme: PresentationTheme = Field(
        default=PresentationTheme.PROFESSIONAL,
        description="Visual theme for the presentation.",
    )

    @field_validator("topic")
    @classmethod
    def topic_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("topic cannot be whitespace only.")
        return stripped


class SlideContent(BaseModel):
    """
    Shared contract between ai_service and presentation_service.
    Fixes the runtime crash where create_pptx() expected slide_info["title"]
    (dict) but generate_slide_content() returned list[list[str]].
    """
    title: str = Field(..., min_length=1, max_length=100)
    bullets: list[str] = Field(..., min_length=1)
    image_placeholder: Optional[str] = Field(default=None)

    @field_validator("bullets")
    @classmethod
    def filter_empty_bullets(cls, v: list[str]) -> list[str]:
        filtered = [b.strip() for b in v if b.strip()]
        if not filtered:
            raise ValueError("bullets must contain at least one non-empty item.")
        return filtered


class PPTResponse(BaseModel):
    job_id: uuid.UUID
    status: GenerationStatus
    message: str
    filename: Optional[str] = None
    download_url: Optional[str] = None
