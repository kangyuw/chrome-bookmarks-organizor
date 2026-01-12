---
name: Phase 1 Parser
overview: Implement the HTML parser module to extract bookmarks from Chrome's Netscape bookmark format, with validation, deduplication, and proper error handling.
todos:
  - id: add_dependency
    content: Add beautifulsoup4>=4.12.0 to pyproject.toml dependencies
    status: completed
  - id: create_parser_module
    content: Create src/parser.py with module-level docstring and imports
    status: completed
  - id: implement_file_reading
    content: Implement file reading and BeautifulSoup parsing with root <DL> detection
    status: completed
  - id: implement_recursive_traversal
    content: Implement _parse_recursive function with folder stack management
    status: completed
  - id: implement_bookmark_extraction
    content: Implement _extract_bookmark_from_tag with URL, title, date, and description extraction
    status: completed
  - id: implement_deduplication
    content: Implement deduplication logic with ADD_DATE comparison and tie-breaker
    status: completed
  - id: implement_error_handling
    content: Add error handling with standard exceptions and logging
    status: completed
  - id: add_logging
    content: Add logging statements for warnings, errors, and summary statistics
    status: completed
  - id: add_type_annotations
    content: Add comprehensive type annotations to all functions
    status: completed
  - id: add_docstrings
    content: Add Google-style docstrings to all functions
    status: completed
---

# Phase 1: Parser Module (`src/parser.py`)

## Overview

Parse Chrome bookmarks from Netscape HTML format into validated `Bookmark` Pydantic models. Handle nested folder structures, extract bookmark metadata, and deduplicate entries.

## Dependencies

Add to `pyproject.toml`:

- `beautifulsoup4>=4.12.0` (for HTML parsing)

## Key Functions

- `parse_bookmarks_html(file_path: Path | str) -> List[Bookmark]` - Main entry point
- `_extract_bookmark_from_tag(tag: Tag, folder_path: List[str]) -> Optional[Bookmark] `- Extract bookmark from `<A>` tag
- `_parse_recursive(dl_element: Tag, folder_stack: List[str]) -> List[Bookmark]` - Recursive folder traversal

## File Structure Understanding

Chrome exports use Netscape Bookmark format:

- DOCTYPE: `<!DOCTYPE NETSCAPE-Bookmark-file-1>`
- Root structure: `<DL><p>` contains all bookmarks and folders
- Folders: `<DT><H3 ADD_DATE="..." LAST_MODIFIED="...">Folder Name</H3>` followed by `<DL><p>`
- Bookmarks: `<DT><A HREF="..." ADD_DATE="..." ICON="...">Title</A>`
- Descriptions: `<DD>` tags following `<A>` tags (may be multiple)
- Nested structure: Multiple levels of `<DL><p>` for nested folders

## Implementation Details

### 1. File Reading

- Read file using `pathlib.Path.read_text(encoding="utf-8")`
- Parse with `BeautifulSoup(html_content, "html.parser")` (no external C dependency)
- Find root `<DL>` element (first `<DL>` after `<H1>` or document root)
- **Error handling**: If root `<DL>` not found → raise `ValueError` with clear message

### 2. Recursive Traversal

- Maintain a `List[str]` stack to track current folder path
- For each child element in `<DL>`:
- If `<DT><H3>`: Extract folder name (trimmed), push to stack if non-empty, recurse into nested `<DL>`
- If `<DT><A>`: Extract bookmark data, use current stack as `folder_path`
- When exiting nested `<DL>`: Pop folder from stack
- Handle edge cases:
- Bookmarks at root level (empty `folder_path`)
- Empty folder names: Skip (exclude from `folder_path`)
- Folder dates: Ignore (only extract dates from bookmark `<A>` tags)

### 3. Bookmark Extraction

- Extract `HREF` attribute (URL) - required
- Extract text content as `title` - required (will be validated by Pydantic)
- Extract `ADD_DATE` attribute:
- Convert from Unix timestamp (seconds since epoch) to `int`
- Handle missing or `ADD_DATE="0"`: Use `0` as fallback (preserves original data)
- Extract description:
- Find all following `<DD>` tags (siblings after `<A>` tag)
- Concatenate all `<DD>` tag text content with newlines (`\n`)
- If no `<DD>` tags, description is `None`
- Ignore `ICON` attribute (base64 data, not needed)
- Build `folder_path` from current stack state (only non-empty folder names)

### 4. Validation & Deduplication

- Create `Bookmark` instances using Pydantic validation
- Pydantic automatically validates:
- URL format via `HttpUrl` type
- Title non-empty via field validator
- Date as integer timestamp
- **Deduplication logic**:
- Track seen URLs in `Dict[str, Bookmark]`
- If duplicate URL found:
- Compare `ADD_DATE` values
- Keep bookmark with most recent `ADD_DATE`
- If `ADD_DATE` values are equal, keep the first one encountered
- Invalid entries caught by Pydantic validation: log warning and skip
- Return deduplicated list of `Bookmark` instances

### 5. Error Handling

Use standard Python exceptions (custom exceptions will be added in Phase 2):

- File not found → raise `FileNotFoundError` with file path
- Invalid HTML structure (missing root `<DL>`) → raise `ValueError` with context
- Invalid bookmark data → catch Pydantic `ValidationError`, log warning with bookmark details, skip entry
- URL validation failures → caught by Pydantic `ValidationError`, logged with URL

### 6. Logging

- Use `logging` module with appropriate levels:
- `WARNING`: Invalid bookmarks skipped, empty folder names, multiple `<DD>` tags
- `ERROR`: File read errors, HTML parsing failures
- `INFO`: Summary statistics (total parsed, duplicates found, invalid entries)
- Log messages should include context (URL, title, error type)

### 7. Code Quality

- Comprehensive type annotations using `typing` module
- Google-style docstrings for all functions
- Use `pathlib.Path` for file operations
- Handle edge cases:
- Empty titles (caught by Pydantic)
- Missing dates (use 0)
- Malformed HTML (raise ValueError)
- Empty folder names (skip)
- Multiple `<DD>` tags (concatenate)

## Testing

Minimal test suite:

- Basic smoke test: Parse a valid bookmark file
- Verify bookmarks are extracted correctly
- Verify parser runs without errors on sample file

## Files to Create/Modify

- `src/parser.py` - Main parser implementation
- `pyproject.toml` - Add `beautifulsoup4>=4.12.0` dependency
- `tests/test_parser.py` - Minimal smoke tests (optional for Phase 1)