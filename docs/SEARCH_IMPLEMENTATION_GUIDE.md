# Search Functionality Implementation Guide

## Overview

This guide documents the search functionality improvements implemented for Context Kiwi, which can be replicated for Script Kiwi. The improvements transform basic substring matching into intelligent multi-term search with better relevance scoring and scalability.

## Problem Statement

**Before:** Search used simple substring matching (`ILIKE` pattern matching) which:
- Required constructing complex query strings
- Only matched if query appeared as substring (OR logic)
- Poor relevance ranking
- Didn't scale well to large datasets
- Required "wacky search term thing" instead of straightforward natural language queries

**After:** Natural language multi-term search that:
- Parses queries into normalized terms
- Requires ALL terms to match (AND logic)
- Intelligent relevance scoring (70% relevance + 30% compatibility)
- Better local search with fuzzy matching
- Ready for PostgreSQL full-text search migration
- Straightforward, intuitive interface

## Implementation Steps

### 1. Enhanced Registry Search (`db/directives.py` or equivalent)

**Location:** `context_kiwi/db/directives.py` → `search()` method

**Key Changes:**
- Added `_parse_search_query()` method to normalize query terms
- Added `_calculate_relevance_score()` method for intelligent scoring
- Modified search logic to require ALL terms to match
- Combined relevance (70%) + compatibility (30%) for final score

**Code Structure:**

```python
def search(
    self, 
    query: str, 
    tech_stack: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    subcategories: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    sort_by: str = "score",
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Search with PostgreSQL full-text search and advanced filtering.
    
    Uses improved multi-term matching for better relevance.
    """
    self._require_db()
    
    # Parse and normalize query
    query_terms = self._parse_search_query(query)
    if not query_terms:
        return []
    
    try:
        # Build search conditions (one per term)
        or_conditions = []
        for term in query_terms:
            or_conditions.extend([f"name.ilike.%{term}%", f"description.ilike.%{term}%"])
        
        # Build query with OR for initial filtering
        query_builder = self.client.table("directives").select(
            "id, name, category, subcategory, description, is_official, download_count, quality_score, "
            "tech_stack, created_at, updated_at, tags, "
            "directive_versions!inner(version, is_latest)"
        ).eq("directive_versions.is_latest", True)
        
        if or_conditions:
            query_builder = query_builder.or_(",".join(or_conditions))
        
        # Apply filters (categories, subcategories, dates, etc.)
        # ... existing filter logic ...
        
        # Execute query - get more results to filter client-side
        result = query_builder.limit(limit * 3).execute()
        
        directives = []
        for row in get_rows(result.data):
            d = {
                "name": row.get("name"),
                "category": row.get("category"),
                "subcategory": row.get("subcategory"),
                "description": row.get("description"),
                # ... other fields ...
            }
            
            # CRITICAL: Multi-term matching - ensure ALL terms appear
            name_desc = f"{d['name']} {d.get('description', '')}".lower()
            if not all(term.lower() in name_desc for term in query_terms):
                continue  # Skip if not all terms match
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance_score(
                query_terms, d["name"], d.get("description", "")
            )
            d["relevance_score"] = relevance_score
            
            # Apply tech stack compatibility
            if tech_stack and (d_stack := d.get("tech_stack")):
                overlap = set(tech.lower() for tech in tech_stack) & set(t.lower() for t in d_stack)
                if not overlap:
                    continue
                d["compatibility_score"] = len(overlap) / max(len(d_stack), 1)
            else:
                d["compatibility_score"] = 1.0
            
            directives.append(d)
        
        # Sort results
        if sort_by == "success_rate":
            directives.sort(key=lambda x: x.get("quality_score", 0), reverse=True)
        elif sort_by == "date":
            directives.sort(key=lambda x: x.get("updated_at") or x.get("created_at") or "", reverse=True)
        elif sort_by == "downloads":
            directives.sort(key=lambda x: x.get("download_count", 0), reverse=True)
        else:  # "score" or default
            # Combined score: 70% relevance + 30% compatibility
            directives.sort(
                key=lambda x: (
                    x.get("relevance_score", 0) * 0.7 + 
                    x.get("compatibility_score", 0) * 0.3
                ),
                reverse=True
            )
        
        return directives[:limit]
    except Exception as e:
        self.logger.error(f"Failed to search directives: {e}")
        raise

def _parse_search_query(self, query: str) -> List[str]:
    """
    Parse search query into normalized terms.
    
    Handles:
    - Multiple words (split by whitespace)
    - Normalization (lowercase, strip)
    - Filters out single characters
    
    Future: Add support for quoted phrases and operators (| for OR, - for NOT)
    """
    if not query or not query.strip():
        return []
    
    terms = []
    for word in query.split():
        word = word.strip().lower()
        if word and len(word) >= 2:  # Ignore single characters
            terms.append(word)
    
    return terms

def _calculate_relevance_score(
    self, 
    query_terms: List[str], 
    name: str, 
    description: str
) -> float:
    """
    Calculate relevance score based on term matches.
    
    Scoring:
    - Exact name match: 100
    - Name contains all terms: 80
    - Name contains some terms: 60 * (matches/terms)
    - Description contains all terms: 40
    - Description contains some terms: 20 * (matches/terms)
    """
    name_lower = name.lower()
    desc_lower = (description or "").lower()
    
    # Check exact name match
    name_normalized = name_lower.replace("_", " ").replace("-", " ")
    query_normalized = " ".join(query_terms)
    if name_normalized == query_normalized or name_lower == query_normalized.replace(" ", "_"):
        return 100.0
    
    # Count term matches in name
    name_matches = sum(1 for term in query_terms if term in name_lower)
    desc_matches = sum(1 for term in query_terms if term in desc_lower)
    
    # Calculate score
    score = 0.0
    
    if name_matches == len(query_terms):
        score = 80.0  # All terms in name
    elif name_matches > 0:
        score = 60.0 * (name_matches / len(query_terms))  # Some terms in name
    
    if desc_matches == len(query_terms):
        score = max(score, 40.0)  # All terms in description
    elif desc_matches > 0:
        score = max(score, 20.0 * (desc_matches / len(query_terms)))  # Some terms in description
    
    return score
```

