# Chrome Bookmarks Organizer

AI-Powered Bookmark Architect for organizing Chrome bookmarks using semantic classification.

## Features

- Parse Chrome bookmarks from Netscape HTML format
- Tree view visualization of parsed bookmarks with folder hierarchy
- AI-powered semantic categorization using Google Gemini API
- Automatic duplicate detection and removal
- Broken link detection via web search
- Resume/checkpoint functionality for large bookmark collections
- Organized output in Netscape HTML format

## Requirements

- Python 3.10+
- Poetry (for dependency management)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd chrome-bookmarks-organizor
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Copy the example configuration file:
```bash
cp config/config.yaml.example config/config.yaml
```

4. Edit `config/config.yaml` and add your Gemini API key.

## Project Structure

```
chrome-bookmarks-organizor/
├── src/
│   ├── models.py           # Pydantic data models
│   ├── parser.py           # HTML to JSON parser (Phase 1)
│   ├── tree_viewer.py      # Tree structure visualization
│   ├── api_client.py       # Gemini API client (Phase 4)
│   ├── generator.py        # JSON to HTML generator (Phase 5)
│   ├── prompts.py          # LLM prompt templates (Phase 3)
│   ├── exceptions.py       # Custom exception classes (Phase 2)
│   └── utils.py            # Shared utilities (Phase 6)
├── tests/                  # Test suite
├── config/                  # Configuration files
├── input/              # Input bookmark files
└── output/                 # Generated organized bookmarks
```

## Testing

### Quick Test Script

Test the parser with a sample bookmark file:

```bash
poetry run python -c "from src.parser import parse_bookmarks_html; bookmarks = parse_bookmarks_html('input/bookmarks_1_11_26.html'); print(f'Successfully parsed {len(bookmarks)} bookmarks')"
```

### Viewing Bookmark Tree Structure

After parsing bookmarks, you can view them in a tree structure showing the folder hierarchy and bookmark titles.

The tree viewer supports both:
- **Folder trees**: Display the original folder structure from parsed `Bookmark` objects
- **Category trees**: Display AI-assigned categories from `ClassifiedBookmark` objects

#### Using the Tree Viewer Programmatically

Use the tree viewer functions directly in your code:

```python
from pathlib import Path
from src.parser import parse_bookmarks_html
from src.tree_viewer import (
    print_folder_tree,
    display_folder_tree,
    save_folder_tree_to_file,
    print_and_save_folder_tree,
)

# Parse bookmarks
bookmarks = parse_bookmarks_html('input/bookmarks_1_11_26.html')

# Print tree to console (plain text format)
print_folder_tree(bookmarks, markdown=False)

# Get tree as markdown string
tree_markdown = display_folder_tree(bookmarks, markdown=True)

# Save tree to file
save_folder_tree_to_file(bookmarks, output_dir="output", filename="my_tree.md")

# Print and save in one call
print_and_save_folder_tree(bookmarks, output_dir="output", filename="my_tree.md")
```

### Running Tests

Run the full test suite:

```bash
poetry run pytest
```

Run specific test file:

```bash
poetry run pytest tests/test_models.py
```

Run tests excluding integration tests:

```bash
poetry run pytest -m "not integration"
```

Run tests with verbose output:

```bash
poetry run pytest -v
```

## Implementation Status

- [x] Phase 0: Data Models (`src/models.py`)
- [X] Phase 1: Parser Module
- [X] Phase 2: Custom Exceptions
- [X] Phase 3: Prompt Templates
- [X] Phase 4: API Client Module
- [ ] Phase 5: Generator Module
- [ ] Phase 6: Utilities & CLI

## License

MIT
