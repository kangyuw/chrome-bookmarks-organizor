"""Unit tests for Pydantic models.

Tests cover validation, serialization, and edge cases for all models.
"""

import json
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from pydantic import ValidationError

from src.models import Bookmark, ClassifiedBookmark, Config, ProgressState


class TestBookmark:
    """Test suite for Bookmark model."""

    def test_valid_bookmark(self) -> None:
        """Test creating a valid bookmark."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Example Site",
            add_date=1609459200,
            folder_path=["Tech", "Web Development"],
        )
        assert bookmark.url == "https://example.com"
        assert bookmark.title == "Example Site"
        assert bookmark.add_date == 1609459200
        assert bookmark.folder_path == ["Tech", "Web Development"]
        assert bookmark.description is None

    def test_bookmark_with_description(self) -> None:
        """Test bookmark with optional description."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Example Site",
            add_date=1609459200,
            folder_path=[],
            description="A test description",
        )
        assert bookmark.description == "A test description"

    def test_url_validation_valid(self) -> None:
        """Test that valid URLs are accepted."""
        valid_urls = [
            "https://example.com",
            "http://example.com",
            "https://example.com/path?query=value",
            "https://subdomain.example.com",
        ]
        for url in valid_urls:
            bookmark = Bookmark(
                url=url,
                title="Test",
                add_date=1609459200,
                folder_path=[],
            )
            assert str(bookmark.url) == url

    def test_url_validation_invalid(self) -> None:
        """Test that invalid URLs are rejected."""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Only HTTP/HTTPS allowed
            "javascript:alert(1)",
            "",
        ]
        for url in invalid_urls:
            with pytest.raises(ValidationError):
                Bookmark(
                    url=url,
                    title="Test",
                    add_date=1609459200,
                    folder_path=[],
                )

    def test_title_validation_empty(self) -> None:
        """Test that empty titles are rejected."""
        with pytest.raises(ValidationError, match="Title cannot be empty"):
            Bookmark(
                url="https://example.com",
                title="",
                add_date=1609459200,
                folder_path=[],
            )

    def test_title_validation_whitespace_only(self) -> None:
        """Test that whitespace-only titles are rejected."""
        with pytest.raises(ValidationError, match="Title cannot be empty"):
            Bookmark(
                url="https://example.com",
                title="   ",
                add_date=1609459200,
                folder_path=[],
            )

    def test_title_trimming(self) -> None:
        """Test that titles are trimmed of leading/trailing whitespace."""
        bookmark = Bookmark(
            url="https://example.com",
            title="  Example Site  ",
            add_date=1609459200,
            folder_path=[],
        )
        assert bookmark.title == "Example Site"

    def test_add_date_validation_negative(self) -> None:
        """Test that negative timestamps are rejected."""
        with pytest.raises(ValidationError, match="add_date cannot be negative"):
            Bookmark(
                url="https://example.com",
                title="Test",
                add_date=-1,
                folder_path=[],
            )

    def test_add_date_validation_too_large(self) -> None:
        """Test that unreasonably large timestamps are rejected."""
        with pytest.raises(ValidationError, match="is unreasonably large"):
            Bookmark(
                url="https://example.com",
                title="Test",
                add_date=99999999999,
                folder_path=[],
            )

    def test_add_date_validation_valid(self) -> None:
        """Test that valid timestamps are accepted."""
        valid_dates = [
            0,  # Epoch
            1609459200,  # 2021-01-01
            int(datetime.now().timestamp()),  # Current time
        ]
        for date in valid_dates:
            bookmark = Bookmark(
                url="https://example.com",
                title="Test",
                add_date=date,
                folder_path=[],
            )
            assert bookmark.add_date == date

    def test_folder_path_validation_empty_list(self) -> None:
        """Test that empty folder path list is valid."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Test",
            add_date=1609459200,
            folder_path=[],
        )
        assert bookmark.folder_path == []

    def test_folder_path_trimming(self) -> None:
        """Test that folder names are trimmed."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Test",
            add_date=1609459200,
            folder_path=["  Tech  ", "  Web Development  "],
        )
        assert bookmark.folder_path == ["Tech", "Web Development"]

    def test_folder_path_empty_strings_removed(self) -> None:
        """Test that empty strings in folder_path are removed."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Test",
            add_date=1609459200,
            folder_path=["Tech", "", "Web Development", "   "],
        )
        assert bookmark.folder_path == ["Tech", "Web Development"]

    def test_json_serialization(self) -> None:
        """Test JSON serialization via model_dump."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Example Site",
            add_date=1609459200,
            folder_path=["Tech"],
            description="Test description",
        )
        data = bookmark.model_dump()
        assert isinstance(data, dict)
        assert data["url"] == "https://example.com"
        assert data["title"] == "Example Site"
        assert data["add_date"] == 1609459200
        assert data["folder_path"] == ["Tech"]
        assert data["description"] == "Test description"

    def test_json_deserialization(self) -> None:
        """Test JSON deserialization via model_validate."""
        data = {
            "url": "https://example.com",
            "title": "Example Site",
            "add_date": 1609459200,
            "folder_path": ["Tech"],
            "description": "Test description",
        }
        bookmark = Bookmark.model_validate(data)
        assert bookmark.url == "https://example.com"
        assert bookmark.title == "Example Site"
        assert bookmark.add_date == 1609459200
        assert bookmark.folder_path == ["Tech"]
        assert bookmark.description == "Test description"

    def test_model_dump_json(self) -> None:
        """Test model_dump_json method."""
        bookmark = Bookmark(
            url="https://example.com",
            title="Example Site",
            add_date=1609459200,
            folder_path=["Tech"],
        )
        json_str = bookmark.model_dump_json()
        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["url"] == "https://example.com"
        assert data["title"] == "Example Site"


