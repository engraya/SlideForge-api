import json
from unittest.mock import MagicMock, patch

import pytest

from src.exceptions import AIParsingError, AIServiceError
from src.schemas.presentation import SlideContent
from src.services.ai_service import GeminiProvider

VALID_GEMINI_RESPONSE = json.dumps({
    "slides": [
        {
            "title": "Introduction",
            "bullets": ["Point A", "Point B"],
            "image_placeholder": None,
        },
        {
            "title": "Main Topic",
            "bullets": ["Detail 1", "Detail 2", "Detail 3"],
            "image_placeholder": "A bar chart",
        },
    ]
})


class TestGeminiProvider:
    @patch("src.services.ai_service.genai.GenerativeModel")
    def test_generate_slides_success(self, mock_model_class):
        mock_response = MagicMock()
        mock_response.text = VALID_GEMINI_RESPONSE
        mock_model_class.return_value.generate_content.return_value = mock_response

        provider = GeminiProvider()
        slides = provider.generate_slides("AI", 2, "English")

        assert len(slides) == 2
        assert isinstance(slides[0], SlideContent)
        assert slides[0].title == "Introduction"
        assert slides[1].bullets == ["Detail 1", "Detail 2", "Detail 3"]

    @patch("src.services.ai_service.genai.GenerativeModel")
    def test_raises_ai_parsing_error_on_invalid_json(self, mock_model_class):
        mock_response = MagicMock()
        mock_response.text = "Not valid JSON at all"
        mock_model_class.return_value.generate_content.return_value = mock_response

        provider = GeminiProvider()
        with pytest.raises(AIParsingError) as exc_info:
            provider.generate_slides("AI", 2, "English")
        assert exc_info.value.error_code == "AI_PARSING_ERROR"

    @patch("src.services.ai_service.genai.GenerativeModel")
    def test_raises_parsing_error_when_slides_key_missing(self, mock_model_class):
        mock_response = MagicMock()
        mock_response.text = json.dumps({"data": []})
        mock_model_class.return_value.generate_content.return_value = mock_response

        provider = GeminiProvider()
        with pytest.raises(AIParsingError):
            provider.generate_slides("AI", 2, "English")

    @patch("src.services.ai_service.genai.GenerativeModel")
    def test_retries_on_network_error_then_succeeds(self, mock_model_class):
        mock_response = MagicMock()
        mock_response.text = VALID_GEMINI_RESPONSE

        mock_model_class.return_value.generate_content.side_effect = [
            ConnectionError("Network error"),
            ConnectionError("Network error"),
            mock_response,
        ]

        provider = GeminiProvider()
        with patch("src.services.ai_service.time.sleep"):
            slides = provider.generate_slides("AI", 2, "English")

        assert len(slides) == 2
        assert mock_model_class.return_value.generate_content.call_count == 3

    @patch("src.services.ai_service.genai.GenerativeModel")
    def test_raises_after_all_retries_exhausted(self, mock_model_class):
        mock_model_class.return_value.generate_content.side_effect = ConnectionError("Down")

        provider = GeminiProvider()
        with patch("src.services.ai_service.time.sleep"):
            with pytest.raises(AIServiceError) as exc_info:
                provider.generate_slides("AI", 2, "English")

        assert "3 attempts" in exc_info.value.detail
        assert exc_info.value.error_code == "AI_SERVICE_ERROR"

    @patch("src.services.ai_service.genai.GenerativeModel")
    def test_parsing_error_not_retried(self, mock_model_class):
        mock_response = MagicMock()
        mock_response.text = "bad json"
        mock_model_class.return_value.generate_content.return_value = mock_response

        provider = GeminiProvider()
        with pytest.raises(AIParsingError):
            provider.generate_slides("AI", 2, "English")

        # Must be called exactly once — parsing errors are not retried
        assert mock_model_class.return_value.generate_content.call_count == 1

    @patch("src.services.ai_service.genai.GenerativeModel")
    def test_empty_response_raises_service_error(self, mock_model_class):
        mock_response = MagicMock()
        mock_response.text = ""
        mock_model_class.return_value.generate_content.return_value = mock_response

        provider = GeminiProvider()
        with patch("src.services.ai_service.time.sleep"):
            with pytest.raises(AIServiceError):
                provider.generate_slides("AI", 2, "English")
