import os
import time

import pytest

from src.exceptions import PresentationNotFoundError
from src.services.file_service import FileService
from src.utils.security import (
    generate_safe_filename,
    get_safe_file_path,
    sanitize_topic_for_filename,
)


class TestSanitizeTopicForFilename:
    def test_basic_topic(self):
        assert sanitize_topic_for_filename("Climate Change") == "Climate_Change"

    def test_special_characters_stripped(self):
        result = sanitize_topic_for_filename("Q3 Revenue & Forecast (2024)!")
        assert "&" not in result
        assert "(" not in result
        assert "!" not in result

    def test_unicode_normalized(self):
        result = sanitize_topic_for_filename("Café au Lait")
        assert "é" not in result

    def test_empty_topic_returns_fallback(self):
        assert sanitize_topic_for_filename("!!!") == "presentation"

    def test_truncation(self):
        long_topic = "A" * 100
        assert len(sanitize_topic_for_filename(long_topic)) <= 50

    def test_whitespace_collapsed(self):
        result = sanitize_topic_for_filename("  multiple   spaces  ")
        assert "  " not in result


class TestGenerateSafeFilename:
    def test_ends_with_pptx(self):
        assert generate_safe_filename("Test Topic").endswith(".pptx")

    def test_no_spaces(self):
        assert " " not in generate_safe_filename("Topic With Spaces")

    def test_unique_on_repeated_calls(self):
        names = {generate_safe_filename("Same Topic") for _ in range(50)}
        assert len(names) == 50


class TestGetSafeFilePath:
    def test_valid_filename(self, tmp_path):
        (tmp_path / "valid_file.pptx").touch()
        result = get_safe_file_path("valid_file.pptx", tmp_path)
        assert result == (tmp_path / "valid_file.pptx").resolve()

    def test_path_traversal_double_dot_stripped(self, tmp_path):
        # Path.name strips directory components — ../../../etc/passwd becomes 'passwd'
        result = get_safe_file_path("../../../etc/passwd", tmp_path)
        assert result.parent == tmp_path.resolve()
        assert result.name == "passwd"

    def test_absolute_path_injection_stripped(self, tmp_path):
        result = get_safe_file_path("/etc/passwd", tmp_path)
        assert result.parent == tmp_path.resolve()
        assert result.name == "passwd"


class TestFileService:
    def test_get_output_path_returns_unique_paths(self, tmp_path):
        svc = FileService(output_dir=tmp_path)
        _, name1 = svc.get_output_path("Test Topic")
        _, name2 = svc.get_output_path("Test Topic")
        assert name1 != name2

    def test_get_output_path_creates_output_dir(self, tmp_path):
        new_dir = tmp_path / "subdir"
        svc = FileService(output_dir=new_dir)
        assert new_dir.exists()

    def test_resolve_download_path_missing_file_raises(self, tmp_path):
        svc = FileService(output_dir=tmp_path)
        with pytest.raises(PresentationNotFoundError):
            svc.resolve_download_path("nonexistent.pptx")

    def test_resolve_download_path_existing_file(self, tmp_path):
        svc = FileService(output_dir=tmp_path)
        test_file = tmp_path / "valid.pptx"
        test_file.touch()
        result = svc.resolve_download_path("valid.pptx")
        assert result == test_file.resolve()

    def test_cleanup_deletes_old_files(self, tmp_path, monkeypatch):
        svc = FileService(output_dir=tmp_path)
        old_file = tmp_path / "old_presentation.pptx"
        old_file.touch()

        old_time = time.time() - 7200
        os.utime(str(old_file), (old_time, old_time))

        monkeypatch.setattr("src.services.file_service.settings.FILE_TTL_SECONDS", 3600)
        deleted = svc.cleanup_expired_files()
        assert deleted == 1
        assert not old_file.exists()

    def test_cleanup_keeps_recent_files(self, tmp_path):
        svc = FileService(output_dir=tmp_path)
        new_file = tmp_path / "new_presentation.pptx"
        new_file.touch()

        deleted = svc.cleanup_expired_files()
        assert deleted == 0
        assert new_file.exists()
