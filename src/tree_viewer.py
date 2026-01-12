"""Tree structure viewer for bookmarks.

This module provides functionality to build and display the folder/category
tree structure from bookmarks in a human-readable format.

It supports both:
- Parsed bookmarks (Bookmark) using folder_path (original folder structure)
- Classified bookmarks (ClassifiedBookmark) using category_path (AI-assigned categories)
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models import Bookmark, ClassifiedBookmark

logger = logging.getLogger(__name__)


def build_category_tree(bookmarks: List[ClassifiedBookmark]) -> Dict[str, Any]:
    """Build a nested tree structure from bookmark category paths.

    Creates a hierarchical dictionary representing the folder structure
    based on category_path from classified bookmarks, including bookmark titles.

    Args:
        bookmarks: List of ClassifiedBookmark instances.

    Returns:
        Nested dictionary representing the tree structure.
        Format: {folder_name: {subfolder: {...}, "_count": int, "_bookmarks": [...]}}

    Example:
        >>> bookmarks = [
        ...     ClassifiedBookmark(..., category_path=["Tech", "Python"]),
        ...     ClassifiedBookmark(..., category_path=["Tech", "JavaScript"]),
        ... ]
        >>> tree = build_category_tree(bookmarks)
        >>> "Tech" in tree
        True
    """
    tree: Dict[str, Any] = {"_count": 0, "_bookmarks": []}

    for bookmark in bookmarks:
        path = bookmark.category_path
        if not path:
            # If no category path, add to root level
            tree["_bookmarks"].append(bookmark)
            tree["_count"] += 1
            continue

        # Navigate/create the path in the tree
        current = tree
        for folder in path:
            if folder not in current:
                current[folder] = {"_count": 0, "_bookmarks": []}
            current[folder]["_count"] += 1
            current = current[folder]

        # Add bookmark to the leaf folder (deepest level)
        current["_bookmarks"].append(bookmark)

    return tree


def format_tree_node_markdown(
    node: Dict[str, Any],
    indent_level: int = 0,
    max_depth: int = 10,
    current_depth: int = 0,
) -> List[str]:
    """Format a tree node in markdown format with nested lists.

    Args:
        node: Dictionary node representing a folder and its children.
        indent_level: Current indentation level for markdown lists.
        max_depth: Maximum depth to display (prevents infinite recursion).
        current_depth: Current depth in the tree.

    Returns:
        List of formatted markdown strings representing the tree structure.
    """
    lines: List[str] = []
    if current_depth >= max_depth:
        return lines

    # Get folder names (excluding metadata like "_count" and "_bookmarks")
    folders = [k for k in node.keys() if k not in ("_count", "_bookmarks")]
    folders.sort()

    # Get bookmarks at this level
    bookmarks = node.get("_bookmarks", [])

    for folder_name in folders:
        child_node = node[folder_name]
        folder_count = child_node.get("_count", 0)

        # Format folder as markdown list item with count
        indent = "  " * indent_level
        folder_line = f"{indent}- **{folder_name}**"
        if folder_count > 0:
            folder_line += f" ({folder_count} bookmark{'s' if folder_count != 1 else ''})"
        lines.append(folder_line)

        # Recursively format children
        child_lines = format_tree_node_markdown(
            child_node,
            indent_level=indent_level + 1,
            max_depth=max_depth,
            current_depth=current_depth + 1,
        )
        lines.extend(child_lines)

    # Add bookmark titles at this level (as list items)
    if bookmarks:
        sorted_bookmarks = sorted(bookmarks, key=lambda b: b.title)
        for bookmark in sorted_bookmarks:
            indent = "  " * (indent_level + 1)
            # Format bookmark with URL if available
            bookmark_line = f"{indent}- [{bookmark.title}]({bookmark.url})"
            lines.append(bookmark_line)

    return lines


def format_tree_node(
    node: Dict[str, Any],
    prefix: str = "",
    is_last: bool = True,
    max_depth: int = 10,
    current_depth: int = 0,
) -> List[str]:
    """Format a tree node and its children recursively, including bookmark titles.

    Args:
        node: Dictionary node representing a folder and its children.
        prefix: String prefix for indentation (used for tree drawing).
        is_last: Whether this is the last child at its level.
        max_depth: Maximum depth to display (prevents infinite recursion).
        current_depth: Current depth in the tree.

    Returns:
        List of formatted strings representing the tree structure.
    """
    lines: List[str] = []
    if current_depth >= max_depth:
        return lines

    # Get folder names (excluding metadata like "_count" and "_bookmarks")
    folders = [k for k in node.keys() if k not in ("_count", "_bookmarks")]
    count = node.get("_count", 0)

    # Sort folders alphabetically
    folders.sort()

    # Get bookmarks at this level
    bookmarks = node.get("_bookmarks", [])

    for i, folder_name in enumerate(folders):
        is_last_folder = i == len(folders) - 1
        child_node = node[folder_name]

        # Determine the connector symbols
        if is_last:
            connector = "└── " if is_last_folder else "├── "
            next_prefix = prefix + "    "
        else:
            connector = "└── " if is_last_folder else "├── "
            next_prefix = prefix + "│   "

        # Get count for this folder
        folder_count = child_node.get("_count", 0)

        # Format the line
        line = f"{prefix}{connector}{folder_name}"
        if folder_count > 0:
            line += f" ({folder_count} bookmark{'s' if folder_count != 1 else ''})"
        lines.append(line)

        # Recursively format children
        child_prefix = next_prefix if is_last_folder else prefix + "│   "
        child_lines = format_tree_node(
            child_node,
            prefix=child_prefix,
            is_last=is_last_folder,
            max_depth=max_depth,
            current_depth=current_depth + 1,
        )
        lines.extend(child_lines)

    # Add bookmark titles at this level (as leaf nodes)
    if bookmarks:
        # Determine the prefix for bookmarks
        if is_last:
            bookmark_prefix = prefix + "    "
            bookmark_connector = "└── " if not folders else "├── "
        else:
            bookmark_prefix = prefix + "│   "
            bookmark_connector = "├── "

        # Sort bookmarks by title
        sorted_bookmarks = sorted(bookmarks, key=lambda b: b.title)

        for i, bookmark in enumerate(sorted_bookmarks):
            is_last_bookmark = i == len(sorted_bookmarks) - 1 and not folders
            connector = "└── " if is_last_bookmark else "├── "
            bookmark_line = f"{bookmark_prefix}{connector}{bookmark.title}"
            lines.append(bookmark_line)

    return lines


def display_category_tree(bookmarks: List[ClassifiedBookmark], markdown: bool = True) -> str:
    """Display the category tree structure from classified bookmarks.

    Builds and formats a tree structure showing all category paths
    and bookmark counts for each folder.

    Args:
        bookmarks: List of ClassifiedBookmark instances.
        markdown: If True, format as markdown. If False, use plain text with tree characters.

    Returns:
        Formatted string representation of the tree structure.

    Example:
        >>> bookmarks = [ClassifiedBookmark(...), ...]
        >>> tree_str = display_category_tree(bookmarks)
        >>> print(tree_str)
        # Category Tree Structure

        ## Tech (5 bookmarks)
        - Programming (3 bookmarks)
          - Python (2 bookmarks)
            - Python Tutorial
            - Advanced Python
          - JavaScript (1 bookmark)
            - JS Guide
        - Web Development (2 bookmarks)
    """
    if not bookmarks:
        return "No bookmarks to display."

    tree = build_category_tree(bookmarks)
    if not tree:
        return "No category structure found."

    lines: List[str] = []
    total_count = len(bookmarks)
    
    if markdown:
        lines.append("# Category Tree Structure")
        lines.append("")
        lines.append(f"**Total:** {total_count} bookmark{'s' if total_count != 1 else ''}")
        lines.append("")
        lines.append("---")
        lines.append("")
    else:
        lines.append(f"Category Tree Structure ({total_count} total bookmark{'s' if total_count != 1 else ''})")
        lines.append("=" * 60)

    if markdown:
        # Handle root-level bookmarks (if any)
        root_bookmarks = tree.get("_bookmarks", [])
        if root_bookmarks:
            lines.append("## Root Level Bookmarks")
            lines.append("")
            for bookmark in sorted(root_bookmarks, key=lambda b: b.title):
                lines.append(f"- [{bookmark.title}]({bookmark.url})")
            if tree.keys() - {"_count", "_bookmarks"}:
                lines.append("")

        # Format each root folder as markdown
        root_folders = sorted([k for k in tree.keys() if k not in ("_count", "_bookmarks")])
        for root_folder in root_folders:
            root_node = tree[root_folder]
            root_count = root_node.get("_count", 0)

            # Root folder as markdown header
            lines.append(f"## {root_folder}")
            if root_count > 0:
                lines.append(f"*{root_count} bookmark{'s' if root_count != 1 else ''}*")
            lines.append("")

            # Children formatted as markdown nested lists
            child_lines = format_tree_node_markdown(
                root_node,
                indent_level=0,
            )
            lines.extend(child_lines)
            lines.append("")  # Add spacing between root folders

    else:
        # Handle root-level bookmarks (if any) - plain text format
        root_bookmarks = tree.get("_bookmarks", [])
        if root_bookmarks:
            lines.append("Root Level Bookmarks:")
            for bookmark in sorted(root_bookmarks, key=lambda b: b.title):
                lines.append(f"  • {bookmark.title}")
            if tree.keys() - {"_count", "_bookmarks"}:
                lines.append("")

        # Format each root folder - plain text format
        root_folders = sorted([k for k in tree.keys() if k not in ("_count", "_bookmarks")])
        for i, root_folder in enumerate(root_folders):
            is_last_root = i == len(root_folders) - 1
            root_node = tree[root_folder]
            root_count = root_node.get("_count", 0)

            # Root folder line
            root_line = root_folder
            if root_count > 0:
                root_line += f" ({root_count} bookmark{'s' if root_count != 1 else ''})"
            lines.append(root_line)

            # Children
            child_lines = format_tree_node(
                root_node,
                prefix="",
                is_last=is_last_root,
            )
            lines.extend(child_lines)

            # Add spacing between root folders (except for the last one)
            if not is_last_root:
                lines.append("")

    return "\n".join(lines)


def save_category_tree_to_file(
    bookmarks: List[ClassifiedBookmark],
    output_dir: Path | str = "output",
    filename: str = "category_tree.md",
) -> Path:
    """Save the category tree structure to a markdown file in the output directory.

    Creates the output directory if it doesn't exist and writes the tree
    structure as markdown to a file.

    Args:
        bookmarks: List of ClassifiedBookmark instances.
        output_dir: Directory where the file will be saved (default: "output").
        filename: Name of the output file (default: "category_tree.md").

    Returns:
        Path to the saved file.

    Raises:
        OSError: If the file cannot be written.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_path = output_path / filename
    tree_str = display_category_tree(bookmarks, markdown=True)

    file_path.write_text(tree_str, encoding="utf-8")
    logger.info(f"Category tree structure saved to: {file_path}")

    return file_path


