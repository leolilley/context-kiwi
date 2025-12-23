"""
Supabase client wrapper for Context Kiwi.
"""

import os
from typing import Optional
from functools import lru_cache

from dotenv import load_dotenv

# Load .env file
load_dotenv()


class SupabaseClient:
    """Wrapper around Supabase client with lazy initialization."""
    
    _instance: Optional["SupabaseClient"] = None
    _client = None
    
    def __init__(self):
        self._url = os.getenv("SUPABASE_URL")
        self._key = os.getenv("SUPABASE_SECRET_KEY")
    
    @property
    def client(self):
        """Lazily initialize Supabase client."""
        if self._client is None:
            if not self._url or not self._key:
                raise ValueError(
                    "SUPABASE_URL and SUPABASE_SECRET_KEY must be set in environment"
                )
            from supabase import create_client
            self._client = create_client(self._url, self._key)
        return self._client
    
    @property
    def is_configured(self) -> bool:
        """Check if Supabase is configured."""
        return bool(self._url and self._key)
    
    def table(self, name: str):
        """Get a table reference."""
        return self.client.table(name)
    
    @classmethod
    def get_instance(cls) -> "SupabaseClient":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


@lru_cache(maxsize=1)
def get_supabase_client() -> SupabaseClient:
    """Get the Supabase client singleton."""
    return SupabaseClient.get_instance()

