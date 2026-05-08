import uuid
from unittest.mock import patch

import pytest

from src.schemas.presentation import GenerationStatus, SlideContent

MOCK_SLIDES = [
    SlideContent(title="Intro", bullets=["Bullet 1", "Bullet 2"]),
    SlideContent(title="Details", bullets=["Bullet A", "Bullet B"]),
]


class TestHealthEndpoints:
    def test_health_returns_200(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "environment" in data

    def test_ready_returns_200(self, client):
        response = client.get("/api/v1/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"


class TestCreatePresentation:
    def test_returns_202_with_job_id(self, client):
        with patch("src.api.v1.presentation._generate_presentation_task"):
            response = client.post(
                "/api/v1/presentations",
                json={"topic": "Machine Learning", "num_slides": 3},
            )
        assert response.status_code == 202
        body = response.json()
        assert "job_id" in body
        assert body["status"] == GenerationStatus.PENDING
        assert body["message"] == "Presentation generation queued."

    def test_rejects_short_topic(self, client):
        response = client.post(
            "/api/v1/presentations",
            json={"topic": "AI"},
        )
        assert response.status_code == 422

    def test_rejects_whitespace_topic(self, client):
        response = client.post(
            "/api/v1/presentations",
            json={"topic": "   "},
        )
        assert response.status_code == 422

    def test_rejects_too_many_slides(self, client):
        response = client.post(
            "/api/v1/presentations",
            json={"topic": "Valid Topic", "num_slides": 25},
        )
        assert response.status_code == 422

    def test_rejects_zero_slides(self, client):
        response = client.post(
            "/api/v1/presentations",
            json={"topic": "Valid Topic", "num_slides": 0},
        )
        assert response.status_code == 422

    def test_rejects_invalid_language(self, client):
        response = client.post(
            "/api/v1/presentations",
            json={"topic": "Valid Topic", "language": "Klingon"},
        )
        assert response.status_code == 422

    def test_rejects_invalid_theme(self, client):
        response = client.post(
            "/api/v1/presentations",
            json={"topic": "Valid Topic", "theme": "dark_mode"},
        )
        assert response.status_code == 422

    def test_accepts_all_valid_themes(self, client):
        for theme in ["professional", "minimal", "vibrant"]:
            with patch("src.api.v1.presentation._generate_presentation_task"):
                response = client.post(
                    "/api/v1/presentations",
                    json={"topic": "Valid Topic", "theme": theme},
                )
            assert response.status_code == 202, f"Theme {theme} should be accepted"


class TestStatusEndpoint:
    def test_returns_404_for_unknown_job(self, client):
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/presentations/{fake_id}/status")
        assert response.status_code == 404

    def test_returns_pending_after_creation(self, client):
        with patch("src.api.v1.presentation._generate_presentation_task"):
            create_response = client.post(
                "/api/v1/presentations",
                json={"topic": "Machine Learning", "num_slides": 3},
            )
        job_id = create_response.json()["job_id"]
        status_response = client.get(f"/api/v1/presentations/{job_id}/status")
        assert status_response.status_code == 200
        assert status_response.json()["status"] == GenerationStatus.PENDING

    def test_returns_400_for_malformed_uuid(self, client):
        response = client.get("/api/v1/presentations/not-a-uuid/status")
        assert response.status_code == 422


class TestDownloadEndpoint:
    def test_returns_404_for_unknown_job(self, client):
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/presentations/{fake_id}/download")
        assert response.status_code == 404

    def test_returns_404_when_job_not_ready(self, client):
        with patch("src.api.v1.presentation._generate_presentation_task"):
            create_response = client.post(
                "/api/v1/presentations",
                json={"topic": "Machine Learning", "num_slides": 3},
            )
        job_id = create_response.json()["job_id"]
        response = client.get(f"/api/v1/presentations/{job_id}/download")
        assert response.status_code == 404
        assert "not ready" in response.json()["detail"]


class TestErrorResponses:
    def test_error_response_has_error_code_field(self, client):
        fake_id = str(uuid.uuid4())
        response = client.get(f"/api/v1/presentations/{fake_id}/status")
        body = response.json()
        assert "error_code" in body
        assert "detail" in body
        assert body["error_code"] == "PRESENTATION_NOT_FOUND"
