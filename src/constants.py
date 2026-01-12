"""Constants for output directory structure.

This module defines the centralized output directory structure to ensure
all outputs (trees, progress files, logs, tests) are organized in dedicated subdirectories.
"""

from pathlib import Path

# Base output directory
OUTPUT_DIR = Path("output")

# Dedicated subdirectories for different output types
TREE_VIEWER_DIR = OUTPUT_DIR / "tree_viewer"
PROGRESS_DIR = OUTPUT_DIR / "progress"
LOGS_DIR = OUTPUT_DIR / "logs"
TESTS_DIR = OUTPUT_DIR / "tests"

# Default filenames
DEFAULT_PROGRESS_FILE = PROGRESS_DIR / "progress.json"
DEFAULT_CATEGORY_TREE_FILE = TREE_VIEWER_DIR / "category_tree.md"
DEFAULT_FOLDER_TREE_FILE = TREE_VIEWER_DIR / "folder_tree.md"