class TestClassifiedBookmark:
    """Test suite for ClassifiedBookmark model."""

    def test_valid_classified_bookmark(self) -> None:
        """Test creating a valid classified bookmark."""
        classified = ClassifiedBookmark(
            url="https://example.com",
            title="Example Site",
            add_date=1609459200,
            folder_path=["Tech"],
            category_path=["Tech", "Web Development"],
            ai_description="A comprehensive guide to web development",
        )
        assert classified.category_path == ["Tech", "Web Development"]
        assert classified.ai_description == "A comprehensive guide to web development"
        assert classified.series_group is None
        assert classified.is_broken is None

    def test_classified_bookmark_inheritance(self) -> None:
        """Test that ClassifiedBookmark inherits from Bookmark."""
        classified = ClassifiedBookmark(
            url="https://example.com",
            title="Example Site",
            add_date=1609459200,
            folder_path=["Tech"],
            category_path=["Tech", "Web Development"],
            ai_description="Test description",
        )
        # Should have all Bookmark fields
        assert classified.url == "https://example.com"
        assert classified.title == "Example Site"
        assert classified.add_date == 1609459200
        assert classified.folder_path == ["Tech"]
        # Should have additional fields
        assert classified.category_path == ["Tech", "Web Development"]
        assert classified.ai_description == "Test description"

    def test_category_path_validation_empty(self) -> None:
        """Test that empty category_path is rejected."""
        with pytest.raises(ValidationError, match="category_path cannot be empty"):
            ClassifiedBookmark(
                url="https://example.com",
                title="Test",
                add_date=1609459200,
                folder_path=[],
                category_path=[],
                ai_description="Test description",
            )

    def test_category_path_validation_empty_strings(self) -> None:
        """Test that category_path with empty strings is rejected."""
        with pytest.raises(ValidationError, match="cannot contain empty strings"):
            ClassifiedBookmark(
                url="https://example.com",
                title="Test",
                add_date=1609459200,
                folder_path=[],
                category_path=["Tech", ""],
                ai_description="Test description",
            )

    def test_category_path_trimming(self) -> None:
        """Test that category names are trimmed."""
        classified = ClassifiedBookmark(
            url="https://example.com",
            title="Test",
            add_date=1609459200,
            folder_path=[],
            category_path=["  Tech  ", "  Web Development  "],
            ai_description="Test description",
        )
        assert classified.category_path == ["Tech", "Web Development"]

    def test_ai_description_validation_empty(self) -> None:
        """Test that empty ai_description is rejected."""
        with pytest.raises(ValidationError, match="ai_description cannot be empty"):
            ClassifiedBookmark(
                url="https://example.com",
                title="Test",
                add_date=1609459200,
                folder_path=[],
                category_path=["Tech"],
                ai_description="",
            )

    def test_ai_description_trimming(self) -> None:
        """Test that ai_description is trimmed."""
        classified = ClassifiedBookmark(
            url="https://example.com",
            title="Test",
            add_date=1609459200,
            folder_path=[],
            category_path=["Tech"],
            ai_description="  Test description  ",
        )
        assert classified.ai_description == "Test description"

    def test_series_group_optional(self) -> None:
        """Test that series_group is optional."""
        classified = ClassifiedBookmark(
            url="https://example.com",
            title="Test",
            add_date=1609459200,
            folder_path=[],
            category_path=["Tech"],
            ai_description="Test description",
            series_group="test-series",
        )
        assert classified.series_group == "test-series"

    def test_is_broken_optional(self) -> None:
        """Test that is_broken is optional."""
        classified = ClassifiedBookmark(
            url="https://example.com",
            title="Test",
            add_date=1609459200,
            folder_path=[],
            category_path=["Tech"],
            ai_description="Test description",
            is_broken=True,
        )
        assert classified.is_broken is True

    def test_json_serialization(self) -> None:
        """Test JSON serialization of ClassifiedBookmark."""
        classified = ClassifiedBookmark(
            url="https://example.com",
            title="Example Site",
            add_date=1609459200,
            folder_path=["Tech"],
            category_path=["Tech", "Web Development"],
            ai_description="Test description",
            series_group="test-series",
            is_broken=False,
        )
        data = classified.model_dump()
        assert data["category_path"] == ["Tech", "Web Development"]
        assert data["ai_description"] == "Test description"
        assert data["series_group"] == "test-series"
        assert data["is_broken"] is False

    def test_json_deserialization(self) -> None:
        """Test JSON deserialization of ClassifiedBookmark."""
        data = {
            "url": "https://example.com",
            "title": "Example Site",
            "add_date": 1609459200,
            "folder_path": ["Tech"],
            "category_path": ["Tech", "Web Development"],
            "ai_description": "Test description",
            "series_group": "test-series",
            "is_broken": False,
        }
        classified = ClassifiedBookmark.model_validate(data)
        assert classified.category_path == ["Tech", "Web Development"]
        assert classified.ai_description == "Test description"
        assert classified.series_group == "test-series"
        assert classified.is_broken is False