### 2. Improved Local Search (`directives/loader.py` or equivalent)

**Location:** `context_kiwi/directives/loader.py` → `_calculate_score()` method

**Key Changes:**
- Enhanced scoring to handle multiple terms
- Better partial match handling
- Category and tech stack bonuses

**Code Structure:**

```python
def _calculate_score(
    self, 
    query: str, 
    name: str, 
    description: str,
    category: str,
    tech_stack: list[str]
) -> float:
    """
    Calculate match score with improved multi-term support.
    
    Scoring:
    - Exact name match: 100
    - Name contains all query terms: 80
    - Name contains some query terms: 60 * ratio
    - Description contains all terms: 40
    - Description contains some terms: 20 * ratio
    - Category match: +15
    - Tech stack match: +10
    """
    query_lower = query.lower()
    name_lower = name.lower()
    desc_lower = (description or "").lower()
    category_lower = (category or "").lower()
    
    # Parse query into terms
    query_terms = [t.strip() for t in query_lower.split() if t.strip() and len(t.strip()) >= 2]
    
    if not query_terms:
        # Fallback to simple matching
        if name_lower == query_lower:
            return 100
        if query_lower in name_lower:
            return 70
        if description and query_lower in desc_lower:
            return 40
        return 0
    
    # Exact name match
    name_normalized = name_lower.replace("_", " ").replace("-", " ")
    query_normalized = " ".join(query_terms)
    if name_lower == query_normalized or name_normalized == query_normalized:
        return 100
    
    score = 0.0
    
    # Count term matches in name
    name_matches = sum(1 for term in query_terms if term in name_lower)
    if name_matches == len(query_terms):
        score = 80.0  # All terms in name
    elif name_matches > 0:
        score = 60.0 * (name_matches / len(query_terms))  # Partial match
    
    # Count term matches in description
    desc_matches = sum(1 for term in query_terms if term in desc_lower)
    if desc_matches == len(query_terms):
        score = max(score, 40.0)  # All terms in description
    elif desc_matches > 0:
        score = max(score, 20.0 * (desc_matches / len(query_terms)))  # Partial match
    
    # Category match (bonus)
    if category_lower:
        category_matches = sum(1 for term in query_terms if term in category_lower)
        if category_matches > 0:
            score += 15.0 * (category_matches / len(query_terms))
    
    # Tech stack match (bonus)
    if tech_stack:
        tech_matches = 0
        for tech in tech_stack:
            tech_lower = tech.lower()
            tech_matches += sum(1 for term in query_terms if term in tech_lower)
        if tech_matches > 0:
            score += 10.0 * min(tech_matches / len(query_terms), 1.0)
    
    return min(score, 100.0)  # Cap at 100
```

