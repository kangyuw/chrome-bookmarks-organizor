# AI-Powered Bookmark Architect Implementation Plan

> **Note**: This plan is quite detailed. For a simpler, more focused approach, see [simplified_implementation.plan.md](./simplified_implementation.plan.md)

## Architecture Overview

The system will be built as a modular Python application with three main components:

1. **Parser Module**: Extracts bookmarks from Netscape HTML format
2. **API Client Module**: Gemini API integration with web search, batching and resume capability
3. **Generator Module**: Reconstructs organized HTML output

## Project Structure

```
chrome-bookmarks-organizor/
├── src/
│   ├── __init__.py
│   ├── models.py           # Pydantic models for data validation
│   ├── parser.py           # HTML to JSON parser
│   ├── api_client.py       # Gemini API client with batching and web search
│   ├── generator.py        # JSON to HTML generator
│   ├── prompts.py          # LLM prompt templates (version controlled)
│   ├── exceptions.py        # Custom exception classes
│   └── utils.py            # Shared utilities (backup, config, logging, etc.)
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   ├── test_api_client.py
│   ├── test_generator.py
│   ├── test_models.py
│   └── fixtures/
│       └── sample_bookmarks.html
├── config/
│   └── config.yaml          # Configuration (Hydra/YAML format)
├── data/
│   ├── bookmarks.html       # Input file
│   ├── bookmarks.html.bak   # Auto-backup
│   └── progress.json        # Resume state
├── output/
│   └── organized_bookmarks.html
├── main.py                  # CLI entry point
├── pyproject.toml           # Poetry/Rye dependency management
├── ruff.toml                 # Ruff configuration
├── .python-version          # Python version specification
└── README.md
```

## Implementation Details

### Phase 0: Data Models (`src/models.py`)

**Pydantic Models:**

- `Bookmark` - Base bookmark model with validation
- `ClassifiedBookmark` - Final model with AI classification (extends Bookmark)
- `ProgressState` - Resume/checkpoint model
- `Config` - Application configuration model (loaded from YAML)

**Key Features:**

- URL validation using Pydantic's `HttpUrl` type
- Date parsing and validation for `ADD_DATE`
- Field validators for title length, folder path structure
- JSON serialization/deserialization via `.model_dump()` and `.model_validate()`
- Type safety throughout the application
- Comprehensive type annotations using `typing` module
- Google-style docstrings for all models

**Example Structure:**

```python
class Bookmark(BaseModel):
    url: HttpUrl
    title: str
    add_date: int  # Unix timestamp
    folder_path: List[str]
    description: Optional[str] = None
    
    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError('Title cannot be empty')
        return v.strip()

class ClassifiedBookmark(Bookmark):
    category_path: List[str]
    ai_description: str
    series_group: Optional[str] = None
    is_broken: Optional[bool] = None  # Detected by Gemini via web search
```

### Phase 1: Parser Module (`src/parser.py`)

**Key Functions:**

- `parse_bookmarks_html(file_path: Path | str) -> List[Bookmark]`
- `_extract_bookmark_from_tag(tag: Tag, folder_path: List[str]) -> Optional[Bookmark]`
- `_parse_recursive(dl_element: Tag, folder_stack: List[str]) -> List[Bookmark]`
- Returns validated `Bookmark` Pydantic models

**Implementation Requirements:**

**File Structure Understanding:**

- Chrome exports use Netscape Bookmark format: `<!DOCTYPE NETSCAPE-Bookmark-file-1>`
- Root structure: `<DL><p>` contains all bookmarks and folders
- Folders: `<DT><H3 ADD_DATE="..." LAST_MODIFIED="...">Folder Name</H3>` followed by `<DL><p>`
- Bookmarks: `<DT><A HREF="..." ADD_DATE="..." ICON="...">Title</A>`
- Optional descriptions: `<DD>` tags immediately following `<A>` tags
- Nested structure: Multiple levels of `<DL><p>` for nested folders

**Parsing Logic:**

1. **File Reading:**

   - Read file using `pathlib.Path`
   - Parse with `BeautifulSoup` using `html.parser` (no external C dependency)
   - Find root `<DL>` element

2. **Recursive Traversal:**

   - Maintain a `List[str]` stack to track current folder path
   - For each child element in `<DL>`:
     - If `<DT><H3>`: Extract folder name, push to stack, recurse into nested `<DL>`
     - If `<DT><A>`: Extract bookmark data, use current stack as `folder_path`
     - If closing `</DL>`: Pop folder from stack
   - Handle edge cases: bookmarks at root level (empty `folder_path`)

