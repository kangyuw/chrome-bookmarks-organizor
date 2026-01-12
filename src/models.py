"""Pydantic data models for bookmark organization.

This module defines the core data models used throughout the application:
- Bookmark: Base bookmark model with validation
- ClassifiedBookmark: Extended model with AI classification results
- ProgressState: Model for resume/checkpoint functionality
- Config: Application configuration model with YAML support
"""

import os
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional

import yaml
from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


class Bookmark(BaseModel):
    """Base bookmark model with validation.

    Represents a single bookmark extracted from Chrome's Netscape bookmark format.
    All fields are validated to ensure data integrity.

    Attributes:
        url: The bookmark URL (validated as HTTP/HTTPS URL).
        title: The bookmark title (non-empty, trimmed).
        add_date: Unix timestamp when bookmark was added.
        folder_path: List of folder names representing the bookmark's location
            in the original folder hierarchy.
        description: Optional description text from the bookmark file.

    Example:
        >>> bookmark = Bookmark(
        ...     url="https://example.com",
        ...     title="Example Site",
        ...     add_date=1609459200,
        ...     folder_path=["Tech", "Web Development"]
        ... )
        >>> bookmark.title
        'Example Site'
    """

    url: HttpUrl
    title: str
    add_date: int
    folder_path: List[str]
    description: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate that title is not empty.

        Args:
            v: The title string to validate.

        Returns:
            The trimmed title string.

        Raises:
            ValueError: If title is empty or contains only whitespace.
        """
        if not v or len(v.strip()) == 0:
            raise ValueError("Title cannot be empty")
        return v.strip()

    @field_validator("add_date")
    @classmethod
    def validate_add_date(cls, v: int) -> int:
        """Validate that add_date is a reasonable Unix timestamp.

        Args:
            v: The Unix timestamp to validate.

        Returns:
            The validated timestamp.

        Raises:
            ValueError: If timestamp is negative or unreasonably large.
        """
        if v < 0:
            raise ValueError("add_date cannot be negative")
        # Allow timestamps up to year 2100 (reasonable future limit)
        max_timestamp = 4102444800
        if v > max_timestamp:
            raise ValueError(f"add_date {v} is unreasonably large (max: {max_timestamp})")
        return v

    @field_validator("folder_path")
    @classmethod
    def validate_folder_path(cls, v: List[str]) -> List[str]:
        """Validate folder path structure.

        Args:
            v: List of folder names.

        Returns:
            List of trimmed, non-empty folder names.

        Raises:
            ValueError: If any folder name is empty after trimming.
        """
        if not isinstance(v, list):
            raise ValueError("folder_path must be a list")
        trimmed = [folder.strip() for folder in v if folder.strip()]
        return trimmed

    def model_dump_json(self, **kwargs) -> str:
        """Serialize model to JSON string.

        Args:
            **kwargs: Additional arguments passed to Pydantic's model_dump_json.

        Returns:
            JSON string representation of the model.
        """
        return super().model_dump_json(**kwargs)

    class Config:
        """Pydantic model configuration."""

        json_encoders = {
            datetime: lambda v: int(v.timestamp()),
        }


class ClassificationRequest(BaseModel):
    """Temporary model for API communication (title-only approach).

    Used to send bookmark data to the Gemini API with only essential information
    (title and folder path) to reduce token usage. The ID is used to match
    responses back to original bookmarks.

    Attributes:
        id: Unique integer identifier for matching responses to original bookmarks.
        title: Bookmark title.
        folder_path: Original folder structure as a list of folder names.

    Note:
        This model is temporary and only used for API communication, not persisted.
    """

    id: int
    title: str
    folder_path: List[str]


class ClassificationResponse(BaseModel):
    """Temporary model for API response parsing.

    Used to parse Gemini API responses and match them back to original bookmarks
    using the ID field.

    Attributes:
        id: Matches the request ID for matching.
        category_path: AI-assigned semantic category path.
        ai_description: AI-generated description.
        series_group: Optional identifier for bookmarks in the same series/site.
        is_broken: Optional flag indicating if the link is broken/inaccessible.

    Note:
        This model is temporary and only used for API communication, not persisted.
    """

    id: int
    category_path: List[str]
    ai_description: str
    series_group: Optional[str] = None
    is_broken: Optional[bool] = None


class ClassifiedBookmark(Bookmark):
    """Extended bookmark model with AI classification results.

    Extends the base Bookmark model with fields populated by AI classification.
    Used to store the results of semantic categorization and enrichment.

    Attributes:
        category_path: Semantic category path assigned by AI (e.g., ["Tech", "Coding", "Python"]).
        ai_description: AI-generated description (typically 30 words) in the configured language.
        series_group: Optional identifier for bookmarks that belong to the same series/site.
        is_broken: Optional flag indicating if the link is broken/inaccessible (detected via web search).

    Example:
        >>> classified = ClassifiedBookmark(
        ...     url="https://example.com",
        ...     title="Example Site",
        ...     add_date=1609459200,
        ...     folder_path=["Tech"],
        ...     category_path=["Tech", "Web Development"],
        ...     ai_description="A comprehensive guide to web development..."
        ... )
        >>> classified.category_path
        ['Tech', 'Web Development']
    """

    category_path: List[str]
    ai_description: str
    series_group: Optional[str] = None
    is_broken: Optional[bool] = None

    @field_validator("category_path")
    @classmethod
    def validate_category_path(cls, v: List[str]) -> List[str]:
        """Validate category path structure.

        Args:
            v: List of category names.

        Returns:
            List of trimmed, non-empty category names.

        Raises:
            ValueError: If category_path is empty or contains empty strings.
        """
        if not isinstance(v, list):
            raise ValueError("category_path must be a list")
        if len(v) == 0:
            raise ValueError("category_path cannot be empty")
        trimmed = [category.strip() for category in v]
        if any(not cat for cat in trimmed):
            raise ValueError("category_path cannot contain empty strings")
        return trimmed

    @field_validator("ai_description")
    @classmethod
    def validate_ai_description(cls, v: str) -> str:
        """Validate AI description is not empty.

        Args:
            v: The description string to validate.

        Returns:
            The trimmed description string.

        Raises:
            ValueError: If description is empty or contains only whitespace.
        """
        if not v or len(v.strip()) == 0:
            raise ValueError("ai_description cannot be empty")
        return v.strip()


class ProgressState(BaseModel):
    """Model for tracking processing progress and enabling resume functionality.

    Stores checkpoint information to allow resuming processing after interruption.
    Serialized to JSON for persistence.

    Attributes:
        last_batch_id: The ID of the last successfully processed batch (0-indexed).
        processed_count: Total number of bookmarks processed so far.
        total_count: Total number of bookmarks to process.
        processed_bookmarks: List of ClassifiedBookmark instances that have been processed.
        timestamp: Unix timestamp when this progress state was saved.

    Example:
        >>> progress = ProgressState(
        ...     last_batch_id=5,
        ...     processed_count=300,
        ...     total_count=1000,
        ...     processed_bookmarks=[...]
        ... )
        >>> progress.save_to_file("progress.json")
    """

    last_batch_id: int = Field(ge=0, description="Last successfully processed batch ID (0-indexed)")
    processed_count: int = Field(ge=0, description="Total number of bookmarks processed")
    total_count: int = Field(ge=0, description="Total number of bookmarks to process")
    processed_bookmarks: List[ClassifiedBookmark] = Field(
        default_factory=list, description="List of processed bookmarks"
    )
    timestamp: int = Field(
        default_factory=lambda: int(datetime.now().timestamp()),
        description="Unix timestamp when progress was saved",
    )

    @model_validator(mode="after")
    def validate_counts(self) -> "ProgressState":
        """Validate that processed_count does not exceed total_count.

        Returns:
            Self after validation.

        Raises:
            ValueError: If processed_count > total_count.
        """
        if self.processed_count > self.total_count:
            raise ValueError(
                f"processed_count ({self.processed_count}) cannot exceed "
                f"total_count ({self.total_count})"
            )
        return self

    def save_to_file(self, file_path: Path | str) -> None:
        """Save progress state to JSON file.

        Args:
            file_path: Path to the JSON file where progress will be saved.

        Raises:
            OSError: If file cannot be written.
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load_from_file(cls, file_path: Path | str) -> Optional["ProgressState"]:
        """Load progress state from JSON file.

        Args:
            file_path: Path to the JSON file containing progress state.

        Returns:
            ProgressState instance if file exists and is valid, None otherwise.
        """
        path = Path(file_path)
        if not path.exists():
            return None
        try:
            content = path.read_text(encoding="utf-8")
            return cls.model_validate_json(content)
        except Exception:
            return None


