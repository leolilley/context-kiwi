"""Database helper utilities for Supabase responses."""

from typing import Any, Dict, List, Optional, cast

# Type alias for Supabase row data
Row = Dict[str, Any]


def get_rows(data: Any) -> List[Row]:
    """Safely extract rows from Supabase response data."""
    if isinstance(data, list):
        return cast(List[Row], data)
    return []


def get_first(data: Any) -> Optional[Row]:
    """Safely get first row from Supabase response data."""
    rows = get_rows(data)
    return rows[0] if rows else None


def get_nested_first(row: Row, key: str) -> Optional[Row]:
    """Get first item from a nested array field (e.g., joined relations)."""
    nested = row.get(key, [])
    if isinstance(nested, list) and nested:
        return nested[0] if isinstance(nested[0], dict) else None
    return nested if isinstance(nested, dict) else None

