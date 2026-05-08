from __future__ import annotations

import json
import logging
import time
from typing import Protocol, runtime_checkable

import google.generativeai as genai

from src.config import settings
from src.exceptions import AIParsingError, AIServiceError
from src.schemas.presentation import SlideContent
from src.utils.logging import get_logger

logger = get_logger(__name__)

genai.configure(api_key=settings.GOOGLE_API_KEY)


@runtime_checkable
class AIProvider(Protocol):
    def generate_slides(
        self,
        topic: str,
        num_slides: int,
        language: str,
    ) -> list[SlideContent]: ...


class GeminiProvider:
    """
    Calls Google Gemini in JSON mode to produce validated SlideContent objects.
    Fixes:
    - Fragile \\n\\n parsing → structured JSON output via response_mime_type
    - No error handling → try/except + typed exceptions at every failure point
    - Wrong return type (list[list[str]]) → returns list[SlideContent]
    - No retry → exponential backoff over 3 attempts
    """

    MODEL_NAME = "gemini-3-flash-preview"
    MAX_RETRIES = 3
    BASE_BACKOFF_SECONDS = 1.0

    def __init__(self) -> None:
        self._model = genai.GenerativeModel(
            model_name=self.MODEL_NAME,
            generation_config=genai.GenerationConfig(
                response_mime_type="application/json",
                temperature=0.7,
                max_output_tokens=8192,
            ),
        )

    def _build_prompt(self, topic: str, num_slides: int, language: str) -> str:
        return f"""You are a professional presentation designer.
Generate exactly {num_slides} slides in {language} about: {topic}

Return a JSON object matching this exact schema — no markdown, no extra text:
{{
  "slides": [
    {{
      "title": "Slide title (max 80 characters)",
      "bullets": ["bullet 1", "bullet 2", "bullet 3"],
      "image_placeholder": "Optional: short description of a relevant image, or null"
    }}
  ]
}}

Rules:
- The "slides" array must have exactly {num_slides} items.
- Each "title" must be a non-empty string under 80 characters.
- Each "bullets" array must have between 2 and 6 items.
- Each bullet is a concise sentence (max 120 characters).
- image_placeholder is optional; omit or set to null if not relevant.
- Respond ONLY with valid JSON. No explanation, no markdown code fences.
"""

    def _parse_response(self, raw_text: str, expected_count: int) -> list[SlideContent]:
        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise AIParsingError(
                detail=f"Gemini returned non-JSON response: {exc}",
                context={"raw_response_preview": raw_text[:200]},
            ) from exc

        if "slides" not in data or not isinstance(data["slides"], list):
            raise AIParsingError(
                detail="Gemini response missing 'slides' array.",
                context={"keys_found": list(data.keys())},
            )

        slides: list[SlideContent] = []
        for idx, raw_slide in enumerate(data["slides"]):
            try:
                slide = SlideContent.model_validate(raw_slide)
                slides.append(slide)
            except Exception as exc:
                raise AIParsingError(
                    detail=f"Slide {idx} failed validation: {exc}",
                    context={"slide_data": raw_slide},
                ) from exc

        if not slides:
            raise AIParsingError(
                detail="Gemini returned zero slides.",
                context={"expected": expected_count},
            )

        if len(slides) != expected_count:
            logger.warning(
                "Gemini returned unexpected slide count",
                extra={"expected": expected_count, "received": len(slides)},
            )

        return slides

    def generate_slides(
        self,
        topic: str,
        num_slides: int,
        language: str,
    ) -> list[SlideContent]:
        prompt = self._build_prompt(topic, num_slides, language)
        last_exc: Exception | None = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                logger.info(
                    "Calling Gemini API",
                    extra={"attempt": attempt, "topic": topic, "num_slides": num_slides},
                )
                response = self._model.generate_content(prompt)

                if not response or not hasattr(response, "text") or not response.text:
                    raise AIServiceError(
                        detail="Gemini returned empty response.",
                        context={"attempt": attempt},
                    )

                slides = self._parse_response(response.text, num_slides)
                logger.info(
                    "Gemini call succeeded",
                    extra={"attempt": attempt, "slides_returned": len(slides)},
                )
                return slides

            except (AIServiceError, AIParsingError):
                raise  # Don't retry typed parsing failures
            except Exception as exc:
                last_exc = exc
                backoff = self.BASE_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    "Gemini API call failed, retrying",
                    extra={
                        "attempt": attempt,
                        "max_retries": self.MAX_RETRIES,
                        "backoff_seconds": backoff,
                        "error": str(exc),
                    },
                )
                if attempt < self.MAX_RETRIES:
                    time.sleep(backoff)

        raise AIServiceError(
            detail=f"Gemini API failed after {self.MAX_RETRIES} attempts.",
            context={"last_error": str(last_exc)},
        ) from last_exc