class Config(BaseModel):
    """Application configuration model with YAML loading support.

    Loads and validates application configuration from YAML files.
    All fields are validated to ensure configuration integrity.

    Attributes:
        gemini_api_key: Google Gemini API key (required, can be set via GEMINI_API_KEY env var).
        batch_size: Number of bookmarks to process per API batch (10-100, default: 25).
        enable_web_search: Whether to enable web search in Gemini API.
        model_name: Gemini model name to use (default: "gemini-1.5-flash").
        max_retries: Maximum number of retry attempts for API calls (1-10, default: 3).
        retry_backoff_factor: Exponential backoff multiplier for retries (1.0-10.0, default: 2.0).
        log_level: Logging level ("DEBUG", "INFO", "WARNING", "ERROR").
        excluded_paths: List of folder paths to exclude from processing (e.g., ["misc", "archives"]).
            Bookmarks in these paths will be preserved with their original paths.

    Example:
        >>> config = Config.load_from_yaml("config/config.yaml")
        >>> config.batch_size
        25
    """

    gemini_api_key: Optional[str] = Field(
        default=None,
        description="Google Gemini API key (can be set via GEMINI_API_KEY environment variable)",
    )
    batch_size: int = Field(
        ge=10,
        le=100,
        default=25,
        description="Batch size for API calls (title-only approach allows larger batches if needed)",
    )
    enable_web_search: bool = Field(default=True, description="Enable web search in Gemini API")
    model_name: str = Field(default="gemini-1.5-flash", description="Gemini model name")
    max_retries: int = Field(ge=1, le=10, default=3, description="Maximum retry attempts")
    retry_backoff_factor: float = Field(
        ge=1.0, le=10.0, default=2.0, description="Exponential backoff factor"
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Logging level"
    )
    excluded_paths: List[List[str]] = Field(
        default_factory=list,
        description="List of folder paths to exclude from processing (e.g., [['misc', 'archives']])",
    )

    @model_validator(mode="after")
    def validate_api_key(self) -> "Config":
        """Validate that API key is provided (from config or environment variable).

        Checks for API key in the following order:
        1. Value provided in config file
        2. GEMINI_API_KEY environment variable

        Returns:
            Self after validation.

        Raises:
            ValueError: If API key is not found in config or environment.
        """
        # Check if API key is already set from config
        if self.gemini_api_key and len(self.gemini_api_key.strip()) > 0:
            self.gemini_api_key = self.gemini_api_key.strip()
            return self

        # Try to get from environment variable
        env_key = os.getenv("GEMINI_API_KEY")
        if env_key and len(env_key.strip()) > 0:
            self.gemini_api_key = env_key.strip()
            return self

        # No API key found
        raise ValueError(
            "Gemini API key is required. Set it in config file or GEMINI_API_KEY environment variable"
        )

    @classmethod
    def load_from_yaml(cls, file_path: Path | str) -> "Config":
        """Load configuration from YAML file.

        Args:
            file_path: Path to the YAML configuration file.

        Returns:
            Config instance with loaded and validated values.

        Raises:
            FileNotFoundError: If configuration file does not exist.
            yaml.YAMLError: If YAML file is malformed.
            ValueError: If configuration values are invalid.

        Example:
            >>> config = Config.load_from_yaml("config/config.yaml")
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        try:
            content = path.read_text(encoding="utf-8")
            data = yaml.safe_load(content)
            if data is None:
                raise ValueError("Configuration file is empty")
            return cls.model_validate(data)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in configuration file: {e}") from e