3. **Bookmark Extraction:**

   - Extract `HREF` attribute (URL) - required
   - Extract text content as `title` - required
   - Extract `ADD_DATE` attribute:
     - Convert from Unix timestamp (seconds since epoch)
     - Handle missing or `ADD_DATE="0"` (use 0 or current timestamp as fallback)
   - Check for following `<DD>` tag for description (optional)
   - Ignore `ICON` attribute (base64 data, not needed)
   - Build `folder_path` from current stack state

4. **Validation & Deduplication:**

   - Create `Bookmark` instances using Pydantic validation
   - Pydantic automatically validates:
     - URL format via `HttpUrl` type
     - Title non-empty via field validator
     - Date as integer timestamp
   - Deduplication logic:
     - Track seen URLs in `Dict[str, Bookmark]`
     - If duplicate found, compare `ADD_DATE` values
     - Keep bookmark with most recent `ADD_DATE`
   - Invalid entries caught by Pydantic validation, log and skip

5. **Error Handling:**

   - File not found → raise `ParsingError` with informative message
   - Invalid HTML structure → raise `ParsingError` with context
   - Invalid bookmark data → raise `InvalidBookmarkError`, log and skip
   - URL validation failures → caught by Pydantic, logged

**Code Quality:**

- Comprehensive type annotations using `typing` module
- Google-style docstrings for all functions
- Proper logging using `logging` module for warnings and errors
- Use `pathlib.Path` for file operations
- Handle edge cases: empty titles, missing dates, malformed HTML

### Phase 2: Custom Exceptions (`src/exceptions.py`)

**Exception Classes:**

- `BookmarkOrganizerError` - Base exception class
- `ParsingError` - Raised when HTML parsing fails
- `InvalidBookmarkError` - Raised when bookmark data is invalid
- `APIError` - Base class for API-related errors
- `APIRateLimitError` - Raised on 429 responses
- `APIResponseError` - Raised when API response is invalid
- `ProgressError` - Raised when progress save/load fails

**Implementation:**

- All exceptions inherit from `BookmarkOrganizerError`
- Include informative error messages
- Use specific exception types (avoid bare `except` clauses)

### Phase 3: Prompt Templates (`src/prompts.py`)

**Purpose:**

- Centralized prompt management with version control
- Template versioning for reproducibility
- Easy prompt iteration and A/B testing

**Key Functions:**

- `get_classification_prompt(bookmarks: List[Bookmark], language: str = "english") -> str`
- Prompt templates stored as constants or loaded from files
- Support for prompt versioning

**Prompt Template Structure:**

```
You are a professional Information Architect. You will receive a JSON list of bookmarks with URLs and titles.

IMPORTANT: Use web search to access and analyze each URL to understand its content, verify if it's accessible, and gather context.

Tasks:
1. For each bookmark, use web search to visit the URL and analyze its content
2. Assign each bookmark to a semantic Category Path (e.g., ["Tech", "Coding", "Python"])
3. Use Dynamic Depth: Create sub-folders only if there are >10 related items
4. Generate a 30-word {language} description based on the actual page content
5. Identify Series: Group URLs from the same series/site together
6. Mark broken/inaccessible links (404, domain expired, etc.) with is_broken: true
7. Return valid JSON with structure: [{{"url": "...", "category_path": [...], "ai_description": "...", "series_group": "...", "is_broken": false}}]
```

### Phase 4: API Client Module (`src/api_client.py`)

**Key Functions:**

- `class GeminiClient` with methods:
  - `async def classify_batch(bookmarks: List[Bookmark]) -> List[ClassifiedBookmark]`
  - `def save_progress(batch_id: int, results: List[ClassifiedBookmark]) -> None`
  - `def load_progress() -> Optional[ProgressState]`
  - `async def process_all(bookmarks: List[Bookmark], resume: bool = False) -> List[ClassifiedBookmark]`

**Implementation Requirements:**

- Batch size: 50-80 items per API call (configurable)
- Use Gemini 1.5 Flash model with web search enabled
- Enable web search via API configuration to allow Gemini to fetch and analyze URLs
- Structured JSON output via `response_mime_type: "application/json"`
- Parse Gemini JSON response using `ClassifiedBookmark.model_validate()` for each item
- Pydantic automatically validates `category_path` (list of strings), `ai_description` (string), etc.
- Progress saved using `ProgressState.model_dump_json()` for type-safe serialization
- Resume capability: Load progress using `ProgressState.model_validate()` from JSON
- Error handling: Raise specific exceptions (`APIRateLimitError`, `APIResponseError`)
- Exponential backoff for rate limits (429 responses)
- Comprehensive type annotations using `typing` module
- Google-style docstrings for all methods
- Proper logging for API calls, errors, and retries
- Use `asyncio` for async operations
- Load prompts from `prompts.py` module