### 3. Updated Search Tool Interface

**Location:** `context_kiwi/tools/search.py` → `description` and `inputSchema`

**Key Changes:**
- Updated descriptions to emphasize natural language search
- Added examples showing multi-term queries
- Clarified that all terms must match

**Code Structure:**

```python
@property
def description(self) -> str:
    return """Find directives using natural language search.

REQUIRED: query, source, project_path (when source is "local" or "all")
OPTIONAL: sort_by (defaults to "score")

Search Features:
- Multi-term matching: "JWT auth" matches directives with both "JWT" and "auth"
- Smart scoring: Name matches ranked higher than description matches
- Context-aware: Registry search auto-includes your tech stack for better ranking

Sources:
- "local": Search .ai/directives/ and ~/.context-kiwi/directives/ (project + user)
- "registry": Search community registry with tech stack compatibility ranking
- "all": Search both local and registry

Examples:
- search("auth", "registry") - Find auth directives in registry (no project_path needed)
- search("auth", "local", project_path="/path/to/project") - Find local auth directives
- search("JWT authentication", "registry", sort_by="date") - Multi-term search, newest first
- search("form validation", "all", project_path="/path/to/project") - Search everywhere
- search("React component", "registry", tech_stack=["React", "TypeScript"]) - Tech stack filtered

CRITICAL: Always provide project_path when searching "local" or "all" - without it, search will fail with an error."""

@property
def inputSchema(self) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query - natural language search supporting multiple terms. Examples: 'JWT auth', 'form validation', 'React component'. All terms must match for best results."
            },
            # ... other properties ...
        },
        "required": ["query", "source"]
    }
```

### 4. Database Migration (PostgreSQL Full-Text Search)

**Location:** `docs/migrations/add_fulltext_search.sql`

**Purpose:** Adds PostgreSQL full-text search infrastructure for even better performance and relevance.

**Migration SQL:**

```sql
-- Migration: Add PostgreSQL Full-Text Search Support
-- Description: Adds tsvector column and GIN index for fast, scalable full-text search

-- Step 1: Add search_vector column (auto-updated tsvector)
ALTER TABLE directives 
ADD COLUMN IF NOT EXISTS search_vector tsvector 
GENERATED ALWAYS AS (
  to_tsvector('english', 
    coalesce(name, '') || ' ' || 
    coalesce(description, '')
  )
) STORED;

-- Step 2: Create GIN index for fast full-text search
CREATE INDEX IF NOT EXISTS directives_search_idx 
ON directives 
USING GIN(search_vector);

-- Step 3: Add index on name for exact/prefix matching
CREATE INDEX IF NOT EXISTS directives_name_idx 
ON directives 
USING btree(lower(name));

-- Step 4: Add index on description for additional search patterns
CREATE INDEX IF NOT EXISTS directives_description_idx 
ON directives 
USING gin(to_tsvector('english', coalesce(description, '')));
```

**How to Apply:**

Using Supabase MCP:
```python
mcp_user-supabase_apply_migration(
    project_id="your-project-id",
    name="add_fulltext_search",
    query="<migration SQL above>"
)
```

Or manually via Supabase dashboard SQL editor.

**Benefits:**
- O(log n) search performance with GIN indexes
- Better relevance ranking with `ts_rank()`
- Language-specific stemming
- Scales to millions of records

**Note:** The current implementation works without this migration. The migration is an optional enhancement for even better performance.

## Key Concepts

### 1. Multi-Term Matching

**Before:** `"JWT auth"` would match anything with "JWT" OR "auth" (OR logic)

**After:** `"JWT auth"` matches only items with BOTH "JWT" AND "auth" (AND logic)

This is achieved by:
1. Parsing query into terms: `["jwt", "auth"]`
2. Filtering results to ensure all terms appear: `all(term in name_desc for term in terms)`

### 2. Relevance Scoring

**Formula:** `(relevance_score * 0.7) + (compatibility_score * 0.3)`