class TestProgressState:
    """Test suite for ProgressState model."""

    def test_valid_progress_state(self) -> None:
        """Test creating a valid progress state."""
        progress = ProgressState(
            last_batch_id=5,
            processed_count=300,
            total_count=1000,
            processed_bookmarks=[],
        )
        assert progress.last_batch_id == 5
        assert progress.processed_count == 300
        assert progress.total_count == 1000
        assert progress.processed_bookmarks == []
        assert isinstance(progress.timestamp, int)

    def test_progress_state_defaults(self) -> None:
        """Test that defaults are applied correctly."""
        progress = ProgressState(
            last_batch_id=0,
            processed_count=0,
            total_count=100,
        )
        assert progress.processed_bookmarks == []
        assert isinstance(progress.timestamp, int)
        assert progress.timestamp > 0

    def test_last_batch_id_validation_negative(self) -> None:
        """Test that negative last_batch_id is rejected."""
        with pytest.raises(ValidationError):
            ProgressState(
                last_batch_id=-1,
                processed_count=0,
                total_count=100,
            )

    def test_processed_count_validation_negative(self) -> None:
        """Test that negative processed_count is rejected."""
        with pytest.raises(ValidationError):
            ProgressState(
                last_batch_id=0,
                processed_count=-1,
                total_count=100,
            )

    def test_total_count_validation_negative(self) -> None:
        """Test that negative total_count is rejected."""
        with pytest.raises(ValidationError):
            ProgressState(
                last_batch_id=0,
                processed_count=0,
                total_count=-1,
            )

    def test_processed_count_exceeds_total(self) -> None:
        """Test that processed_count cannot exceed total_count."""
        with pytest.raises(ValidationError, match="cannot exceed"):
            ProgressState(
                last_batch_id=0,
                processed_count=101,
                total_count=100,
            )

    def test_save_and_load_file(self) -> None:
        """Test saving and loading progress state from file."""
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "progress.json"
            progress = ProgressState(
                last_batch_id=5,
                processed_count=300,
                total_count=1000,
            )
            progress.save_to_file(file_path)
            assert file_path.exists()

            loaded = ProgressState.load_from_file(file_path)
            assert loaded is not None
            assert loaded.last_batch_id == 5
            assert loaded.processed_count == 300
            assert loaded.total_count == 1000

    def test_load_file_not_exists(self) -> None:
        """Test loading from non-existent file returns None."""
        file_path = Path("/nonexistent/path/progress.json")
        loaded = ProgressState.load_from_file(file_path)
        assert loaded is None

    def test_save_and_load_with_bookmarks(self) -> None:
        """Test saving and loading progress state with processed bookmarks."""
        with TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "progress.json"
            bookmarks = [
                ClassifiedBookmark(
                    url="https://example.com",
                    title="Example",
                    add_date=1609459200,
                    folder_path=[],
                    category_path=["Tech"],
                    ai_description="Test",
                )
            ]
            progress = ProgressState(
                last_batch_id=1,
                processed_count=1,
                total_count=10,
                processed_bookmarks=bookmarks,
            )
            progress.save_to_file(file_path)

            loaded = ProgressState.load_from_file(file_path)
            assert loaded is not None
            assert len(loaded.processed_bookmarks) == 1
            assert loaded.processed_bookmarks[0].url == "https://example.com"

    def test_json_serialization(self) -> None:
        """Test JSON serialization of ProgressState."""
        progress = ProgressState(
            last_batch_id=5,
            processed_count=300,
            total_count=1000,
        )
        data = progress.model_dump()
        assert data["last_batch_id"] == 5
        assert data["processed_count"] == 300
        assert data["total_count"] == 1000
        assert "timestamp" in data