### Phase 5: Generator Module (`src/generator.py`)

**Key Functions:**

- `def generate_html(classified_bookmarks: List[ClassifiedBookmark], output_path: Path | str) -> None`

**Implementation Requirements:**

- Create root folder: `<H3>AI Optimized [YYYY-MM-DD]</H3>`
- Recursively build folder structure from `category_path` arrays
- Place broken links in `<H3>Broken Links</H3>` folder at root
- Use `<DD>` tags for descriptions (30-word summaries)
- Preserve `ADD_DATE` from original bookmarks
- Output valid Netscape HTML format
- Comprehensive type annotations using `typing` module
- Google-style docstrings for all functions
- Proper error handling with custom exceptions
- Use `pathlib.Path` for file operations

### Phase 6: Utilities & CLI (`src/utils.py`, `main.py`)

**Key Functions:**

- `backup_file(file_path: Path | str) -> Path` - Creates timestamped backup
- `load_config(config_path: Path | str) -> Config` - Loads and validates config from YAML using `Config` Pydantic model
- `setup_logging(log_level: str = "INFO", log_file: Optional[Path] = None) -> None` - Configures logging to file and console

**Implementation Requirements:**

- Use `hydra` or `yaml` for configuration loading
- Config validation ensures required fields (API key) are present
- Type checking for batch_size, enable_web_search, etc.
- Comprehensive type annotations using `typing` module
- Google-style docstrings for all functions
- Proper error handling with custom exceptions
- Use `pathlib.Path` for file operations
- Use `logging` module judiciously

**CLI Interface (`main.py`):**

```python
python main.py bookmarks.html [--limit N] [--resume] [--test] [--config PATH]
```

- `--limit N`: Test mode - process only first N bookmarks
- `--resume`: Resume from last saved progress
- `--test`: Dry-run mode (no API calls, mock responses)
- `--config PATH`: Path to config YAML file (default: `config/config.yaml`)
- Use `argparse` or `click` for CLI argument parsing
- Comprehensive type annotations
- Google-style docstrings

## Configuration

**`config/config.yaml` (Hydra/YAML format):**

```yaml
gemini_api_key: "YOUR_API_KEY"
batch_size: 60
description_language: "english"
enable_web_search: true
model_name: "gemini-1.5-flash"
max_retries: 3
retry_backoff_factor: 2.0
log_level: "INFO"
```

**Pydantic Config Model (`src/models.py`):**

```python
class Config(BaseModel):
    gemini_api_key: str
    batch_size: int = Field(ge=10, le=100, default=60)
    description_language: Literal["english", "chinese"] = "english"
    enable_web_search: bool = True
    model_name: str = "gemini-1.5-flash"
    max_retries: int = Field(ge=1, le=10, default=3)
    retry_backoff_factor: float = Field(ge=1.0, le=10.0, default=2.0)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    
    @field_validator('gemini_api_key')
    @classmethod
    def validate_api_key(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError('Gemini API key is required')
        return v.strip()
```

- Automatic validation on load using Pydantic
- Type checking and constraints
- Default values for optional fields
- Load from YAML using `yaml` or `hydra` library

## Data Flow

```
bookmarks.html
    ↓ [Parser + Pydantic Validation]
List[Bookmark] (validated, duplicates removed)
    ↓ [API Client - Batched + Web Search + Pydantic Parsing]
List[ClassifiedBookmark] (validated from API response with web search results)
    ↓ [Save progress using ProgressState.model_dump_json()]
    ↓ [Generator]
organized_bookmarks.html
```

**Pydantic Validation Points:**

- Parser: URL validation, date parsing, field constraints
- API Client: Category path structure, description format, broken link detection
- Config: Required fields, type checking

## Code Quality Standards

**Type Annotations:**

- All functions, methods, and class members must have comprehensive type annotations
- Use `typing` module: `List`, `Dict`, `Optional`, `Union`, `Literal`, etc.
- Use `Path | str` for file paths (Python 3.10+ union syntax)
- Use most specific types possible (avoid `Any`)

**Documentation:**

- Google-style docstrings for all functions, methods, and classes
- Include: purpose, parameters, return values, exceptions raised
- Include usage examples where helpful
- Document async functions clearly

**Code Formatting:**

- Use Ruff for formatting and linting
- Configure in `ruff.toml`
- Run `ruff check` and `ruff format` before commits

**Asynchronous Programming:**

- Use `async`/`await` for I/O-bound operations (API calls, file I/O where appropriate)
- Use `asyncio` for concurrent batch processing
- Proper async context managers for resource cleanup

**Error Handling:**

- Use specific exception types (custom exceptions from `exceptions.py`)
- Provide informative error messages
- Avoid bare `except` clauses
- Log errors appropriately using `logging` module

