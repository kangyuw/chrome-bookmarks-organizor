"""Integration tests for Gemini API client.

These tests make actual API calls to Gemini and should be run separately
from unit tests. They require a valid API key to be set.

To run only integration tests:
    pytest -m integration tests/test_api_client_integration.py

To skip integration tests:
    pytest -m "not integration"
"""

import os
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.api_client import GeminiClient
from src.models import Bookmark, Config


@pytest.fixture
def config() -> Config | None:
    """Load configuration from environment or config file."""
    config_path = Path("config/config.yaml")
    
    # Try to load from config file first
    if config_path.exists():
        try:
            loaded_config = Config.load_from_yaml(config_path)
            # Override with test settings (smaller batch size for testing)
            loaded_config.batch_size = 10
            loaded_config.max_retries = 2
            loaded_config.retry_backoff_factor = 1.5
            return loaded_config
        except Exception as e:
            # If loading fails, try creating from environment variable
            pass
    
    # Fallback: try to create from environment variable
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY not set and config.yaml not found or invalid")
    
    # Create config with test settings
    return Config(
        gemini_api_key=api_key,
        batch_size=10,  # Minimum batch size for testing
        enable_web_search=True,
        model_name="gemini-1.5-flash",
        max_retries=2,
        retry_backoff_factor=1.5,
        log_level="INFO",
    )


