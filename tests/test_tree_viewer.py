"""Unit tests for tree viewer functionality.

Tests cover tree building, formatting, display, and file saving functions.
"""

import pytest
from pathlib import Path
from tempfile import TemporaryDirectory

from src.models import ClassifiedBookmark
from src.tree_viewer import (
    build_category_tree,
    display_category_tree,
    save_category_tree_to_file,
)


class TestTreeViewer:
    """Test suite for tree viewer functions."""

    def test_build_category_tree_single_path(self) -> None:
        """Test building tree with a single category path."""
        bookmarks = [
            ClassifiedBookmark(
                url="https://example.com",
                title="Test",
                add_date=1609459200,
                folder_path=["Tech"],
                category_path=["Tech", "Programming", "Python"],
                ai_description="Test description",
            )
        ]
        tree = build_category_tree(bookmarks)

        assert "Tech" in tree
        assert "Programming" in tree["Tech"]
        assert "Python" in tree["Tech"]["Programming"]
        assert tree["Tech"]["_count"] == 1

    def test_build_category_tree_multiple_paths(self) -> None:
        """Test building tree with multiple category paths."""
        bookmarks = [
            ClassifiedBookmark(
                url="https://example1.com",
                title="Python",
                add_date=1609459200,
                folder_path=["Tech"],
                category_path=["Tech", "Programming", "Python"],
                ai_description="Python guide",
            ),
            ClassifiedBookmark(
                url="https://example2.com",
                title="JavaScript",
                add_date=1609459200,
                folder_path=["Tech"],
                category_path=["Tech", "Programming", "JavaScript"],
                ai_description="JS guide",
            ),
            ClassifiedBookmark(
                url="https://example3.com",
                title="React",
                add_date=1609459200,
                folder_path=["Tech"],
                category_path=["Tech", "Web Development"],
                ai_description="React docs",
            ),
        ]
        tree = build_category_tree(bookmarks)

        assert "Tech" in tree
        assert tree["Tech"]["_count"] == 3
        assert "Programming" in tree["Tech"]
        assert tree["Tech"]["Programming"]["_count"] == 2
        assert "Web Development" in tree["Tech"]
        assert tree["Tech"]["Web Development"]["_count"] == 1

    def test_display_category_tree(self) -> None:
        """Test displaying category tree structure."""
        bookmarks = [
            ClassifiedBookmark(
                url="https://example1.com",
                title="Python",
                add_date=1609459200,
                folder_path=["Tech"],
                category_path=["Tech", "Programming", "Python"],
                ai_description="Python guide",
            ),
            ClassifiedBookmark(
                url="https://example2.com",
                title="JavaScript",
                add_date=1609459200,
                folder_path=["Tech"],
                category_path=["Tech", "Programming", "JavaScript"],
                ai_description="JS guide",
            ),
        ]
        tree_str = display_category_tree(bookmarks)

        assert "Category Tree Structure" in tree_str
        assert "Tech" in tree_str
        assert "Programming" in tree_str
        assert "Python" in tree_str
        assert "JavaScript" in tree_str
        assert "bookmark" in tree_str.lower()

    def test_display_category_tree_empty(self) -> None:
        """Test displaying tree with empty bookmarks list."""
        bookmarks: list[ClassifiedBookmark] = []
        tree_str = display_category_tree(bookmarks)

        assert "No bookmarks to display" in tree_str

    def test_display_category_tree_single_root(self) -> None:
        """Test displaying tree with single root category."""
        bookmarks = [
            ClassifiedBookmark(
                url="https://example.com",
                title="Test",
                add_date=1609459200,
                folder_path=[],
                category_path=["Tech"],
                ai_description="Test",
            )
        ]
        tree_str = display_category_tree(bookmarks)

        assert "Tech" in tree_str
        assert "1 bookmark" in tree_str

    def test_display_category_tree_multiple_roots(self) -> None:
        """Test displaying tree with multiple root categories."""
        bookmarks = [
            ClassifiedBookmark(
                url="https://example1.com",
                title="Tech",
                add_date=1609459200,
                folder_path=[],
                category_path=["Tech", "Programming"],
                ai_description="Tech",
            ),
            ClassifiedBookmark(
                url="https://example2.com",
                title="Science",
                add_date=1609459200,
                folder_path=[],
                category_path=["Science", "Physics"],
                ai_description="Science",
            ),
        ]
        tree_str = display_category_tree(bookmarks)

        assert "Tech" in tree_str
        assert "Science" in tree_str
        assert "2 total bookmarks" in tree_str

    def test_save_category_tree_to_file(self) -> None:
        """Test saving category tree to file."""
        bookmarks = [
            ClassifiedBookmark(
                url="https://example.com",
                title="Test",
                add_date=1609459200,
                folder_path=["Tech"],
                category_path=["Tech", "Programming"],
                ai_description="Test",
            )
        ]

        with TemporaryDirectory() as tmpdir:
            file_path = save_category_tree_to_file(
                bookmarks, output_dir=tmpdir, filename="test_tree.txt"
            )

            assert file_path.exists()
            assert file_path.name == "test_tree.txt"
            content = file_path.read_text(encoding="utf-8")
            assert "Tech" in content
            assert "Programming" in content
            assert "Category Tree Structure" in content

    def test_save_category_tree_creates_directory(self) -> None:
        """Test that save function creates output directory if it doesn't exist."""
        bookmarks = [
            ClassifiedBookmark(
                url="https://example.com",
                title="Test",
                add_date=1609459200,
                folder_path=[],
                category_path=["Tech"],
                ai_description="Test",
            )
        ]

        with TemporaryDirectory() as tmpdir:
            new_dir = Path(tmpdir) / "new_output"
            file_path = save_category_tree_to_file(
                bookmarks, output_dir=new_dir, filename="tree.txt"
            )

            assert new_dir.exists()
            assert file_path.exists()
