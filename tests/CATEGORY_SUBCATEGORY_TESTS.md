# Category and Subcategory Feature Tests

This document describes the comprehensive test suite for the dynamic category and subcategory functionality added to context-kiwi.

## Test Coverage Summary

### 1. Database Layer (`tests/db/test_directives.py`)

#### `test_create_directive_with_subcategory`
- **Purpose**: Verify that directives can be created with subcategory
- **Validates**: 
  - `DirectiveDB.create()` accepts `subcategory` parameter
  - Subcategory is correctly passed to database insert
  - Subcategory is stored in the database

#### `test_list_directives_with_subcategory_filter`
- **Purpose**: Verify filtering directives by subcategory
- **Validates**:
  - `DirectiveDB.list()` accepts `subcategory` parameter
  - Filter is correctly applied to database query
  - Only directives matching subcategory are returned

#### `test_search_directives_with_subcategory_filter`
- **Purpose**: Verify searching directives with subcategory filter
- **Validates**:
  - `DirectiveDB.search()` accepts `subcategories` parameter (list)
  - Filter is correctly applied to search query
  - Results are filtered by subcategory

#### `test_directive_record_with_subcategory`
- **Purpose**: Verify `DirectiveRecord` correctly extracts subcategory from database rows
- **Validates**:
  - `DirectiveRecord.from_row()` extracts `subcategory` field
  - Subcategory is correctly assigned to record object

#### `test_directive_record_without_subcategory`
- **Purpose**: Verify `DirectiveRecord` handles null subcategory
- **Validates**:
  - `DirectiveRecord.from_row()` handles `subcategory=None`
  - Record object correctly stores `None` for subcategory

#### `test_create_directive_with_dynamic_category`
- **Purpose**: Verify dynamic categories work (any category name allowed)
- **Validates**:
  - `DirectiveDB.create()` accepts any category name (not restricted to enum)
  - Categories like "workflows", "patterns", etc. are accepted
  - No CHECK constraint errors occur

### 2. Directive Loader (`tests/directives/test_loader.py`)

#### `test_extract_subcategory_from_xml`
- **Purpose**: Verify subcategory extraction from directive XML content
- **Validates**:
  - `DirectiveLoader` extracts `<subcategory>` tag from XML
  - Subcategory is correctly assigned to `DirectiveMatch` objects
  - Category and subcategory are both extracted correctly

#### `test_extract_subcategory_from_path`
- **Purpose**: Verify subcategory extraction from file system path
- **Validates**:
  - When subcategory is not in XML, it's extracted from directory structure
  - Path like `.ai/directives/patterns/api-endpoints/` → subcategory="api-endpoints"
  - Fallback path extraction works correctly

#### `test_search_with_subcategory_filter_local`
- **Purpose**: Verify local search filtering by subcategory
- **Validates**:
  - `DirectiveLoader.search()` accepts `subcategories` parameter
  - Local search results are filtered by subcategory
  - Only matching subcategories are returned

#### `test_search_with_subcategory_filter_registry`
- **Purpose**: Verify registry search filtering by subcategory
- **Validates**:
  - `DirectiveLoader.search()` passes `subcategories` to `DirectiveDB.search()`
  - Registry search results are filtered correctly
  - Subcategory is included in `DirectiveMatch` objects from registry

### 3. Search Tool (`tests/tools/test_search.py`)

#### `test_search_with_subcategory_filter`
- **Purpose**: Verify search tool accepts and passes subcategory filters
- **Validates**:
  - `SearchTool.execute()` accepts `subcategories` in input
  - Subcategory filter is passed to `DirectiveLoader.search()`
  - Results include subcategory information
  - Combined filters (categories + subcategories) work correctly

### 4. Publish Tool (`tests/tools/test_publish.py`)

#### `test_publish_extracts_subcategory_from_content`
- **Purpose**: Verify subcategory extraction from directive content during publish
- **Validates**:
  - `extract_metadata_from_content()` extracts `<subcategory>` tag
  - Category, subcategory, and description are all extracted
  - Extraction works with markdown-wrapped XML

#### `test_publish_with_subcategory`
- **Purpose**: Verify publishing directives with subcategory
- **Validates**:
  - Publish tool extracts subcategory from directive file
  - Subcategory is included in publish request
  - Directive is published with correct subcategory metadata

### 5. Get Tool (`tests/tools/test_get.py`)

#### `test_get_directive_with_subcategory_from_registry`
- **Purpose**: Verify get tool uses category/subcategory from registry for path construction
- **Validates**:
  - `GetTool` fetches `category` and `subcategory` from registry
  - File is saved to correct path: `.ai/directives/{category}/{subcategory}/{name}.md`
  - Path in success message includes subcategory

#### `test_get_directive_without_subcategory`
- **Purpose**: Verify get tool handles directives without subcategory
- **Validates**:
  - When `subcategory` is `None`, file is saved to: `.ai/directives/{category}/{name}.md`
  - No subcategory folder is created
  - Path in success message doesn't include subcategory

## Test Execution

To run all tests:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/db/test_directives.py
pytest tests/directives/test_loader.py
pytest tests/tools/test_search.py
pytest tests/tools/test_publish.py
pytest tests/tools/test_get.py

# Run specific test
pytest tests/db/test_directives.py::TestDirectiveDB::test_create_directive_with_subcategory -v

# Run with coverage
pytest --cov=context_kiwi --cov-report=html
```

## Test Dependencies

Tests require:
- `pytest`
- `pytest-asyncio`
- `pytest-cov` (for coverage)
- Mock dependencies (via `conftest.py` fixtures)

## Key Test Patterns

1. **Mocking Supabase**: Uses `MockSupabaseClient` from `conftest.py`
2. **Temporary Directories**: Uses `tmp_path` fixture for file system tests
3. **Async Testing**: Uses `@pytest.mark.asyncio` for async tool tests
4. **Patch Patterns**: Uses `unittest.mock.patch` for dependency injection

## Coverage Areas

✅ Database CRUD operations with subcategory
✅ Metadata extraction from XML and paths
✅ Search filtering (local and registry)
✅ Publish with subcategory extraction
✅ Get/download with path construction
✅ Dynamic category support (no restrictions)
✅ Null subcategory handling

## Future Test Additions

Consider adding:
- Integration tests with real Supabase instance
- Performance tests for large subcategory filters
- Edge case tests (special characters in subcategory names)
- Migration tests (upgrading old directives to include subcategory)
