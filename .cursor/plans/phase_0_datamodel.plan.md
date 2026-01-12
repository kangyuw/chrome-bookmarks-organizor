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

---

## Todo Items

### Environment Setup

- [ ] Initialize Poetry project (`poetry init`) with Python 3.10+ requirement
- [ ] Add core dependencies to `pyproject.toml`:
  - [ ] `pydantic>=2.0.0` (for data validation and models)
  - [ ] `pydantic-settings>=2.0.0` (for Config model with YAML support)
  - [ ] `pyyaml>=6.0` (for YAML configuration file parsing)
- [ ] Add development dependencies:
  - [ ] `pytest>=7.0.0` (for testing)
  - [ ] `pytest-cov>=4.0.0` (for coverage reporting)
  - [ ] `ruff>=0.1.0` (for linting and formatting)
  - [ ] `mypy>=1.0.0` (for type checking)
- [ ] Run `poetry install` to create virtual environment and install dependencies
- [ ] Configure `ruff` in `pyproject.toml` with appropriate settings
- [ ] Create `.python-version` file (if using pyenv) or document Python version requirement

### Project Structure

- [ ] Create `src/` directory for source code
- [ ] Create `src/models.py` file
- [ ] Create `tests/` directory for test files
- [ ] Create `tests/test_models.py` file
- [ ] Create `config/` directory for configuration files (if needed)
- [ ] Add `__init__.py` files to make directories proper Python packages

### Model Implementation

- [ ] Implement `Bookmark` base model with:
  - [ ] `url: HttpUrl` field with validation
  - [ ] `title: str` field with non-empty validator
  - [ ] `add_date: int` field (Unix timestamp) with validator
  - [ ] `folder_path: List[str]` field with path structure validator
  - [ ] `description: Optional[str]` field
  - [ ] Google-style docstring
  - [ ] `.model_dump()` and `.model_validate()` methods tested
- [ ] Implement `ClassifiedBookmark` model extending `Bookmark` with:
  - [ ] `category_path: List[str]` field
  - [ ] `ai_description: str` field
  - [ ] `series_group: Optional[str]` field
  - [ ] `is_broken: Optional[bool]` field
  - [ ] Google-style docstring
- [ ] Implement `ProgressState` model with:
  - [ ] Fields for resume/checkpoint functionality
  - [ ] JSON serialization support
  - [ ] Google-style docstring
- [ ] Implement `Config` model with:
  - [ ] YAML file loading capability
  - [ ] Application configuration fields
  - [ ] Google-style docstring
  - [ ] Validation for required configuration values

### Testing

- [ ] Write unit tests for `Bookmark` model:
  - [ ] Test URL validation (valid and invalid URLs)
  - [ ] Test title validation (empty, whitespace-only, valid titles)
  - [ ] Test date parsing and validation
  - [ ] Test folder_path structure validation
  - [ ] Test JSON serialization/deserialization
- [ ] Write unit tests for `ClassifiedBookmark` model:
  - [ ] Test inheritance from `Bookmark`
  - [ ] Test all additional fields
  - [ ] Test JSON serialization/deserialization
- [ ] Write unit tests for `ProgressState` model:
  - [ ] Test checkpoint save/load functionality
  - [ ] Test JSON serialization/deserialization
- [ ] Write unit tests for `Config` model:
  - [ ] Test YAML file loading
  - [ ] Test configuration validation
  - [ ] Test default values
- [ ] Run `pytest` to ensure all tests pass
- [ ] Run `ruff check` and `ruff format` to ensure code quality
- [ ] Run `mypy src/` to ensure type checking passes

### Documentation

- [ ] Add module-level docstring to `src/models.py`
- [ ] Ensure all models have comprehensive Google-style docstrings
- [ ] Document any custom validators and their purposes
- [ ] Add usage examples in docstrings or create example scripts