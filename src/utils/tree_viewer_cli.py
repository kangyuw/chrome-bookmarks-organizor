"""Command-line utility for viewing bookmark tree structures.

This utility can load bookmarks from various sources and display them
as tree structures using the tree_viewer module.

Supported input formats:
- HTML bookmark files (Chrome Netscape format)
- JSON progress files (containing ClassifiedBookmark instances)
- JSON files with lists of ClassifiedBookmark or Bookmark instances
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Union, cast

from src.constants import TREE_VIEWER_DIR
from src.models import Bookmark, ClassifiedBookmark, ProgressState
from src.parser import parse_bookmarks_html
from src.tree_viewer import (
    display_category_tree,
    display_folder_tree,
    print_and_save_category_tree,
    print_and_save_folder_tree,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_bookmarks_from_file(input_path: Path) -> tuple[List[Bookmark], bool]:
    """Load bookmarks from a file.

    Supports multiple file formats:
    - HTML files: Parsed as Chrome bookmarks
    - JSON files: Can be ProgressState, list of ClassifiedBookmark, or list of Bookmark

    Args:
        input_path: Path to the input file.

    Returns:
        Tuple of (list of bookmarks, is_classified).
        is_classified is True if bookmarks are ClassifiedBookmark instances.

    Raises:
        FileNotFoundError: If the file does not exist.
        ValueError: If the file format is not supported or invalid.
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    file_ext = input_path.suffix.lower()

    if file_ext == ".html":
        # Parse HTML bookmarks file
        logger.info(f"Parsing HTML bookmarks file: {input_path}")
        bookmarks = parse_bookmarks_html(input_path)
        return bookmarks, False

    elif file_ext == ".json":
        # Try to load as JSON
        logger.info(f"Loading JSON file: {input_path}")
        try:
            content = input_path.read_text(encoding="utf-8")
            data = json.loads(content)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON file: {e}") from e

        # Try ProgressState format first
        try:
            progress = ProgressState.model_validate(data)
            if progress.processed_bookmarks:
                logger.info(
                    f"Loaded {len(progress.processed_bookmarks)} classified bookmarks from ProgressState"
                )
                return progress.processed_bookmarks, True
        except Exception:
            pass

        # Try list of ClassifiedBookmark
        if isinstance(data, list) and len(data) > 0:
            try:
                classified_bookmarks = [
                    ClassifiedBookmark.model_validate(item) for item in data
                ]
                logger.info(f"Loaded {len(classified_bookmarks)} classified bookmarks")
                return classified_bookmarks, True
            except Exception:
                pass

            # Try list of Bookmark
            try:
                bookmarks = [Bookmark.model_validate(item) for item in data]
                logger.info(f"Loaded {len(bookmarks)} bookmarks")
                return bookmarks, False
            except Exception:
                pass

        raise ValueError(
            "JSON file format not recognized. Expected one of: "
            "ProgressState, list of ClassifiedBookmark, or list of Bookmark"
        )

    else:
        raise ValueError(
            f"Unsupported file format: {file_ext}. "
            "Supported formats: .html, .json"
        )


def main() -> int:
    """Main entry point for the tree viewer CLI utility.

    Returns:
        Exit code (0 for success, non-zero for error).
    """
    parser = argparse.ArgumentParser(
        description="View bookmark tree structures from various input sources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View folder tree from HTML bookmarks file
  python -m src.utils.tree_viewer_cli input/bookmarks.html

  # View category tree from progress JSON file
  python -m src.utils.tree_viewer_cli output/progress.json --category

  # Save tree to file (default: output/tree_viewer/)
  python -m src.utils.tree_viewer_cli input/bookmarks.html --output output/tree_viewer

  # View as plain text (no markdown)
  python -m src.utils.tree_viewer_cli input/bookmarks.html --no-markdown
        """,
    )

    parser.add_argument(
        "input_path",
        type=Path,
        help="Path to input file (HTML bookmarks or JSON file)",
    )

    parser.add_argument(
        "--category",
        action="store_true",
        help="Display category tree (for ClassifiedBookmark) instead of folder tree",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        help="Output directory for saving tree files (default: output/tree_viewer/)",
        default=None,
    )

    parser.add_argument(
        "--filename",
        "-f",
        type=str,
        help="Output filename (default: category_tree.md or folder_tree.md)",
    )

    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Display as plain text instead of markdown",
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Only display to console, don't save to file",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Load bookmarks
        bookmarks, is_classified = load_bookmarks_from_file(args.input_path)

        if not bookmarks:
            logger.warning("No bookmarks found in input file")
            return 1

        # Determine output directory (use dedicated subdirectory by default)
        if args.output is None:
            output_dir = TREE_VIEWER_DIR
        else:
            output_dir = args.output

        # Determine output filename
        if args.filename:
            filename = args.filename
        else:
            if args.category or is_classified:
                filename = "category_tree.md"
            else:
                filename = "folder_tree.md"

        # Determine if we should use category tree
        use_category = args.category or is_classified

        if not isinstance(bookmarks[0], ClassifiedBookmark) and use_category:
            logger.error(
                "Cannot display category tree: bookmarks are not ClassifiedBookmark instances"
            )
            return 1

        # Display and optionally save
        if args.no_save:
            # Only print to console
            if use_category:
                from src.tree_viewer import print_category_tree

                # Type cast needed since we verified these are ClassifiedBookmark instances
                classified_bookmarks = cast(List[ClassifiedBookmark], bookmarks)
                print_category_tree(classified_bookmarks, markdown=not args.no_markdown)
            else:
                from src.tree_viewer import print_folder_tree

                print_folder_tree(bookmarks, markdown=not args.no_markdown)
        else:
            # Print and save
            if use_category:
                # Type cast needed since we verified these are ClassifiedBookmark instances
                classified_bookmarks = cast(List[ClassifiedBookmark], bookmarks)
                print_and_save_category_tree(
                    classified_bookmarks,
                    output_dir=output_dir,
                    filename=filename,
                )
            else:
                print_and_save_folder_tree(
                    bookmarks,
                    output_dir=output_dir,
                    filename=filename,
                )

        return 0

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return 1
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
