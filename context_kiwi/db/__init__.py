"""
Database layer for Context Kiwi.
Provides Supabase integration for directives, runs, and users.
"""

from context_kiwi.db.client import get_supabase_client, SupabaseClient
from context_kiwi.db.directives import DirectiveDB
from context_kiwi.db.analytics import AnalyticsDB
from context_kiwi.db.helpers import Row, get_rows, get_first, get_nested_first

__all__ = [
    "get_supabase_client", 
    "SupabaseClient", 
    "DirectiveDB",
    "AnalyticsDB",
    "Row",
    "get_rows",
    "get_first",
    "get_nested_first",
]