def print_category_tree(bookmarks: List[ClassifiedBookmark], markdown: bool = False) -> None:
    """Print the category tree structure to console.

    Convenience function that displays the tree structure using the logger.
    Uses plain text format for console output (better for terminal display).

    Args:
        bookmarks: List of ClassifiedBookmark instances.
        markdown: If True, use markdown format. If False, use plain text (default).
    """
    tree_str = display_category_tree(bookmarks, markdown=markdown)
    logger.info("\n" + tree_str)
    print("\n" + tree_str)


def print_and_save_category_tree(
    bookmarks: List[ClassifiedBookmark],
    output_dir: Path | str = "output",
    filename: str = "category_tree.md",
) -> Path:
    """Print and save the category tree structure.

    Displays the tree to console (plain text) and saves both markdown and plain text
    tree view formats to files in the output directory.

    Args:
        bookmarks: List of ClassifiedBookmark instances.
        output_dir: Directory where the files will be saved (default: "output").
        filename: Name of the markdown output file (default: "category_tree.md").
            The plain text tree view will be saved as "category_tree.txt".

    Returns:
        Path to the saved markdown file.
    """
    # Print to console (plain text format for better terminal display)
    print_category_tree(bookmarks, markdown=False)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save markdown format
    markdown_tree_str = display_category_tree(bookmarks, markdown=True)
    markdown_file_path = output_path / filename
    markdown_file_path.write_text(markdown_tree_str, encoding="utf-8")
    logger.info(f"Category tree structure (markdown) saved to: {markdown_file_path}")

    # Save plain text tree view format
    plain_tree_str = display_category_tree(bookmarks, markdown=False)
    # Generate plain text filename from markdown filename
    plain_filename = filename.replace(".md", ".txt")
    if plain_filename == filename:  # If no .md extension, add .txt
        plain_filename = f"{filename}.txt"
    plain_file_path = output_path / plain_filename
    plain_file_path.write_text(plain_tree_str, encoding="utf-8")
    logger.info(f"Category tree structure (plain text) saved to: {plain_file_path}")

    return markdown_file_path


