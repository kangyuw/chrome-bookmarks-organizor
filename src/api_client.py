"""API client for Gemini-based bookmark classification.

This module provides the GeminiClient class for classifying bookmarks using
Google's Gemini API. It implements a title-only approach to reduce token usage
while maintaining classification accuracy through web search.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from google import genai
from google.genai import types
from pydantic import ValidationError

from src.exceptions import (
    APIError,
    APIRateLimitError,
    APIResponseError,
    MatchingError,
    ProgressError,
)
from src.models import (
    Bookmark,
    ClassifiedBookmark,
    ClassificationRequest,
    ClassificationResponse,
    Config,
    ProgressState,
)

logger = logging.getLogger(__name__)


class GeminiClient:
    """Client for classifying bookmarks using Google Gemini API.

    Implements folder-aware batching and title-only requests to optimize
    token usage while maintaining classification accuracy.

    Attributes:
        config: Application configuration with API key and settings.
        model: Configured Gemini model instance.

    Example:
        >>> config = Config.load_from_yaml("config/config.yaml")
        >>> client = GeminiClient(config)
        >>> bookmarks = [Bookmark(...), ...]
        >>> classified = await client.process_all(bookmarks)
    """

    def __init__(self, config: Config) -> None:
        """Initialize GeminiClient with configuration.

        Args:
            config: Application configuration containing API key and settings.

        Raises:
            APIError: If API key is invalid or model cannot be initialized.
        """
        self.config = config

        try:
            self.client = genai.Client(api_key=config.gemini_api_key)
            self.model_name = config.model_name
            # Store generation config for use in API calls
            tools = None
            if config.enable_web_search:
                tools = [types.Tool(google_search=types.GoogleSearch())]
            
            self.generation_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.7,
                tools=tools,
            )
        except Exception as e:
            raise APIError(f"Failed to initialize Gemini client: {e}") from e

        logger.info(f"Initialized GeminiClient with model: {config.model_name}")

    def _is_path_excluded(self, folder_path: List[str]) -> bool:
        """Check if a folder path matches any excluded path.

        A bookmark is excluded if its folder_path starts with any of the
        excluded paths (prefix match).

        Args:
            folder_path: List of folder names representing the bookmark's path.

        Returns:
            True if the path matches any excluded path, False otherwise.

        Example:
            >>> client._is_path_excluded(["misc", "archives"])
            True  # if ["misc", "archives"] is in excluded_paths
        """
        if not self.config.excluded_paths:
            return False

        folder_path_tuple = tuple(folder_path)
        for excluded_path in self.config.excluded_paths:
            excluded_tuple = tuple(excluded_path)
            # Check if folder_path starts with excluded_path
            if len(folder_path_tuple) >= len(excluded_tuple):
                if folder_path_tuple[: len(excluded_tuple)] == excluded_tuple:
                    return True
        return False

    def _convert_to_classified_bookmark(self, bookmark: Bookmark) -> ClassifiedBookmark:
        """Convert a regular Bookmark to ClassifiedBookmark with original path.

        Used for excluded bookmarks that should preserve their original
        folder structure. The category_path is set to match the original
        folder_path, and a simple description is generated.

        Args:
            bookmark: Bookmark instance to convert.

        Returns:
            ClassifiedBookmark with original path preserved.
        """
        return ClassifiedBookmark(
            url=bookmark.url,
            title=bookmark.title,
            add_date=bookmark.add_date,
            folder_path=bookmark.folder_path,
            description=bookmark.description,
            category_path=bookmark.folder_path.copy(),  # Preserve original path
            ai_description=f"Bookmark from {bookmark.title}",
            series_group=None,
            is_broken=None,
        )

    def group_bookmarks_by_folder(
        self, bookmarks: List[Bookmark]
    ) -> Dict[Tuple[str, ...], List[Bookmark]]:
        """Group bookmarks by their folder path.

        Groups bookmarks that share the same folder_path tuple together.
        This enables folder-aware batching for better context.

        Args:
            bookmarks: List of Bookmark instances to group.

        Returns:
            Dictionary mapping folder_path tuple to list of bookmarks in that folder.

        Example:
            >>> bookmarks = [
            ...     Bookmark(..., folder_path=["Tech", "Python"]),
            ...     Bookmark(..., folder_path=["Tech", "Python"]),
            ...     Bookmark(..., folder_path=["Tech", "JavaScript"]),
            ... ]
            >>> grouped = client.group_bookmarks_by_folder(bookmarks)
            >>> len(grouped[("Tech", "Python")])
            2
        """
        grouped: Dict[Tuple[str, ...], List[Bookmark]] = {}
        for bookmark in bookmarks:
            folder_key = tuple(bookmark.folder_path)
            if folder_key not in grouped:
                grouped[folder_key] = []
            grouped[folder_key].append(bookmark)
        return grouped

    def create_batches_with_folder_context(
        self, bookmarks: List[Bookmark], batch_size: int
    ) -> List[Tuple[List[Bookmark], List[str]]]:
        """Create batches with folder context awareness.

        Groups bookmarks by folder first, then creates batches:
        - For folders with ≤batch_size bookmarks: single batch
        - For larger folders: splits into sub-batches

        Args:
            bookmarks: List of Bookmark instances to batch.
            batch_size: Maximum number of bookmarks per batch.

        Returns:
            List of tuples (bookmark_batch, folder_path) where folder_path
            is the list of folder names for that batch.

        Example:
            >>> bookmarks = [Bookmark(...), ...]
            >>> batches = client.create_batches_with_folder_context(bookmarks, 25)
            >>> len(batches[0][0])  # First batch size
            25
        """
        grouped = self.group_bookmarks_by_folder(bookmarks)
        batches: List[Tuple[List[Bookmark], List[str]]] = []

        for folder_path_tuple, folder_bookmarks in grouped.items():
            folder_path_list = list(folder_path_tuple)

            if len(folder_bookmarks) <= batch_size:
                # Single batch for this folder
                batches.append((folder_bookmarks, folder_path_list))
            else:
                # Split into multiple batches
                for i in range(0, len(folder_bookmarks), batch_size):
                    batch = folder_bookmarks[i : i + batch_size]
                    batches.append((batch, folder_path_list))

        logger.info(
            f"Created {len(batches)} batch(es) from {len(bookmarks)} bookmarks "
            f"across {len(grouped)} folder(s)"
        )
        return batches

    def prepare_batch_for_api(
        self, bookmarks: List[Bookmark]
    ) -> Tuple[List[ClassificationRequest], Dict[int, Bookmark]]:
        """Prepare bookmarks for API request (title-only conversion).

        Converts Bookmark list to ClassificationRequest list (title-only)
        and creates a mapping for response matching.

        Args:
            bookmarks: List of Bookmark instances to prepare.

        Returns:
            Tuple of (request_data, id_to_bookmark_map) where:
            - request_data: List of ClassificationRequest instances
            - id_to_bookmark_map: Dictionary mapping ID to original Bookmark

        Example:
            >>> bookmarks = [Bookmark(...), ...]
            >>> requests, mapping = client.prepare_batch_for_api(bookmarks)
            >>> len(requests) == len(bookmarks)
            True
        """
        requests: List[ClassificationRequest] = []
        id_to_bookmark: Dict[int, Bookmark] = {}

        for idx, bookmark in enumerate(bookmarks, start=1):
            request = ClassificationRequest(
                id=idx,
                title=bookmark.title,
                folder_path=bookmark.folder_path,
            )
            requests.append(request)
            id_to_bookmark[idx] = bookmark

        return requests, id_to_bookmark

    def match_responses_to_bookmarks(
        self,
        responses: List[ClassificationResponse],
        id_to_bookmark: Dict[int, Bookmark],
    ) -> List[ClassifiedBookmark]:
        """Match API responses back to original bookmarks.

        Matches ClassificationResponse by ID to original Bookmark and creates
        ClassifiedBookmark instances with AI classification results.

        Args:
            responses: List of ClassificationResponse from API.
            id_to_bookmark: Dictionary mapping ID to original Bookmark.

        Returns:
            List of ClassifiedBookmark instances with AI results.

        Raises:
            MatchingError: If IDs are missing, duplicated, or mismatched.

        Example:
            >>> responses = [ClassificationResponse(id=1, ...), ...]
            >>> id_to_bookmark = {1: Bookmark(...), ...}
            >>> classified = client.match_responses_to_bookmarks(responses, id_to_bookmark)
            >>> len(classified) == len(responses)
            True
        """
        # Check for missing IDs
        response_ids = {r.id for r in responses}
        expected_ids = set(id_to_bookmark.keys())
        missing_ids = list(expected_ids - response_ids)

        if missing_ids:
            raise MatchingError(
                "Missing IDs in API response",
                missing_ids=missing_ids,
            )

        # Check for duplicate IDs
        seen_ids: Dict[int, int] = {}
        duplicate_ids: List[int] = []
        for response in responses:
            if response.id in seen_ids:
                duplicate_ids.append(response.id)
            seen_ids[response.id] = seen_ids.get(response.id, 0) + 1

        if duplicate_ids:
            raise MatchingError(
                "Duplicate IDs in API response",
                duplicate_ids=duplicate_ids,
            )

        # Match and create ClassifiedBookmark instances
        classified: List[ClassifiedBookmark] = []
        for response in responses:
            bookmark = id_to_bookmark[response.id]
            classified_bookmark = ClassifiedBookmark(
                url=bookmark.url,
                title=bookmark.title,
                add_date=bookmark.add_date,
                folder_path=bookmark.folder_path,
                description=bookmark.description,
                category_path=response.category_path,
                ai_description=response.ai_description,
                series_group=response.series_group,
                is_broken=response.is_broken,
            )
            classified.append(classified_bookmark)

        return classified

    async def classify_batch(
        self, bookmarks: List[Bookmark], folder_path: List[str]
    ) -> List[ClassifiedBookmark]:
        """Classify a batch of bookmarks using Gemini API.

        Prepares title-only batch, sends to Gemini API with web search,
        parses JSON response, and matches back to original bookmarks.

        Args:
            bookmarks: List of Bookmark instances to classify.
            folder_path: Original folder path for context.

        Returns:
            List of ClassifiedBookmark instances with AI classification.

        Raises:
            APIError: If API call fails.
            APIResponseError: If response cannot be parsed.
            MatchingError: If response matching fails.

        Example:
            >>> bookmarks = [Bookmark(...), ...]
            >>> classified = await client.classify_batch(bookmarks, ["Tech"])
            >>> len(classified) == len(bookmarks)
            True
        """
        from src.prompts import get_classification_prompt

        # Prepare batch for API (title-only)
        requests, id_to_bookmark = self.prepare_batch_for_api(bookmarks)

        # Get prompt with folder context
        prompt = get_classification_prompt(requests, folder_path)

        # Call API with retry logic
        max_retries = self.config.max_retries
        retry_backoff = self.config.retry_backoff_factor

        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Calling Gemini API (attempt {attempt + 1}/{max_retries}) "
                    f"for {len(bookmarks)} bookmarks in folder: {' > '.join(folder_path) if folder_path else 'Root'}"
                )

                # Run synchronous API call in executor
                loop = asyncio.get_event_loop()
                try:
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.client.models.generate_content(
                            model=self.model_name,
                            contents=prompt,
                            config=self.generation_config,
                        ),
                    )
                except Exception as api_exception:
                    # Handle Google API exceptions
                    error_str = str(api_exception).lower()
                    if "429" in error_str or "quota" in error_str or "rate limit" in error_str:
                        raise APIRateLimitError(
                            f"API rate limit exceeded: {api_exception}",
                            retry_after=60,
                        ) from api_exception
                    elif "401" in error_str or "403" in error_str or "authentication" in error_str:
                        raise APIError(
                            f"API authentication failed: {api_exception}",
                            status_code=401 if "401" in error_str else 403,
                        ) from api_exception
                    else:
                        raise APIError(f"API call failed: {api_exception}") from api_exception

                # Check for errors in response
                if not hasattr(response, "text") or not response.text:
                    raise APIResponseError("Empty response from API")

                # Parse JSON response
                response_text = response.text.strip()

                # Handle code block markers if present
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.startswith("```"):
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

                try:
                    response_data = json.loads(response_text)
                except json.JSONDecodeError as e:
                    raise APIResponseError(
                        f"Invalid JSON in API response: {e}",
                        response_data=response_text[:500],
                    ) from e

                # Validate response structure
                if not isinstance(response_data, list):
                    raise APIResponseError(
                        "API response is not a list",
                        response_data=response_text[:500],
                    )

                # Parse to ClassificationResponse models
                responses: List[ClassificationResponse] = []
                for item in response_data:
                    try:
                        response_obj = ClassificationResponse.model_validate(item)
                        responses.append(response_obj)
                    except ValidationError as e:
                        logger.warning(f"Invalid response item: {item}, error: {e}")
                        raise APIResponseError(
                            f"Invalid response item structure: {e}",
                            response_data=str(item),
                        ) from e

                # Match responses to bookmarks
                classified = self.match_responses_to_bookmarks(responses, id_to_bookmark)

                logger.info(
                    f"Successfully classified {len(classified)} bookmark(s) "
                    f"in folder: {' > '.join(folder_path) if folder_path else 'Root'}"
                )
                return classified

            except APIRateLimitError:
                if attempt < max_retries - 1:
                    wait_time = retry_backoff ** attempt
                    logger.warning(
                        f"Rate limit hit, waiting {wait_time:.1f}s before retry "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise

            except APIResponseError:
                # Don't retry on response errors
                raise

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = retry_backoff ** attempt
                    logger.warning(
                        f"API call failed: {e}, waiting {wait_time:.1f}s before retry "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                    continue
                raise APIError(f"API call failed after {max_retries} attempts: {e}") from e

        raise APIError(f"API call failed after {max_retries} attempts")

    async def process_all(
        self,
        bookmarks: List[Bookmark],
        resume: bool = False,
        progress_file: Optional[Path] = None,
    ) -> List[ClassifiedBookmark]:
        """Process all bookmarks with folder-aware batching and progress tracking.

        Groups bookmarks by folder, creates batches, processes sequentially
        with rate limiting, and saves progress after each batch.
        Bookmarks in excluded paths are preserved with their original paths.

        Args:
            bookmarks: List of all Bookmark instances to process.
            resume: Whether to resume from saved progress.
            progress_file: Optional path to progress file (default: "progress.json").

        Returns:
            List of all ClassifiedBookmark instances (including excluded bookmarks).

        Raises:
            ProgressError: If progress save/load fails.
            APIError: If API calls fail.

        Example:
            >>> bookmarks = [Bookmark(...), ...]
            >>> classified = await client.process_all(bookmarks, resume=True)
            >>> len(classified) == len(bookmarks)
            True
        """
        if progress_file is None:
            progress_file = Path("progress.json")

        # Separate excluded and included bookmarks
        excluded_bookmarks: List[Bookmark] = []
        included_bookmarks: List[Bookmark] = []

        for bookmark in bookmarks:
            if self._is_path_excluded(bookmark.folder_path):
                excluded_bookmarks.append(bookmark)
            else:
                included_bookmarks.append(bookmark)

        if excluded_bookmarks:
            excluded_paths_str = ", ".join(
                [" > ".join(path) for path in self.config.excluded_paths]
            )
            logger.info(
                f"Excluding {len(excluded_bookmarks)} bookmark(s) from paths: {excluded_paths_str}"
            )

        # Convert excluded bookmarks to ClassifiedBookmark with original paths
        excluded_classified = [
            self._convert_to_classified_bookmark(bm) for bm in excluded_bookmarks
        ]

        # Load progress if resuming
        processed_bookmarks: List[ClassifiedBookmark] = []
        start_batch_id = 0

        if resume:
            progress = ProgressState.load_from_file(progress_file)
            if progress:
                processed_bookmarks = progress.processed_bookmarks
                start_batch_id = progress.last_batch_id + 1
                logger.info(
                    f"Resuming from batch {start_batch_id}, "
                    f"{len(processed_bookmarks)} bookmark(s) already processed"
                )

        # Create folder-aware batches (only for included bookmarks)
        batches = self.create_batches_with_folder_context(
            included_bookmarks, self.config.batch_size
        )

        # Process batches sequentially
        total_batches = len(batches)
        for batch_id, (batch_bookmarks, folder_path) in enumerate(batches):
            if batch_id < start_batch_id:
                continue

            try:
                logger.info(
                    f"Processing batch {batch_id + 1}/{total_batches} "
                    f"({len(batch_bookmarks)} bookmark(s) in folder: "
                    f"{' > '.join(folder_path) if folder_path else 'Root'})"
                )

                classified_batch = await self.classify_batch(batch_bookmarks, folder_path)
                processed_bookmarks.extend(classified_batch)

                # Save progress after each batch
                progress = ProgressState(
                    last_batch_id=batch_id,
                    processed_count=len(processed_bookmarks),
                    total_count=len(included_bookmarks),
                    processed_bookmarks=processed_bookmarks,
                )
                try:
                    progress.save_to_file(progress_file)
                    logger.debug(f"Progress saved: {len(processed_bookmarks)}/{len(bookmarks)}")
                except Exception as e:
                    raise ProgressError(
                        f"Failed to save progress: {e}",
                        file_path=str(progress_file),
                    ) from e

                # Rate limiting: small delay between batches
                if batch_id < total_batches - 1:
                    await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(
                    f"Failed to process batch {batch_id + 1}: {e}",
                    exc_info=True,
                )
                raise

        logger.info(
            f"Successfully processed {len(processed_bookmarks)} bookmark(s) "
            f"in {total_batches} batch(es)"
        )

        # Merge excluded bookmarks back into the final result
        all_classified = processed_bookmarks + excluded_classified
        logger.info(
            f"Total bookmarks: {len(all_classified)} "
            f"({len(processed_bookmarks)} processed, {len(excluded_classified)} excluded)"
        )

        # Display and save category tree structure
        from src.tree_viewer import print_and_save_category_tree

        logger.info("Displaying and saving category tree structure...")
        tree_file = print_and_save_category_tree(all_classified)
        logger.info(f"Category tree saved to: {tree_file}")

        return all_classified
