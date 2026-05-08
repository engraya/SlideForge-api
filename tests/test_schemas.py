import pytest
from pydantic import ValidationError

from src.schemas.presentation import (
    LanguageCode,
    PPTRequest,
    PresentationTheme,
    SlideContent,
)


class TestPPTRequest:
    def test_valid_request(self):
        req = PPTRequest(topic="Climate Change", num_slides=5, language=LanguageCode.ENGLISH)
        assert req.topic == "Climate Change"
        assert req.num_slides == 5

    def test_topic_too_short(self):
        with pytest.raises(ValidationError) as exc_info:
            PPTRequest(topic="AI")
        assert "topic" in str(exc_info.value)

    def test_topic_too_long(self):
        with pytest.raises(ValidationError):
            PPTRequest(topic="x" * 301)

    def test_topic_whitespace_only(self):
        with pytest.raises(ValidationError):
            PPTRequest(topic="   ")

    def test_topic_stripped(self):
        req = PPTRequest(topic="  Climate Change  ")
        assert req.topic == "Climate Change"

    def test_num_slides_exceeds_max(self):
        with pytest.raises(ValidationError):
            PPTRequest(topic="Valid Topic", num_slides=21)

    def test_num_slides_below_min(self):
        with pytest.raises(ValidationError):
            PPTRequest(topic="Valid Topic", num_slides=0)

    def test_num_slides_boundary_values(self):
        req_min = PPTRequest(topic="Valid Topic", num_slides=1)
        req_max = PPTRequest(topic="Valid Topic", num_slides=20)
        assert req_min.num_slides == 1
        assert req_max.num_slides == 20

    def test_invalid_language(self):
        with pytest.raises(ValidationError):
            PPTRequest(topic="Valid Topic", language="Klingon")

    def test_invalid_theme(self):
        with pytest.raises(ValidationError):
            PPTRequest(topic="Valid Topic", theme="neon")

    def test_default_values(self):
        req = PPTRequest(topic="Valid Topic")
        assert req.num_slides == 5
        assert req.language == LanguageCode.ENGLISH
        assert req.theme == PresentationTheme.PROFESSIONAL


class TestSlideContent:
    def test_valid_slide(self):
        slide = SlideContent(title="Intro", bullets=["Point A", "Point B"])
        assert slide.title == "Intro"
        assert len(slide.bullets) == 2

    def test_empty_bullets_filtered_out(self):
        slide = SlideContent(title="Intro", bullets=["  ", "Point A", ""])
        assert slide.bullets == ["Point A"]

    def test_all_empty_bullets_raises(self):
        with pytest.raises(ValidationError):
            SlideContent(title="Intro", bullets=["  ", ""])

    def test_no_bullets_raises(self):
        with pytest.raises(ValidationError):
            SlideContent(title="Intro", bullets=[])

    def test_image_placeholder_optional(self):
        slide = SlideContent(title="Intro", bullets=["Point A"])
        assert slide.image_placeholder is None

        slide_with_img = SlideContent(
            title="Intro", bullets=["Point A"], image_placeholder="A bar chart"
        )
        assert slide_with_img.image_placeholder == "A bar chart"
