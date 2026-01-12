# Chrome Bookmarks Organizer

AI-Powered Bookmark Architect for organizing Chrome bookmarks using semantic classification.

## Features

- Parse Chrome bookmarks from Netscape HTML format
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
│   ├── api_client.py       # Gemini API client (Phase 4)
│   ├── generator.py        # JSON to HTML generator (Phase 5)
│   ├── prompts.py          # LLM prompt templates (Phase 3)
│   ├── exceptions.py       # Custom exception classes (Phase 2)
│   └── utils.py            # Shared utilities (Phase 6)
├── tests/                  # Test suite
├── config/                  # Configuration files
├── inputs/              # Input bookmark files
└── output/                 # Generated organized bookmarks
```

## Testing

### Quick Test Script

Test the parser with a sample bookmark file:

```bash
poetry run python -c "from src.parser import parse_bookmarks_html; bookmarks = parse_bookmarks_html('inputs/bookmarks_1_11_26.html'); print(f'Successfully parsed {len(bookmarks)} bookmarks')"
```

### Running Tests

Run the full test suite:

```bash
poetry run pytest
```

### Code Quality

```bash
# Linting
poetry run ruff check src/ tests/

# Formatting
poetry run ruff format src/ tests/

# Type checking
poetry run mypy src/
```

## Implementation Status

- [x] Phase 0: Data Models (`src/models.py`)
- [X] Phase 1: Parser Module
- [ ] Phase 2: Custom Exceptions
- [ ] Phase 3: Prompt Templates
- [ ] Phase 4: API Client Module
- [ ] Phase 5: Generator Module
- [ ] Phase 6: Utilities & CLI

## License

MIT
