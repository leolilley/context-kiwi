# Search Functionality Improvements

## Overview

The search functionality has been significantly enhanced to provide a more scalable, straightforward, and intuitive search experience. The improvements move away from basic substring matching to intelligent multi-term search with better relevance scoring.

## Key Improvements

### 1. Multi-Term Query Parsing

**Before:** Simple substring matching - `"JWT auth"` would match anything containing "JWT" OR "auth"

**After:** Intelligent term parsing - `"JWT auth"` matches directives containing BOTH "JWT" AND "auth"

- Query is split into normalized terms
- All terms must match for best results
- Terms are normalized (lowercase, whitespace trimmed)
- Single character terms are ignored

### 2. Improved Relevance Scoring

**Registry Search:**
- **Relevance Score (70%)**: Based on term matches in name and description
  - Exact name match: 100
  - All terms in name: 80
  - Some terms in name: 60 * (matches/terms)
  - All terms in description: 40
  - Some terms in description: 20 * (matches/terms)
- **Compatibility Score (30%)**: Based on tech stack overlap
- Final score: `(relevance * 0.7) + (compatibility * 0.3)`

**Local Search:**
- Similar scoring with additional bonuses for:
  - Category matches: +15
  - Tech stack matches: +10
- Scores capped at 100

### 3. Better Query Interface

**Before:** Required constructing complex query strings with special syntax

**After:** Natural language queries that "just work"
- `search("JWT authentication", "registry", "score")` - Multi-term search
- `search("form validation", "all", "score")` - Searches everywhere
- No need for special operators or syntax

### 4. Scalability Foundation

**Current Implementation:**
- Improved multi-term matching with client-side filtering
- Better relevance calculation
- Ready for PostgreSQL full-text search migration

**Future Enhancement (Migration Available):**
- PostgreSQL `tsvector`/`tsquery` for true full-text search
- GIN indexes for fast searches on large datasets
- Language-specific stemming and search
- See `docs/migrations/add_fulltext_search.sql` for migration

## Technical Details

### Query Parsing

```python
def _parse_search_query(self, query: str) -> List[str]:
    """Parse search query into normalized terms."""
    terms = []
    for word in query.split():
        word = word.strip().lower()
        if word and len(word) >= 2:  # Ignore single characters
            terms.append(word)
    return terms
```

### Relevance Calculation

```python
def _calculate_relevance_score(
    self, 
    query_terms: List[str], 
    name: str, 
    description: str
) -> float:
    """Calculate relevance score based on term matches."""
    # Exact match: 100
    # All terms in name: 80
    # Some terms in name: 60 * ratio
    # All terms in description: 40
    # Some terms in description: 20 * ratio
```

### Multi-Term Filtering

Results are filtered to ensure all query terms appear in the directive's name or description, providing more precise matches than simple OR-based searches.

## Migration Path

### Current State (Phase 1)
- ✅ Multi-term query parsing
- ✅ Improved relevance scoring
- ✅ Better local search
- ✅ Natural language interface

### Future Enhancement (Phase 2)
- 📋 PostgreSQL full-text search migration
- 📋 GIN indexes for performance
- 📋 Optional: Semantic search with embeddings

See `docs/migrations/add_fulltext_search.sql` for the database migration to enable true PostgreSQL full-text search.

## Usage Examples

### Simple Search
```python
# Single term
search("auth", "local", "score")

# Multi-term (all terms must match)
search("JWT authentication", "registry", "score")
```

### With Filters
```python
search(
    "React component",
    "registry",
    "score",
    tech_stack=["React", "TypeScript"],
    categories=["patterns"]
)
```

### Search Everywhere
```python
search("form validation", "all", "score")
```

## Performance

- **Local Search**: O(n) where n = number of directives (fast for typical projects)
- **Registry Search**: Uses Supabase query optimization + client-side filtering
- **Future**: With full-text search migration, registry search becomes O(log n) with GIN indexes

## Backward Compatibility

All existing search queries continue to work. The improvements are additive:
- Single-term queries work as before (with better scoring)
- Multi-term queries now work intelligently
- All filters and sorting options remain the same

## Testing

All existing tests pass. The improvements maintain backward compatibility while adding new capabilities.

```bash
pytest tests/tools/test_search.py -v
# All 6 tests pass
```