# Functions for displaying parsed bookmarks (using folder_path)


def build_folder_tree(bookmarks: List[Bookmark]) -> Dict[str, Any]:
    """Build a nested tree structure from bookmark folder paths.

    Creates a hierarchical dictionary representing the folder structure
    based on folder_path from parsed bookmarks, including bookmark titles.

    Args:
        bookmarks: List of Bookmark instances.

    Returns:
        Nested dictionary representing the tree structure.
        Format: {folder_name: {subfolder: {...}, "_count": int, "_bookmarks": [...]}}

    Example:
        >>> bookmarks = [
        ...     Bookmark(..., folder_path=["Tech", "Python"]),
        ...     Bookmark(..., folder_path=["Tech", "JavaScript"]),
        ... ]
        >>> tree = build_folder_tree(bookmarks)
        >>> "Tech" in tree
        True
    """
    tree: Dict[str, Any] = {"_count": 0, "_bookmarks": []}

    for bookmark in bookmarks:
        path = bookmark.folder_path
        if not path:
            # If no folder path, add to root level
            tree["_bookmarks"].append(bookmark)
            tree["_count"] += 1
            continue

        # Navigate/create the path in the tree
        current = tree
        for folder in path:
            if folder not in current:
                current[folder] = {"_count": 0, "_bookmarks": []}
            current[folder]["_count"] += 1
            current = current[folder]

        # Add bookmark to the leaf folder (deepest level)
        current["_bookmarks"].append(bookmark)

    return tree