@pytest.fixture
def sample_bookmarks() -> list[Bookmark]:
    """Create sample bookmarks for testing."""
    return [
        Bookmark(
            url="https://www.python.org/",  # type: ignore[arg-type]
            title="Python Programming Language",
            add_date=1609459200,
            folder_path=["Tech", "Programming"],
            description="Official Python website",
        ),
        Bookmark(
            url="https://react.dev/",  # type: ignore[arg-type]
            title="React - The library for web and native user interfaces",
            add_date=1609459200,
            folder_path=["Tech", "Web Development"],
            description="Official React documentation",
        ),
        Bookmark(
            url="https://docs.python.org/3/tutorial/",  # type: ignore[arg-type]
            title="Python Tutorial",
            add_date=1609459200,
            folder_path=["Tech", "Programming", "Python"],
            description="Python tutorial documentation",
        ),
        Bookmark(
            url="https://developer.mozilla.org/en-US/docs/Web/JavaScript",  # type: ignore[arg-type]
            title="JavaScript | MDN",
            add_date=1609459200,
            folder_path=["Tech", "Programming"],
            description="MDN JavaScript documentation",
        ),
        Bookmark(
            url="https://www.docker.com/",  # type: ignore[arg-type]
            title="Docker: Accelerated Container Application Development",
            add_date=1609459200,
            folder_path=["Tech", "DevOps"],
            description="Docker container platform",
        ),
    ]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_classify_single_bookmark(config: Config | None, sample_bookmarks: list[Bookmark]) -> None:
    """Test classifying a single bookmark with real API call."""
    if config is None:
        pytest.skip("Config not available")
    client = GeminiClient(config)
    
    # Test with a single bookmark
    bookmark = sample_bookmarks[0]
    result = await client.classify_batch([bookmark], bookmark.folder_path)
    
    assert len(result) == 1
    classified = result[0]
    
    # Verify the classified bookmark has all required fields
    assert classified.url == bookmark.url
    assert classified.title == bookmark.title
    assert classified.category_path
    assert len(classified.category_path) > 0
    assert classified.ai_description
    assert len(classified.ai_description) > 0
    
    # Verify category_path is in English (as per requirements)
    assert all(isinstance(cat, str) for cat in classified.category_path)
    
    print(f"\n✓ Classified: {bookmark.title}")
    print(f"  Category: {' > '.join(classified.category_path)}")
    print(f"  Description: {classified.ai_description[:100]}...")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_classify_small_batch(config: Config | None, sample_bookmarks: list[Bookmark]) -> None:
    """Test classifying a small batch of bookmarks with real API call."""
    if config is None:
        pytest.skip("Config not available")
    client = GeminiClient(config)
    
    # Test with 3 bookmarks from the same folder
    batch = sample_bookmarks[:3]
    folder_path = batch[0].folder_path
    
    result = await client.classify_batch(batch, folder_path)
    
    assert len(result) == len(batch)
    
    # Verify all bookmarks were classified
    for i, classified in enumerate(result):
        assert classified.url == batch[i].url
        assert classified.title == batch[i].title
        assert classified.category_path
        assert classified.ai_description
        
        print(f"\n✓ {classified.title}")
        print(f"  Category: {' > '.join(classified.category_path)}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_process_all_small_set(config: Config | None, sample_bookmarks: list[Bookmark]) -> None:
    """Test processing all bookmarks with real API calls."""
    if config is None:
        pytest.skip("Config not available")
    
    # Use test-specific output directory
    from src.constants import TESTS_DIR
    
    test_output_dir = TESTS_DIR
    test_output_dir.mkdir(parents=True, exist_ok=True)
    progress_file = test_output_dir / "progress.json"
    
    client = GeminiClient(config)
    
    # Process all sample bookmarks
    result = await client.process_all(sample_bookmarks, resume=False, progress_file=progress_file)
    
    assert len(result) == len(sample_bookmarks)
    
    # Verify all bookmarks were processed
    for classified in result:
        assert classified.category_path
        assert classified.ai_description
        assert len(classified.category_path) > 0
    
    print(f"\n✓ Processed {len(result)} bookmarks")
    print("\nCategory distribution:")
    category_counts: dict[str, int] = {}
    for classified in result:
        root_cat = classified.category_path[0]
        category_counts[root_cat] = category_counts.get(root_cat, 0) + 1
    
    for category, count in sorted(category_counts.items()):
        print(f"  {category}: {count} bookmark(s)")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_excluded_paths(config: Config | None, sample_bookmarks: list[Bookmark]) -> None:
    """Test that excluded paths are preserved without API calls."""
    if config is None:
        pytest.skip("Config not available")
    
    # Use test-specific output directory
    from src.constants import TESTS_DIR
    
    test_output_dir = TESTS_DIR
    test_output_dir.mkdir(parents=True, exist_ok=True)
    progress_file = test_output_dir / "progress_excluded.json"
    
    # Add excluded path to config
    config.excluded_paths = [["Tech", "DevOps"]]
    
    client = GeminiClient(config)
    
    # Process bookmarks
    result = await client.process_all(sample_bookmarks, resume=False, progress_file=progress_file)
    
    # Find the excluded bookmark
    excluded_bookmark = next(
        (b for b in sample_bookmarks if b.folder_path == ["Tech", "DevOps"]), None
    )
    assert excluded_bookmark is not None
    
    # Find it in results
    excluded_result = next((r for r in result if r.url == excluded_bookmark.url), None)
    assert excluded_result is not None
    
    # Verify it preserved original path
    assert excluded_result.category_path == excluded_bookmark.folder_path
    assert excluded_result.folder_path == excluded_bookmark.folder_path
    
    print(f"\n✓ Excluded bookmark preserved: {excluded_result.title}")
    print(f"  Original path: {' > '.join(excluded_result.folder_path)}")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multilingual_bookmarks(config: Config | None) -> None:
    """Test classifying bookmarks with non-English titles."""
    if config is None:
        pytest.skip("Config not available")
    
    # Use test-specific output directory
    from src.constants import TESTS_DIR
    
    test_output_dir = TESTS_DIR
    test_output_dir.mkdir(parents=True, exist_ok=True)
    progress_file = test_output_dir / "progress_multilingual.json"
    
    client = GeminiClient(config)
    
    multilingual_bookmarks = [
        Bookmark(
            url="https://example.com/chinese",  # type: ignore[arg-type]
            title="Python编程教程",
            add_date=1609459200,
            folder_path=["Tech"],
            description="Chinese bookmark title",
        ),
        Bookmark(
            url="https://example.com/japanese",  # type: ignore[arg-type]
            title="JavaScript入門",
            add_date=1609459200,
            folder_path=["Tech"],
            description="Japanese bookmark title",
        ),
    ]
    
    result = await client.process_all(multilingual_bookmarks, resume=False, progress_file=progress_file)
    
    assert len(result) == len(multilingual_bookmarks)
    
    for classified in result:
        # Verify category_path is in English (requirement)
        assert classified.category_path
        assert all(
            isinstance(cat, str) and cat.isascii() for cat in classified.category_path
        ), "Category path should be in English"
        
        print(f"\n✓ {classified.title}")
        print(f"  Category (English): {' > '.join(classified.category_path)}")
        print(f"  Description: {classified.ai_description[:80]}...")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tree_output_generation(config: Config | None, sample_bookmarks: list[Bookmark]) -> None:
    """Test that tree structure is generated and saved correctly."""
    if config is None:
        pytest.skip("Config not available")
    from src.tree_viewer import display_category_tree, save_category_tree_to_file
    
    # Use test-specific output directory
    from src.constants import TESTS_DIR
    
    test_output_dir = TESTS_DIR
    test_output_dir.mkdir(parents=True, exist_ok=True)
    progress_file = test_output_dir / "progress_tree.json"
    
    client = GeminiClient(config)
    
    # Process bookmarks
    result = await client.process_all(sample_bookmarks, resume=False, progress_file=progress_file)
    
    # Generate tree structure
    tree_str = display_category_tree(result, markdown=True)
    
    assert "Category Tree Structure" in tree_str
    assert len(result) > 0
    
    # Verify markdown format
    assert "#" in tree_str  # Should have markdown headers
    assert "[" in tree_str  # Should have markdown links
    
    # Test saving to file
    with TemporaryDirectory() as tmpdir:
        file_path = save_category_tree_to_file(result, output_dir=tmpdir)
        
        assert file_path.exists()
        assert file_path.suffix == ".md"
        
        content = file_path.read_text(encoding="utf-8")
        assert "Category Tree Structure" in content
        
        print(f"\n✓ Tree structure generated and saved")
        print(f"  File: {file_path}")
        print(f"  Size: {len(content)} characters")
