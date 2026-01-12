"""Custom exception classes for bookmark organization.

This module defines a hierarchy of custom exceptions used throughout the
application for better error handling and debugging. All exceptions inherit
from BookmarkOrganizerError to allow catching all application-specific errors.
"""


class BookmarkOrganizerError(Exception):
    """Base exception class for all bookmark organizer errors.

    All custom exceptions in this module inherit from this class, allowing
    code to catch all application-specific errors with a single except clause.

    Example:
        >>> try:
        ...     # Some operation
        ...     pass
        ... except BookmarkOrganizerError as e:
        ...     print(f"Application error: {e}")
    """

    pass


class ParsingError(BookmarkOrganizerError):
    """Raised when HTML parsing fails.

    This exception is raised when there are issues parsing the bookmark HTML file,
    such as invalid HTML structure, missing required elements, or file read errors.

    Args:
        message: Human-readable error message describing the parsing failure.
        file_path: Optional path to the file that failed to parse.

    Example:
        >>> raise ParsingError("Invalid HTML structure: root <DL> element not found", "bookmarks.html")
    """

    def __init__(self, message: str, file_path: str | None = None) -> None:
        """Initialize ParsingError with message and optional file path.

        Args:
            message: Error message describing the parsing failure.
            file_path: Optional path to the file that failed to parse.
        """
        self.message = message
        self.file_path = file_path
        if file_path:
            super().__init__(f"{message} (file: {file_path})")
        else:
            super().__init__(message)


class InvalidBookmarkError(BookmarkOrganizerError):
    """Raised when bookmark data is invalid.

    This exception is raised when a bookmark fails validation, such as
    missing required fields, invalid URL format, or invalid date values.

    Args:
        message: Human-readable error message describing the validation failure.
        url: Optional URL of the bookmark that failed validation.

    Example:
        >>> raise InvalidBookmarkError("Title cannot be empty", "https://example.com")
    """

    def __init__(self, message: str, url: str | None = None) -> None:
        """Initialize InvalidBookmarkError with message and optional URL.

        Args:
            message: Error message describing the validation failure.
            url: Optional URL of the bookmark that failed validation.
        """
        self.message = message
        self.url = url
        if url:
            super().__init__(f"{message} (URL: {url})")
        else:
            super().__init__(message)


class APIError(BookmarkOrganizerError):
    """Base class for API-related errors.

    All API-related exceptions inherit from this class, allowing code to catch
    all API errors with a single except clause.

    Args:
        message: Human-readable error message describing the API error.
        status_code: Optional HTTP status code from the API response.

    Example:
        >>> raise APIError("Failed to connect to API", status_code=500)
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialize APIError with message and optional status code.

        Args:
            message: Error message describing the API error.
            status_code: Optional HTTP status code from the API response.
        """
        self.message = message
        self.status_code = status_code
        if status_code:
            super().__init__(f"{message} (status code: {status_code})")
        else:
            super().__init__(message)


class APIRateLimitError(APIError):
    """Raised when API rate limit is exceeded (429 response).

    This exception is raised when the API returns a 429 status code,
    indicating that too many requests have been made. The application
    should implement exponential backoff and retry logic when catching this.

    Args:
        message: Human-readable error message describing the rate limit error.
        retry_after: Optional number of seconds to wait before retrying.

    Example:
        >>> raise APIRateLimitError("Rate limit exceeded", retry_after=60)
    """

    def __init__(self, message: str = "API rate limit exceeded", retry_after: int | None = None) -> None:
        """Initialize APIRateLimitError with message and optional retry delay.

        Args:
            message: Error message describing the rate limit error.
            retry_after: Optional number of seconds to wait before retrying.
        """
        self.message = message
        self.retry_after = retry_after
        super().__init__(message, status_code=429)
        if retry_after:
            self.args = (f"{message} (retry after {retry_after} seconds)",)


class APIResponseError(APIError):
    """Raised when API response is invalid or cannot be parsed.

    This exception is raised when the API returns a response that cannot be
    parsed, contains invalid data, or is missing required fields.

    Args:
        message: Human-readable error message describing the response error.
        response_data: Optional raw response data that caused the error.

    Example:
        >>> raise APIResponseError("Invalid JSON in API response", response_data="...")
    """

    def __init__(self, message: str, response_data: str | None = None) -> None:
        """Initialize APIResponseError with message and optional response data.

        Args:
            message: Error message describing the response error.
            response_data: Optional raw response data that caused the error.
        """
        self.message = message
        self.response_data = response_data
        super().__init__(message)
        if response_data:
            self.args = (f"{message} (response: {response_data[:100]}...)",)


class MatchingError(BookmarkOrganizerError):
    """Raised when response-to-bookmark matching fails.

    This exception is raised when there are issues matching API responses back
    to original bookmarks, such as missing IDs, duplicate IDs, or mismatched counts.

    Args:
        message: Human-readable error message describing the matching failure.
        missing_ids: Optional list of IDs that were expected but not found in responses.
        duplicate_ids: Optional list of IDs that appeared multiple times in responses.

    Example:
        >>> raise MatchingError("Missing IDs in response", missing_ids=[1, 2, 3])
    """

    def __init__(
        self,
        message: str,
        missing_ids: list[int] | None = None,
        duplicate_ids: list[int] | None = None,
    ) -> None:
        """Initialize MatchingError with message and optional ID lists.

        Args:
            message: Error message describing the matching failure.
            missing_ids: Optional list of IDs that were expected but not found.
            duplicate_ids: Optional list of IDs that appeared multiple times.
        """
        self.message = message
        self.missing_ids = missing_ids or []
        self.duplicate_ids = duplicate_ids or []
        details = []
        if missing_ids:
            details.append(f"missing IDs: {missing_ids}")
        if duplicate_ids:
            details.append(f"duplicate IDs: {duplicate_ids}")
        if details:
            super().__init__(f"{message} ({', '.join(details)})")
        else:
            super().__init__(message)


class ProgressError(BookmarkOrganizerError):
    """Raised when progress save/load fails.

    This exception is raised when there are issues saving or loading progress
    state, such as file permission errors, invalid JSON, or corrupted data.

    Args:
        message: Human-readable error message describing the progress error.
        file_path: Optional path to the progress file that caused the error.

    Example:
        >>> raise ProgressError("Failed to save progress", "progress.json")
    """

    def __init__(self, message: str, file_path: str | None = None) -> None:
        """Initialize ProgressError with message and optional file path.

        Args:
            message: Error message describing the progress error.
            file_path: Optional path to the progress file that caused the error.
        """
        self.message = message
        self.file_path = file_path
        if file_path:
            super().__init__(f"{message} (file: {file_path})")
        else:
            super().__init__(message)