def display_folder_tree(bookmarks: List[Bookmark], markdown: bool = True) -> str:
    """Display the folder tree structure from parsed bookmarks.

    Builds and formats a tree structure showing all folder paths
    and bookmark titles for each folder.

    Args:
        bookmarks: List of Bookmark instances.
        markdown: If True, format as markdown. If False, use plain text with tree characters.

    Returns:
        Formatted string representation of the tree structure.

    Example:
        >>> bookmarks = [Bookmark(...), ...]
        >>> tree_str = display_folder_tree(bookmarks)
        >>> print(tree_str)
        # Folder Tree Structure

        ## Tech (5 bookmarks)
        - Programming (3 bookmarks)
          - Python (2 bookmarks)
            - Python Tutorial
            - Advanced Python
          - JavaScript (1 bookmark)
            - JS Guide
        - Web Development (2 bookmarks)
    """
    if not bookmarks:
        return "No bookmarks to display."

    tree = build_folder_tree(bookmarks)
    if not tree:
        return "No folder structure found."

    lines: List[str] = []
    total_count = len(bookmarks)
    
    if markdown:
        lines.append("# Folder Tree Structure")
        lines.append("")
        lines.append(f"**Total:** {total_count} bookmark{'s' if total_count != 1 else ''}")
        lines.append("")
        lines.append("---")
        lines.append("")
    else:
        lines.append(f"Folder Tree Structure ({total_count} total bookmark{'s' if total_count != 1 else ''})")
        lines.append("=" * 60)

    if markdown:
        # Handle root-level bookmarks (if any)
        root_bookmarks = tree.get("_bookmarks", [])
        if root_bookmarks:
            lines.append("## Root Level Bookmarks")
            lines.append("")
            for bookmark in sorted(root_bookmarks, key=lambda b: b.title):
                lines.append(f"- [{bookmark.title}]({bookmark.url})")
            if tree.keys() - {"_count", "_bookmarks"}:
                lines.append("")

        # Format each root folder as markdown
        root_folders = sorted([k for k in tree.keys() if k not in ("_count", "_bookmarks")])
        for root_folder in root_folders:
            root_node = tree[root_folder]
            root_count = root_node.get("_count", 0)

            # Root folder as markdown header
            lines.append(f"## {root_folder}")
            if root_count > 0:
                lines.append(f"*{root_count} bookmark{'s' if root_count != 1 else ''}*")
            lines.append("")

            # Children formatted as markdown nested lists
            child_lines = format_tree_node_markdown(
                root_node,
                indent_level=0,
            )
            lines.extend(child_lines)
            lines.append("")  # Add spacing between root folders

    else:
        # Handle root-level bookmarks (if any) - plain text format
        root_bookmarks = tree.get("_bookmarks", [])
        if root_bookmarks:
            lines.append("Root Level Bookmarks:")
            for bookmark in sorted(root_bookmarks, key=lambda b: b.title):
                lines.append(f"  • {bookmark.title}")
            if tree.keys() - {"_count", "_bookmarks"}:
                lines.append("")

        # Format each root folder - plain text format
        root_folders = sorted([k for k in tree.keys() if k not in ("_count", "_bookmarks")])
        for i, root_folder in enumerate(root_folders):
            is_last_root = i == len(root_folders) - 1
            root_node = tree[root_folder]
            root_count = root_node.get("_count", 0)

            # Root folder line
            root_line = root_folder
            if root_count > 0:
                root_line += f" ({root_count} bookmark{'s' if root_count != 1 else ''})"
            lines.append(root_line)

            # Children
            child_lines = format_tree_node(
                root_node,
                prefix="",
                is_last=is_last_root,
            )
            lines.extend(child_lines)

            # Add spacing between root folders (except for the last one)
            if not is_last_root:
                lines.append("")

    return "\n".join(lines)