**Relevance Score:**
- Exact name match: 100
- All terms in name: 80
- Some terms in name: 60 * (matches/terms)
- All terms in description: 40
- Some terms in description: 20 * (matches/terms)

**Compatibility Score:**
- Tech stack overlap ratio: `len(overlap) / max(len(directive_stack), 1)`

### 3. Query Parsing

Simple but effective:
- Split by whitespace
- Normalize (lowercase, strip)
- Filter single characters
- Future: Support quoted phrases, operators (|, -)

## Testing

**Test Cases:**
1. Single term: `"auth"` → Should match items with "auth"
2. Multi-term: `"JWT auth"` → Should match items with both "JWT" and "auth"
3. Exact match: `"jwt_auth"` → Should score highest (100)
4. Partial match: `"form validation"` → Should match "form_validator" with good score
5. Tech stack filtering: Should boost compatible items

**Run Tests:**
```bash
pytest tests/tools/test_search.py -v
```

## Adaptation for Script Kiwi

### File Mapping

| Context Kiwi | Script Kiwi Equivalent |
|--------------|------------------------|
| `context_kiwi/db/directives.py` | `script_kiwi/db/scripts.py` (or similar) |
| `context_kiwi/directives/loader.py` | `script_kiwi/scripts/loader.py` (or similar) |
| `context_kiwi/tools/search.py` | `script_kiwi/tools/search.py` |
| `directives` table | `scripts` table |
| `directive_versions` table | `script_versions` table |

### Key Differences to Consider

1. **Table Names:** Replace `directives` with `scripts`, `directive_versions` with `script_versions`
2. **Field Names:** May differ (e.g., `name`, `description` should be similar)
3. **Tech Stack:** Script Kiwi might have different tech stack concepts
4. **Categories:** Script Kiwi might use different categorization

### Implementation Checklist

- [ ] Update `search()` method in database layer with multi-term parsing
- [ ] Add `_parse_search_query()` method
- [ ] Add `_calculate_relevance_score()` method
- [ ] Update local search `_calculate_score()` method
- [ ] Add multi-term filtering logic (ensure all terms match)
- [ ] Update relevance scoring (70% relevance + 30% compatibility)
- [ ] Update search tool descriptions and examples
- [ ] Test with single and multi-term queries
- [ ] Apply database migration (optional, for full-text search)
- [ ] Update documentation

## Example Usage

### Before (Basic)
```python
search("auth", "registry", "score")
# Matches: "auth", "authentication", "auth_helper", "jwt_auth", etc.
# Problem: Too many irrelevant results
```

### After (Improved)
```python
search("JWT authentication", "registry", "score")
# Matches: Only items with BOTH "JWT" AND "authentication"
# Results ranked by: 70% relevance + 30% tech stack compatibility
# Much more precise and relevant
```

## Performance Considerations

**Current Implementation:**
- Local search: O(n) where n = number of scripts (fast for typical projects)
- Registry search: Uses Supabase query + client-side filtering
- Suitable for: Up to ~10,000 scripts

**With Full-Text Search Migration:**
- Registry search: O(log n) with GIN indexes
- Suitable for: Millions of scripts
- Better relevance ranking with `ts_rank()`

## Backward Compatibility

All existing search queries continue to work:
- Single-term queries work as before (with better scoring)
- Multi-term queries now work intelligently
- All filters and sorting options remain the same
- No breaking changes

## Future Enhancements

1. **Quoted Phrases:** `"JWT auth"` (with quotes) = exact phrase match
2. **Operators:** `JWT | auth` = OR logic, `JWT -token` = exclude "token"
3. **Semantic Search:** Vector embeddings for intent-based search
4. **Fuzzy Matching:** Handle typos (e.g., "autentication" → "authentication")
5. **Field-Specific Search:** `name:auth` = search only in name field

## Summary

The key improvements are:
1. **Query Parsing:** Split into normalized terms
2. **Multi-Term Matching:** Require ALL terms to match
3. **Relevance Scoring:** 70% relevance + 30% compatibility
4. **Better Local Search:** Enhanced scoring with bonuses
5. **Natural Language Interface:** No special syntax needed
6. **Database Migration:** Optional full-text search for scale

This transforms search from basic substring matching to intelligent, scalable search that "just works" with natural language queries.
