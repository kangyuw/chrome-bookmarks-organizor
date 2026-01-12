"""Unit tests for prompt templates.

Tests cover prompt generation, formatting, and required content.
"""

import pytest

from src.models import ClassificationRequest
from src.prompts import get_classification_prompt


class TestGetClassificationPrompt:
    """Test suite for get_classification_prompt function."""

    def test_single_bookmark(self) -> None:
        """Test prompt generation with a single bookmark."""
        requests = [
            ClassificationRequest(
                id=1, title="Python Tutorial", folder_path=["Tech", "Programming"]
            )
        ]
        prompt = get_classification_prompt(requests, ["Tech", "Programming"])

        assert "Python Tutorial" in prompt
        assert "1. Python Tutorial" in prompt
        assert "Tech > Programming" in prompt
        assert "category_path" in prompt
        assert "ai_description" in prompt

    def test_multiple_bookmarks(self) -> None:
        """Test prompt generation with multiple bookmarks."""
        requests = [
            ClassificationRequest(id=1, title="Python Tutorial", folder_path=["Tech"]),
            ClassificationRequest(id=2, title="JavaScript Guide", folder_path=["Tech"]),
            ClassificationRequest(id=3, title="React Docs", folder_path=["Tech"]),
        ]
        prompt = get_classification_prompt(requests, ["Tech"])

        assert "1. Python Tutorial" in prompt
        assert "2. JavaScript Guide" in prompt
        assert "3. React Docs" in prompt
        assert "Tech" in prompt

    def test_empty_folder_path(self) -> None:
        """Test prompt generation with empty folder path (Root)."""
        requests = [
            ClassificationRequest(id=1, title="Example", folder_path=[])
        ]
        prompt = get_classification_prompt(requests, [])

        assert "Root" in prompt
        assert "1. Example" in prompt

    def test_nested_folder_path(self) -> None:
        """Test prompt generation with nested folder path."""
        requests = [
            ClassificationRequest(
                id=1, title="Bookmark", folder_path=["Tech", "Programming", "Python"]
            )
        ]
        prompt = get_classification_prompt(requests, ["Tech", "Programming", "Python"])

        assert "Tech > Programming > Python" in prompt
        assert "1. Bookmark" in prompt

    def test_prompt_contains_required_sections(self) -> None:
        """Test that prompt contains all required sections."""
        requests = [
            ClassificationRequest(id=1, title="Test", folder_path=["Tech"])
        ]
        prompt = get_classification_prompt(requests, ["Tech"])

        # Check for key sections
        assert "IMPORTANT INSTRUCTIONS" in prompt
        assert "CRITICAL LANGUAGE REQUIREMENTS" in prompt
        assert "Bookmarks to classify:" in prompt
        assert "For each bookmark, provide:" in prompt
        assert "Return your response as a JSON array" in prompt
        assert "Remember:" in prompt

    def test_language_requirements(self) -> None:
        """Test that prompt includes language requirements."""
        requests = [
            ClassificationRequest(id=1, title="测试", folder_path=["Tech"])
        ]
        prompt = get_classification_prompt(requests, ["Tech"])

        assert "category_path MUST ALWAYS be in ENGLISH" in prompt
        assert "ai_description should be in English" in prompt
        assert "ANY language" in prompt

    def test_json_format_example(self) -> None:
        """Test that prompt includes JSON format example."""
        requests = [
            ClassificationRequest(id=1, title="Test", folder_path=["Tech"])
        ]
        prompt = get_classification_prompt(requests, ["Tech"])

        assert '"id": 1' in prompt
        assert '"category_path"' in prompt
        assert '"ai_description"' in prompt
        assert '"series_group"' in prompt
        assert '"is_broken"' in prompt

    def test_web_search_instruction(self) -> None:
        """Test that prompt includes web search instruction."""
        requests = [
            ClassificationRequest(id=1, title="Test", folder_path=["Tech"])
        ]
        prompt = get_classification_prompt(requests, ["Tech"])

        assert "web search" in prompt.lower()
        assert "Use web search" in prompt

    def test_all_bookmark_ids_present(self) -> None:
        """Test that all bookmark IDs are included in the prompt."""
        requests = [
            ClassificationRequest(id=1, title="First", folder_path=["Tech"]),
            ClassificationRequest(id=2, title="Second", folder_path=["Tech"]),
            ClassificationRequest(id=5, title="Fifth", folder_path=["Tech"]),
        ]
        prompt = get_classification_prompt(requests, ["Tech"])

        assert "1. First" in prompt
        assert "2. Second" in prompt
        assert "5. Fifth" in prompt

    def test_folder_path_reference_instruction(self) -> None:
        """Test that prompt mentions folder path as reference."""
        requests = [
            ClassificationRequest(id=1, title="Test", folder_path=["Tech"])
        ]
        prompt = get_classification_prompt(requests, ["Tech"])

        assert "REFERENCE" in prompt
        assert "original folder_path" in prompt.lower()