def save_folder_tree_to_file(
    bookmarks: List[Bookmark],
    output_dir: Path | str = "output",
    filename: str = "folder_tree.md",
) -> Path:
    """Save the folder tree structure to a markdown file in the output directory.

    Creates the output directory if it doesn't exist and writes the tree
    structure as markdown to a file.

    Args:
        bookmarks: List of Bookmark instances.
        output_dir: Directory where the file will be saved (default: "output").
        filename: Name of the output file (default: "folder_tree.md").

    Returns:
        Path to the saved file.

    Raises:
        OSError: If the file cannot be written.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    file_path = output_path / filename
    tree_str = display_folder_tree(bookmarks, markdown=True)

    file_path.write_text(tree_str, encoding="utf-8")
    logger.info(f"Folder tree structure saved to: {file_path}")

    return file_path


def print_folder_tree(bookmarks: List[Bookmark], markdown: bool = False) -> None:
    """Print the folder tree structure to console.

    Convenience function that displays the tree structure using the logger.
    Uses plain text format for console output (better for terminal display).

    Args:
        bookmarks: List of Bookmark instances.
        markdown: If True, use markdown format. If False, use plain text (default).
    """
    tree_str = display_folder_tree(bookmarks, markdown=markdown)
    logger.info("\n" + tree_str)
    print("\n" + tree_str)


def print_and_save_folder_tree(
    bookmarks: List[Bookmark],
    output_dir: Path | str = "output",
    filename: str = "folder_tree.md",
) -> Path:
    """Print and save the folder tree structure.

    Displays the tree to console (plain text) and saves both markdown and plain text
    tree view formats to files in the output directory.

    Args:
        bookmarks: List of Bookmark instances.
        output_dir: Directory where the files will be saved (default: "output").
        filename: Name of the markdown output file (default: "folder_tree.md").
            The plain text tree view will be saved as "folder_tree.txt".

    Returns:
        Path to the saved markdown file.
    """
    # Print to console (plain text format for better terminal display)
    print_folder_tree(bookmarks, markdown=False)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Save markdown format
    markdown_tree_str = display_folder_tree(bookmarks, markdown=True)
    markdown_file_path = output_path / filename
    markdown_file_path.write_text(markdown_tree_str, encoding="utf-8")
    logger.info(f"Folder tree structure (markdown) saved to: {markdown_file_path}")

    # Save plain text tree view format
    plain_tree_str = display_folder_tree(bookmarks, markdown=False)
    # Generate plain text filename from markdown filename
    plain_filename = filename.replace(".md", ".txt")
    if plain_filename == filename:  # If no .md extension, add .txt
        plain_filename = f"{filename}.txt"
    plain_file_path = output_path / plain_filename
    plain_file_path.write_text(plain_tree_str, encoding="utf-8")
    logger.info(f"Folder tree structure (plain text) saved to: {plain_file_path}")

    return markdown_file_path
