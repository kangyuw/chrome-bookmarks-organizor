"""Parser module for extracting bookmarks from Chrome's Netscape bookmark format.

This module provides functionality to parse Chrome bookmarks from HTML files
in the Netscape Bookmark format, extract bookmark metadata, and return
validated Pydantic Bookmark models.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from bs4 import BeautifulSoup, Tag
from pydantic import ValidationError

from src.models import Bookmark

logger = logging.getLogger(__name__)


def parse_bookmarks_html(file_path: Path | str) -> List[Bookmark]:
    """Parse Chrome bookmarks from a Netscape HTML file.

    Reads and parses a Chrome bookmarks HTML file, extracts all bookmarks
    with their metadata, validates them using Pydantic, and returns a
    deduplicated list of Bookmark instances.

    Args:
        file_path: Path to the bookmarks HTML file.

    Returns:
        List of validated Bookmark instances, deduplicated by URL.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the HTML structure is invalid (e.g., missing root <DL>).

    Example:
        >>> bookmarks = parse_bookmarks_html("bookmarks.html")
        >>> len(bookmarks)
        150
        >>> bookmarks[0].title
        'Example Site'
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Bookmarks file not found: {file_path}")

    try:
        html_content = path.read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Failed to read file {file_path}: {e}")
        raise

    soup = BeautifulSoup(html_content, "html.parser")

    # Find root <DL> element (first <DL> after <H1> or document root)
    root_dl = soup.find("dl")
    if root_dl is None:
        raise ValueError("Invalid HTML structure: root <DL> element not found")

    # Parse recursively starting from root
    all_bookmarks = _parse_recursive(root_dl, [])

    # Deduplicate bookmarks
    deduplicated = _deduplicate_bookmarks(all_bookmarks)

    duplicates_removed = len(all_bookmarks) - len(deduplicated)
    logger.info(
        f"Parsed {len(deduplicated)} bookmarks from {file_path}"
        + (f" (removed {duplicates_removed} duplicate(s))" if duplicates_removed > 0 else "")
    )

    return deduplicated


def _parse_recursive(dl_element: Tag, folder_stack: List[str]) -> List[Bookmark]:
    """Recursively parse bookmarks from a <DL> element.

    Traverses the nested structure of folders and bookmarks, maintaining
    a stack of folder names to build the folder_path for each bookmark.

    Args:
        dl_element: BeautifulSoup Tag representing a <DL> element.
        folder_stack: List of folder names representing the current path.

    Returns:
        List of Bookmark instances found in this <DL> and its children.
    """
    bookmarks: List[Bookmark] = []

    # Iterate through direct children of <DL>
    for child in dl_element.children:
        if not isinstance(child, Tag):
            continue

        # Handle folder: <DT><H3>...</H3><DL>...</DL>
        if child.name == "dt":
            h3_tag = child.find("h3", recursive=False)
            a_tag = child.find("a", recursive=False)

            if h3_tag is not None:
                # Extract folder name
                folder_name = h3_tag.get_text(strip=True)

                # Skip empty folder names
                if not folder_name:
                    logger.warning("Found empty folder name, skipping")
                    continue

                # Push folder to stack
                folder_stack.append(folder_name)

                # Find nested <DL> and recurse
                nested_dl = child.find("dl", recursive=False)
                if nested_dl is not None:
                    nested_bookmarks = _parse_recursive(nested_dl, folder_stack)
                    bookmarks.extend(nested_bookmarks)

                # Pop folder from stack when done
                folder_stack.pop()

            elif a_tag is not None:
                # Extract bookmark
                bookmark = _extract_bookmark_from_tag(a_tag, folder_stack.copy())
                if bookmark is not None:
                    bookmarks.append(bookmark)

    return bookmarks


def _extract_bookmark_from_tag(tag: Tag, folder_path: List[str]) -> Optional[Bookmark]:
    """Extract bookmark data from an <A> tag.

    Extracts URL, title, date, and description from a bookmark <A> tag
    and creates a validated Bookmark instance.

    Args:
        tag: BeautifulSoup Tag representing an <A> element.
        folder_path: List of folder names representing the bookmark's location.

    Returns:
        Bookmark instance if extraction and validation succeed, None otherwise.
    """
    # Extract URL (required)
    href = tag.get("href")
    if not href:
        logger.warning("Bookmark missing HREF attribute, skipping")
        return None

    # Extract title (required, will be validated by Pydantic)
    title = tag.get_text(strip=True)
    if not title:
        logger.warning(f"Bookmark with URL {href} has empty title, skipping")
        return None

    # Extract ADD_DATE (optional, default to 0)
    add_date_str = tag.get("add_date", "0")
    try:
        add_date = int(add_date_str) if add_date_str else 0
    except (ValueError, TypeError):
        logger.warning(
            f"Invalid ADD_DATE '{add_date_str}' for bookmark {href}, using 0"
        )
        add_date = 0

    # Extract description from following <DD> tags
    description = _extract_description(tag)

    # Create Bookmark instance with Pydantic validation
    try:
        bookmark = Bookmark(
            url=href,
            title=title,
            add_date=add_date,
            folder_path=folder_path,
            description=description,
        )
        return bookmark
    except ValidationError as e:
        logger.warning(f"Invalid bookmark data for {href}: {e}")
        return None


def _extract_description(tag: Tag) -> Optional[str]:
    """Extract description from <DD> tags following an <A> tag.

    Finds all <DD> tags that are siblings after the <A> tag and concatenates
    their text content with newlines.

    Args:
        tag: BeautifulSoup Tag representing an <A> element.

    Returns:
        Concatenated description text, or None if no <DD> tags found.
    """
    dd_tags = []
    current = tag.next_sibling

    # Find all following <DD> siblings
    while current is not None:
        if isinstance(current, Tag) and current.name == "dd":
            text = current.get_text(strip=True)
            if text:
                dd_tags.append(text)
        current = current.next_sibling

    if not dd_tags:
        return None

    # Log warning if multiple <DD> tags found
    if len(dd_tags) > 1:
        logger.warning(
            f"Found {len(dd_tags)} <DD> tags for bookmark, concatenating"
        )

    return "\n".join(dd_tags)


def _deduplicate_bookmarks(bookmarks: List[Bookmark]) -> List[Bookmark]:
    """Deduplicate bookmarks by URL, keeping the most recent.

    If multiple bookmarks have the same URL, keeps the one with the most
    recent ADD_DATE. If ADD_DATE values are equal, keeps the first one
    encountered.

    Args:
        bookmarks: List of Bookmark instances to deduplicate.

    Returns:
        Deduplicated list of Bookmark instances.
    """
    seen: Dict[str, Bookmark] = {}
    duplicates_count = 0

    for bookmark in bookmarks:
        url_str = str(bookmark.url)

        if url_str in seen:
            existing = seen[url_str]

            # Compare ADD_DATE values
            if bookmark.add_date > existing.add_date:
                # New bookmark is more recent, replace
                seen[url_str] = bookmark
                duplicates_count += 1
            elif bookmark.add_date == existing.add_date:
                # Same date, keep first one (already in seen)
                duplicates_count += 1
            # If existing is more recent, keep it (do nothing)
            else:
                duplicates_count += 1
        else:
            seen[url_str] = bookmark

    if duplicates_count > 0:
        logger.info(f"Removed {duplicates_count} duplicate bookmark(s)")

    return list(seen.values())
