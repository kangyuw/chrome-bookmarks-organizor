"""Prompt templates for Gemini API classification requests.

This module provides prompt templates for sending bookmark classification
requests to the Gemini API. The prompts are designed for the title-only
approach, which sends only bookmark titles and folder paths to reduce
token usage while maintaining classification accuracy.
"""

from typing import List

from src.models import ClassificationRequest


def get_classification_prompt(
    requests: List[ClassificationRequest],
    folder_path: List[str],
) -> str:
    """Generate a classification prompt for a batch of bookmarks.

    Creates a prompt that instructs Gemini to classify bookmarks using only
    their titles and original folder paths. The prompt emphasizes using web
    search to find content and creating improved semantic organization.

    Args:
        requests: List of ClassificationRequest instances (title-only data).
        folder_path: Original folder path where these bookmarks were located.

    Returns:
        Formatted prompt string ready to send to Gemini API.

    Example:
        >>> requests = [
        ...     ClassificationRequest(id=1, title="Python Tutorial", folder_path=["Tech"])
        ... ]
        >>> prompt = get_classification_prompt(requests, ["Tech"])
        >>> "Python Tutorial" in prompt
        True
    """
    folder_path_str = " > ".join(folder_path) if folder_path else "Root"

    # Build the bookmark list
    bookmark_list = []
    for req in requests:
        bookmark_list.append(f"  {req.id}. {req.title}")

    bookmarks_text = "\n".join(bookmark_list)

    prompt = f"""You are an AI assistant that helps organize bookmarks into semantic categories.

These bookmarks were originally in folder: {folder_path_str}

IMPORTANT INSTRUCTIONS:
1. Use web search to find and analyze the content for each bookmark title
2. Consider the original folder_path as a REFERENCE to understand user preferences, but do NOT constrain yourself to it
3. Create BETTER semantic categories that improve upon the original organization
4. Group related bookmarks into series when appropriate (e.g., tutorials from the same site)
5. Detect broken or inaccessible links when possible
6. Return your response as a JSON array with the following structure for each bookmark

CRITICAL LANGUAGE REQUIREMENTS:
- Bookmarks may be in ANY language (English, Chinese, Japanese, etc.) - handle all languages
- category_path MUST ALWAYS be in ENGLISH, regardless of the bookmark's language
- ai_description should be in English
- The bookmark titles you receive may be in various languages - use web search to understand them

Bookmarks to classify:
{bookmarks_text}

For each bookmark, provide:
- id: The bookmark ID (must match the ID from the list above)
- category_path: A list of category names in ENGLISH ONLY (e.g., ["Tech", "Programming", "Python"]). Always use English, even if the bookmark is in another language.
- ai_description: An English description of the bookmark content (approximately 30 words)
- series_group: Optional identifier if this bookmark belongs to a series (e.g., "Python Tutorial Series Part 1" -> "python-tutorial-series")
- is_broken: Optional boolean indicating if the link appears to be broken/inaccessible

Return your response as a JSON array of objects. Example format:
[
  {{
    "id": 1,
    "category_path": ["Tech", "Programming", "Python"],
    "ai_description": "A comprehensive guide to Python programming...",
    "series_group": "python-tutorial-series",
    "is_broken": false
  }},
  {{
    "id": 2,
    "category_path": ["Tech", "Web Development"],
    "ai_description": "Modern web development practices...",
    "series_group": null,
    "is_broken": false
  }}
]

Remember:
- Use web search to understand what each bookmark is about (bookmarks may be in any language)
- Create meaningful, hierarchical categories in ENGLISH ONLY
- Group related content together
- Return ALL bookmarks with their IDs matching the input list
- category_path must always be in English, regardless of the bookmark's original language
"""

    return prompt