class TestConfig:
    """Test suite for Config model."""

    def test_valid_config(self) -> None:
        """Test creating a valid config."""
        config = Config(gemini_api_key="test-key-123")
        assert config.gemini_api_key == "test-key-123"
        assert config.batch_size == 60
        assert config.description_language == "english"
        assert config.enable_web_search is True
        assert config.model_name == "gemini-1.5-flash"
        assert config.max_retries == 3
        assert config.retry_backoff_factor == 2.0
        assert config.log_level == "INFO"

    def test_config_custom_values(self) -> None:
        """Test config with custom values."""
        config = Config(
            gemini_api_key="test-key",
            batch_size=80,
            description_language="chinese",
            enable_web_search=False,
            model_name="gemini-1.5-pro",
            max_retries=5,
            retry_backoff_factor=3.0,
            log_level="DEBUG",
        )
        assert config.batch_size == 80
        assert config.description_language == "chinese"
        assert config.enable_web_search is False
        assert config.model_name == "gemini-1.5-pro"
        assert config.max_retries == 5
        assert config.retry_backoff_factor == 3.0
        assert config.log_level == "DEBUG"

    def test_api_key_validation_empty(self) -> None:
        """Test that empty API key is rejected."""
        with pytest.raises(ValidationError, match="Gemini API key is required"):
            Config(gemini_api_key="")

    def test_api_key_validation_whitespace_only(self) -> None:
        """Test that whitespace-only API key is rejected."""
        with pytest.raises(ValidationError, match="Gemini API key is required"):
            Config(gemini_api_key="   ")

    def test_api_key_trimming(self) -> None:
        """Test that API key is trimmed."""
        config = Config(gemini_api_key="  test-key  ")
        assert config.gemini_api_key == "test-key"

    def test_batch_size_validation_too_small(self) -> None:
        """Test that batch_size < 10 is rejected."""
        with pytest.raises(ValidationError):
            Config(gemini_api_key="test-key", batch_size=9)

    def test_batch_size_validation_too_large(self) -> None:
        """Test that batch_size > 100 is rejected."""
        with pytest.raises(ValidationError):
            Config(gemini_api_key="test-key", batch_size=101)

    def test_description_language_validation(self) -> None:
        """Test that invalid description_language is rejected."""
        with pytest.raises(ValidationError):
            Config(gemini_api_key="test-key", description_language="invalid")

    def test_log_level_validation(self) -> None:
        """Test that invalid log_level is rejected."""
        with pytest.raises(ValidationError):
            Config(gemini_api_key="test-key", log_level="INVALID")

    def test_max_retries_validation_too_small(self) -> None:
        """Test that max_retries < 1 is rejected."""
        with pytest.raises(ValidationError):
            Config(gemini_api_key="test-key", max_retries=0)

    def test_max_retries_validation_too_large(self) -> None:
        """Test that max_retries > 10 is rejected."""
        with pytest.raises(ValidationError):
            Config(gemini_api_key="test-key", max_retries=11)

    def test_retry_backoff_factor_validation_too_small(self) -> None:
        """Test that retry_backoff_factor < 1.0 is rejected."""
        with pytest.raises(ValidationError):
            Config(gemini_api_key="test-key", retry_backoff_factor=0.9)

    def test_retry_backoff_factor_validation_too_large(self) -> None:
        """Test that retry_backoff_factor > 10.0 is rejected."""
        with pytest.raises(ValidationError):
            Config(gemini_api_key="test-key", retry_backoff_factor=10.1)

    def test_load_from_yaml(self) -> None:
        """Test loading config from YAML file."""
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            yaml_content = """
gemini_api_key: "test-key-123"
batch_size: 80
description_language: "chinese"
enable_web_search: true
model_name: "gemini-1.5-pro"
max_retries: 5
retry_backoff_factor: 3.0
log_level: "DEBUG"
"""
            yaml_path.write_text(yaml_content, encoding="utf-8")

            config = Config.load_from_yaml(yaml_path)
            assert config.gemini_api_key == "test-key-123"
            assert config.batch_size == 80
            assert config.description_language == "chinese"
            assert config.enable_web_search is True
            assert config.model_name == "gemini-1.5-pro"
            assert config.max_retries == 5
            assert config.retry_backoff_factor == 3.0
            assert config.log_level == "DEBUG"

    def test_load_from_yaml_file_not_exists(self) -> None:
        """Test loading from non-existent YAML file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            Config.load_from_yaml("/nonexistent/path/config.yaml")

    def test_load_from_yaml_invalid_yaml(self) -> None:
        """Test loading from invalid YAML raises ValueError."""
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            yaml_path.write_text("invalid: yaml: content: [", encoding="utf-8")

            with pytest.raises(ValueError, match="Invalid YAML"):
                Config.load_from_yaml(yaml_path)

    def test_load_from_yaml_empty_file(self) -> None:
        """Test loading from empty YAML file raises ValueError."""
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            yaml_path.write_text("", encoding="utf-8")

            with pytest.raises(ValueError, match="empty"):
                Config.load_from_yaml(yaml_path)

    def test_load_from_yaml_partial_config(self) -> None:
        """Test loading YAML with only required fields uses defaults."""
        with TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "config.yaml"
            yaml_content = """
gemini_api_key: "test-key-123"
"""
            yaml_path.write_text(yaml_content, encoding="utf-8")

            config = Config.load_from_yaml(yaml_path)
            assert config.gemini_api_key == "test-key-123"
            assert config.batch_size == 60  # Default value
            assert config.description_language == "english"  # Default value

    def test_json_serialization(self) -> None:
        """Test JSON serialization of Config."""
        config = Config(gemini_api_key="test-key")
        data = config.model_dump()
        assert data["gemini_api_key"] == "test-key"
        assert data["batch_size"] == 60
        assert data["description_language"] == "english"