## Error Handling & Resilience

- **Parser errors**: Raise `ParsingError` or `InvalidBookmarkError` with informative messages; log and skip malformed entries
- **API errors**: Raise specific exceptions (`APIRateLimitError`, `APIResponseError`); save progress, log error, allow resume
- **Rate limits**: Detect 429 responses, raise `APIRateLimitError`, implement exponential backoff with configurable retry settings
- **Web search failures**: Gemini handles retries internally; log if bookmark classification fails; raise `APIResponseError` if persistent
- **Progress tracking**: JSON file with `last_batch_id`, `processed_count`, `total_count`; raise `ProgressError` on save/load failures
- **File operations**: Use `pathlib.Path`; handle `FileNotFoundError`, `PermissionError` with custom exceptions
- **Avoid bare `except` clauses**: Always catch specific exception types
- **Logging**: Use `logging` module judiciously for errors, warnings, and important events

## Testing Strategy

**Framework:** `pytest` with high test coverage (target: 90%+)

**Test Structure:**

- `tests/test_parser.py`: Test HTML parsing, deduplication, edge cases
- `tests/test_api_client.py`: Test API client with mocks, retry logic, progress saving
- `tests/test_generator.py`: Test HTML generation, folder structure, broken links handling
- `tests/test_models.py`: Test Pydantic model validation, serialization
- `tests/fixtures/`: Sample bookmark HTML files for testing

**Test Requirements:**

- Unit tests for all functions and methods
- Test both common cases and edge cases
- Use `pytest.fixture` for reusable test data
- Mock external dependencies (Gemini API, file I/O)
- Test error handling and exception raising
- Test async functions using `pytest-asyncio`
- Integration tests for end-to-end workflows

**Test Modes:**

- Test mode (`--test`): Process 10-20 bookmarks with mock API responses
- Limit mode (`--limit 50`): Real processing on subset
- Resume test: Intentionally interrupt, verify resume works

## Dependencies

**Dependency Management:** Poetry or Rye (use `pyproject.toml`)

**Core Dependencies:**

- `pydantic>=2.0.0` - Data validation and modeling
- `beautifulsoup4>=4.12.0` - HTML parsing
- `google-generativeai>=0.3.0` - Gemini API with web search support
- `pyyaml>=6.0` - YAML configuration loading
- `typing-extensions>=4.8.0` - Extended type hints (Python 3.10+)

**Development Dependencies:**

- `pytest>=7.4.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async testing support
- `pytest-cov>=4.1.0` - Coverage reporting
- `ruff>=0.1.0` - Code formatting and linting (replaces black, isort, flake8)
- `mypy>=1.5.0` - Static type checking (optional)

**Python Version:** Python 3.10+

**Code Quality Tools:**

- **Ruff**: Code formatting and linting (configured in `ruff.toml`)
- **Type Hints**: Strict use of `typing` module for all functions, methods, and class members
- **Docstrings**: Google-style docstrings for all functions, methods, and classes

**Pydantic Benefits:**

- Type-safe data models with automatic validation
- URL validation via `HttpUrl` type
- JSON serialization/deserialization built-in
- Better error messages for invalid data
- IDE autocomplete and type hints throughout

## Implementation Phases Summary

1. **Phase 0**: Data Models (`models.py`) - Pydantic models with type annotations
2. **Phase 1**: Parser Module (`parser.py`) - HTML parsing with error handling
3. **Phase 2**: Custom Exceptions (`exceptions.py`) - Exception hierarchy
4. **Phase 3**: Prompt Templates (`prompts.py`) - Centralized prompt management
5. **Phase 4**: API Client Module (`api_client.py`) - Async Gemini API integration
6. **Phase 5**: Generator Module (`generator.py`) - HTML output generation
7. **Phase 6**: Utilities & CLI (`utils.py`, `main.py`) - Configuration, logging, CLI

## Cursorrules Alignment Summary

This plan adheres to the Python LLM workflow cursorrules:

- **Python 3.10+**: All code uses modern Python features
- **Dependency Management**: Poetry/Rye with `pyproject.toml`
- **Code Formatting**: Ruff (replaces black, isort, flake8)
- **Type Hinting**: Strict use of `typing` module throughout
- **Testing**: pytest with 90%+ coverage target
- **Documentation**: Google-style docstrings for all functions/classes
- **Asynchronous**: Prefer `async`/`await` for I/O operations
- **Error Handling**: Custom exceptions, specific types, informative messages
- **Logging**: Judicious use of `logging` module
- **Modular Design**: Single responsibility, reusable components
- **LLM Prompts**: Dedicated `prompts.py` module with version control
- **Configuration**: YAML/Hydra format for reproducibility